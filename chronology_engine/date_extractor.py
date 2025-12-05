"""
Date extraction module using regex-based scanning
"""

import re
import json
from typing import List, Dict, Set
from collections import defaultdict
import sys
sys.path.append('..')
from utils.date_utils import DateUtils
import config


class DateExtractor:
    """Extract dates from knowledge base chunks using regex"""

    def __init__(self, chunks: List[str], metadata: List[Dict]):
        """
        Initialize date extractor

        Args:
            chunks: List of text chunks from knowledge base
            metadata: List of metadata dicts for each chunk
        """
        self.chunks = chunks
        self.metadata = metadata
        self.date_utils = DateUtils()

    def extract_all_dates(self) -> Dict[str, List[str]]:
        """
        Extract all dates from chunks and group by year

        Returns:
            Dictionary mapping year -> list of dates (YYYY-MM-DD format)
        """
        print("\n[Phase 1] Date Discovery")
        print(f"  Scanning {len(self.chunks)} chunks...")

        # Extract raw dates
        raw_dates = self._scan_chunks_for_dates()

        # Normalize and deduplicate
        normalized_dates = self._normalize_and_deduplicate(raw_dates)

        # Group by year
        dates_by_year = self._group_by_year(normalized_dates)

        # Print summary
        total_dates = sum(len(dates) for dates in dates_by_year.values())
        years = sorted(dates_by_year.keys())

        print(f"  ✓ Found {len(raw_dates)} raw date mentions")
        print(f"  ✓ Extracted {total_dates} unique dates")

        if years:
            print(f"  ✓ Date range: {years[0]} to {years[-1]}")
            print(f"  ✓ Years covered: {len(years)}")

        return dates_by_year

    def _scan_chunks_for_dates(self) -> List[Dict]:
        """
        Scan all chunks with regex patterns

        Returns:
            List of dicts with date info and source metadata
        """
        found_dates = []

        for chunk_idx, chunk_text in enumerate(self.chunks):
            # Try each date pattern
            for pattern in config.DATE_PATTERNS:
                matches = re.finditer(pattern, chunk_text, re.IGNORECASE)

                for match in matches:
                    date_string = match.group(0)

                    # Get metadata for this chunk
                    chunk_meta = self.metadata[chunk_idx] if chunk_idx < len(self.metadata) else {}

                    found_dates.append({
                        'raw_date': date_string,
                        'chunk_idx': chunk_idx,
                        'source': chunk_meta.get('source', 'Unknown'),
                        'pages': chunk_meta.get('page_numbers', []),
                        'context': self._get_context(chunk_text, match.start(), match.end())
                    })

        return found_dates

    def _get_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """Extract surrounding context for a date match"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()

    def _normalize_and_deduplicate(self, raw_dates: List[Dict]) -> List[Dict]:
        """
        Normalize dates to YYYY-MM-DD and remove duplicates

        Returns:
            List of unique dates with metadata
        """
        seen_dates = {}  # normalized_date -> metadata
        skipped = 0

        for date_info in raw_dates:
            # Normalize date
            normalized = self.date_utils.normalize_date(date_info['raw_date'])

            if not normalized:
                skipped += 1
                continue

            # Check if valid date (not too far in past/future)
            try:
                year = int(normalized.split('-')[0])
                if year < 1900 or year > 2100:
                    skipped += 1
                    continue
            except:
                skipped += 1
                continue

            # Check for future dates
            if self.date_utils.is_future_date(normalized):
                if not config.INCLUDE_FUTURE_DATES:
                    skipped += 1
                    continue
                date_info['is_future'] = True

            # Store first occurrence with best metadata
            if normalized not in seen_dates:
                seen_dates[normalized] = {
                    'date': normalized,
                    'sources': set([date_info['source']]),
                    'pages': set(date_info['pages']),
                    'chunk_indices': [date_info['chunk_idx']],
                    'is_future': date_info.get('is_future', False)
                }
            else:
                # Merge metadata
                seen_dates[normalized]['sources'].add(date_info['source'])
                seen_dates[normalized]['pages'].update(date_info['pages'])
                seen_dates[normalized]['chunk_indices'].append(date_info['chunk_idx'])

        if skipped > 0:
            print(f"  ℹ Skipped {skipped} invalid/duplicate dates")

        # Convert sets to lists for JSON serialization
        result = []
        for date_data in seen_dates.values():
            date_data['sources'] = list(date_data['sources'])
            date_data['pages'] = sorted(list(date_data['pages']))
            result.append(date_data)

        return result

    def _group_by_year(self, dates: List[Dict]) -> Dict[str, List[str]]:
        """
        Group dates by year

        Returns:
            Dictionary: {year: [date1, date2, ...]}
        """
        dates_by_year = defaultdict(list)

        for date_info in dates:
            year = date_info['date'].split('-')[0]
            dates_by_year[year].append(date_info['date'])

        # Sort dates within each year
        for year in dates_by_year:
            dates_by_year[year] = sorted(dates_by_year[year])

        return dict(dates_by_year)

    def save_dates_cache(self, filepath: str, dates_by_year: Dict):
        """Save extracted dates to cache file"""
        with open(filepath, 'w') as f:
            json.dump({
                'extracted_at': DateUtils().fix_ocr_errors(str(DateUtils)),
                'total_dates': sum(len(dates) for dates in dates_by_year.values()),
                'dates_by_year': dates_by_year
            }, f, indent=2)
        print(f"  ✓ Saved date cache to {filepath}")

    @staticmethod
    def load_dates_cache(filepath: str) -> Dict[str, List[str]]:
        """Load dates from cache file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return data.get('dates_by_year', {})
        except FileNotFoundError:
            return None
