"""
Date utility functions for parsing and normalization
"""

import re
from datetime import datetime
from typing import Optional, List, Dict
import config


class DateUtils:
    """Utilities for date parsing, normalization, and validation"""

    MONTH_MAP = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2, 'febnary': 2, 'febuary': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12, 'decemebr': 12
    }

    # Year filtering constants
    MIN_YEAR = 2010
    MAX_YEAR = 2030

    @staticmethod
    def fix_ocr_errors(text: str) -> str:
        """Fix common OCR errors in dates"""
        for error, correction in config.OCR_CORRECTIONS.items():
            text = text.replace(error, correction)

        # Fix O -> 0 in years (e.g., 2O23 -> 2023)
        text = re.sub(r'(\d{2})O(\d)', r'\g<1>0\2', text)

        return text

    @staticmethod
    def is_year_valid(year: int) -> bool:
        """Check if year is within valid range (2010-2026)"""
        return DateUtils.MIN_YEAR <= year <= DateUtils.MAX_YEAR

    @staticmethod
    def normalize_date(date_string: str, date_format: str = None) -> Optional[str]:
        """
        Convert various date formats to YYYY-MM-DD

        Args:
            date_string: Date string in various formats
            date_format: Expected format (for ambiguous dates)

        Returns:
            Normalized date string or None if unparseable or outside 2010-2026 range
        """
        if not date_string:
            return None

        # Fix OCR errors first
        date_string = DateUtils.fix_ocr_errors(date_string.strip())

        # Try parsing with different patterns
        patterns = [
            "%B %d, %Y",      # February 17, 2023
            "%B %d %Y",       # February 17 2023
            "%b %d, %Y",      # Feb 17, 2023
            "%b %d %Y",       # Feb 17 2023
            "%b. %d, %Y",     # Feb. 17, 2023
            "%Y-%m-%d",       # 2023-02-17
            "%m/%d/%Y",       # 02/17/2023 (US format)
            "%d/%m/%Y",       # 17/02/2023 (EU format)
            "%m-%d-%Y",       # 02-17-2023
            "%d-%m-%Y",       # 17-02-2023
        ]

        for pattern in patterns:
            try:
                parsed = datetime.strptime(date_string, pattern)
                # Filter dates by year range
                if DateUtils.is_year_valid(parsed.year):
                    return parsed.strftime(config.OUTPUT_DATE_FORMAT)
                else:
                    return None  # Date outside valid range
            except (ValueError, TypeError):
                continue

        # Try manual parsing for flexible formats
        try:
            return DateUtils._parse_flexible_date(date_string)
        except:
            return None

    @staticmethod
    def _parse_flexible_date(date_string: str) -> Optional[str]:
        """Parse dates with flexible format (Month Day, Year)"""
        # Match: "Month Day, Year" or "Month Day Year"
        match = re.search(
            r'\b([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\b',
            date_string,
            re.IGNORECASE
        )

        if match:
            month_str, day_str, year_str = match.groups()
            month_num = DateUtils.MONTH_MAP.get(month_str.lower())

            if month_num:
                try:
                    year = int(year_str)
                    # Filter by year range
                    if not DateUtils.is_year_valid(year):
                        return None
                    
                    date_obj = datetime(year, month_num, int(day_str))
                    return date_obj.strftime(config.OUTPUT_DATE_FORMAT)
                except ValueError:
                    pass

        # Match: MM/DD/YYYY or DD/MM/YYYY
        match = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', date_string)
        if match:
            part1, part2, year_str = match.groups()
            year = int(year_str)
            
            # Filter by year range
            if not DateUtils.is_year_valid(year):
                return None

            # Determine format based on config
            if config.DATE_FORMAT_PREFERENCE == "US":
                month, day = int(part1), int(part2)
            else:
                day, month = int(part1), int(part2)

            try:
                date_obj = datetime(year, month, day)
                return date_obj.strftime(config.OUTPUT_DATE_FORMAT)
            except ValueError:
                # Try opposite format
                try:
                    date_obj = datetime(year, int(part2), int(part1))
                    return date_obj.strftime(config.OUTPUT_DATE_FORMAT)
                except ValueError:
                    pass

        return None

    @staticmethod
    def is_valid_date(date_string: str) -> bool:
        """Check if date string is valid"""
        try:
            datetime.strptime(date_string, config.OUTPUT_DATE_FORMAT)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_future_date(date_string: str) -> bool:
        """Check if date is in the future"""
        try:
            date_obj = datetime.strptime(date_string, config.OUTPUT_DATE_FORMAT)
            return date_obj > datetime.now()
        except (ValueError, TypeError):
            return False

    @staticmethod
    def format_page_range(pages: List[int]) -> str:
        """
        Format page numbers as ranges

        Args:
            pages: List of page numbers (e.g., [10, 11, 12, 15, 18])

        Returns:
            Formatted string (e.g., "Pages 10-12, 15, 18")
        """
        if not pages:
            return "Unknown"

        pages = sorted(set(pages))  # Remove duplicates and sort

        if len(pages) == 1:
            return f"Page {pages[0]}"

        # Group consecutive pages into ranges
        ranges = []
        start = pages[0]
        end = pages[0]

        for i in range(1, len(pages)):
            if pages[i] == end + 1:
                end = pages[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = end = pages[i]

        # Add last range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")

        return f"Pages {', '.join(ranges)}"

    @staticmethod
    def calculate_gap_days(date1: str, date2: str) -> int:
        """Calculate days between two dates"""
        try:
            d1 = datetime.strptime(date1, config.OUTPUT_DATE_FORMAT)
            d2 = datetime.strptime(date2, config.OUTPUT_DATE_FORMAT)
            return abs((d2 - d1).days)
        except (ValueError, TypeError):
            return 0
 