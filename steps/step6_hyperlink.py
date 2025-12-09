"""
STEP 6: Add Hyperlinks to Page Numbers in Table

- Reads page structure from Step 5
- Finds all page number references in table cells
- Adds clickable hyperlinks to corresponding pages
- Handles multiple comma-separated page ranges
- Output: Final_Chronology.pdf
"""
import fitz  # PyMuPDF
import re
import json
import logging
from pathlib import Path

# Import from parent config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_FOLDER, LOG_LEVEL, LOG_FILE

def setup_logging():
    """Configure logging."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logger = logging.getLogger("Step6_Hyperlink")
    logger.setLevel(getattr(logging, LOG_LEVEL))
    logger.handlers.clear()

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(log_format))
    logger.addHandler(ch)

    if LOG_FILE:
        fh = logging.FileHandler(LOG_FILE.replace(".log", "_step6.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format))
        logger.addHandler(fh)

    return logger

logger = setup_logging()

# ============================================================================
# PATTERNS
# ============================================================================

# Match a single page number or range, e.g. "196-200" or "98"
single_range_pattern = re.compile(r'(\d{1,5})(?:\s*-\s*(\d{1,5}))?')

# A text cell that looks like only page numbers / ranges
# e.g. "196-200, 203-208, 669-673" or "98"
page_cell_pattern = re.compile(r'^[\d\s,\-]+$')

def parse_page_ranges(text):
    """
    Parse a string containing comma-separated page ranges.
    "196-200, 203-208, 669-673" -> [("196-200", 196), ("203-208", 203), ...]
    "1-5, 43, 98, 102" -> [("1-5", 1), ("43", 43), ("98", 98), ("102", 102)]
    """
    ranges = []
    for part in text.split(','):
        part = part.strip()
        if not part:
            continue

        m = single_range_pattern.fullmatch(part)
        if not m:
            continue

        start_page = int(m.group(1))
        ranges.append((part, start_page))

    return ranges

def process_pdf(input_path, output_path, index_start, index_end):
    """Process PDF and add hyperlinks to all page number references."""
    doc = fitz.open(input_path)

    # Convert to 0-based indices
    start_idx = max(index_start - 1, 0)
    end_idx = min(index_end - 1, len(doc) - 1)

    logger.info(f"Processing PDF: {input_path}")
    logger.info(f"Total pages: {len(doc)}")
    logger.info(f"Index pages: {index_start}–{index_end}")
    logger.info("=" * 60)

    total_links = 0
    skipped = 0

    for page_idx in range(start_idx, end_idx + 1):
        page = doc[page_idx]
        blocks = page.get_text("dict")["blocks"]
        page_links = 0

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    raw_text = span["text"]
                    text = raw_text.strip()

                    if not text:
                        continue

                    # Only consider spans that look like page cells
                    if not page_cell_pattern.fullmatch(text):
                        continue

                    ranges = parse_page_ranges(text)
                    if not ranges:
                        continue

                    # Span bbox
                    x0, y0, x1, y1 = span["bbox"]
                    width = x1 - x0

                    # Work with the EXACT text as in span (not stripped)
                    span_text = raw_text

                    for range_text, target_page in ranges:
                        target_idx = target_page - 1

                        if target_idx < 0 or target_idx >= len(doc):
                            logger.debug(
                                f"  Page {page_idx+1}: "
                                f"skip '{range_text}' -> invalid page {target_page}"
                            )
                            skipped += 1
                            continue

                        # Find textual position of this range_text inside span_text
                        start_pos = span_text.find(range_text)

                        if start_pos == -1:
                            # Fallback: link entire span
                            rect = fitz.Rect(x0, y0, x1, y1)
                        else:
                            # Approximate width proportionally by character count
                            span_len = max(len(span_text), 1)
                            start_ratio = start_pos / span_len
                            end_ratio = (start_pos + len(range_text)) / span_len

                            sub_x0 = x0 + width * start_ratio
                            sub_x1 = x0 + width * end_ratio
                            rect = fitz.Rect(sub_x0, y0, sub_x1, y1)

                        try:
                            page.insert_link(
                                {"kind": fitz.LINK_GOTO, "page": target_idx, "from": rect}
                            )
                            total_links += 1
                            page_links += 1
                        except Exception as e:
                            logger.error(
                                f"  Page {page_idx+1}: error linking '{range_text}': {e}"
                            )
                            skipped += 1

        if page_links:
            logger.debug(f"Page {page_idx+1}: added {page_links} links")

    logger.info("=" * 60)
    logger.info(f"TOTAL LINKS ADDED: {total_links}")
    logger.info(f"SKIPPED / ERRORS: {skipped}")

    doc.save(output_path)
    doc.close()

    logger.info(f"\nSaved as: {output_path}")

def add_hyperlinks():
    """Main function to add hyperlinks to the chronology PDF."""
    logger.info("=" * 80)
    logger.info("STEP 6: ADD HYPERLINKS TO PAGE NUMBERS")
    logger.info("=" * 80)

    try:
        out_dir = Path(OUTPUT_FOLDER)

        # Load page structure from Step 5
        structure_file = out_dir / "page_structure.json"
        if not structure_file.exists():
            raise FileNotFoundError(f"Page structure not found. Run Step 5 first: {structure_file}")

        with open(structure_file, "r", encoding="utf-8") as f:
            page_structure = json.load(f)

        # Input and output paths
        input_pdf = out_dir / "final_chronology.pdf"
        output_pdf = out_dir / "Final_Chronology.pdf"

        if not input_pdf.exists():
            raise FileNotFoundError(f"Input PDF not found. Run Step 5 first: {input_pdf}")

        # Get table page range
        table_start = page_structure["table_start"]
        table_pages = page_structure["table_pages"]
        separator_page = page_structure["separator_page"]

        # Index end is just before separator
        index_end = separator_page - 1

        logger.info(f"Input: {input_pdf}")
        logger.info(f"Output: {output_pdf}")
        logger.info(f"Table pages: {table_start} to {index_end}")

        # Process PDF
        process_pdf(
            str(input_pdf),
            str(output_pdf),
            table_start,
            index_end
        )

        logger.info("\n" + "=" * 80)
        logger.info("✓ Step 6 Complete: Hyperlinks added successfully")
        logger.info(f"✓ Final output: {output_pdf}")
        logger.info("=" * 80)

        return str(output_pdf)

    except Exception as e:
        logger.error(f"Step 6 FAILED: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    add_hyperlinks()
