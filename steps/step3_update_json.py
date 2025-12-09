"""
STEP 3: Update JSON with Merged Page Numbers

- Reads original JSON
- Maps original page numbers to merged page numbers
- Creates timeline_updated.json with CONSECUTIVE page ranges
"""
import json
import logging
from pathlib import Path
from collections import defaultdict

# Import from parent config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import JSON_INPUT_PATH, OUTPUT_FOLDER, LOG_LEVEL, LOG_FILE, setup_folders

def setup_logging():
    """Configure logging."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logger = logging.getLogger("Step3_UpdateJSON")
    logger.setLevel(getattr(logging, LOG_LEVEL))
    logger.handlers.clear()

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(log_format))
    logger.addHandler(ch)

    if LOG_FILE:
        fh = logging.FileHandler(LOG_FILE.replace(".log", "_step3.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format))
        logger.addHandler(fh)

    return logger

logger = setup_logging()

def load_page_mapping(mapping_file):
    """Load page mapping from Step 2."""
    logger.info(f"Loading page mapping: {mapping_file}")
    with open(mapping_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build lookup: source_file -> {original_page -> merged_page}
    mapping = defaultdict(dict)
    for entry in data.get("page_mapping", []):
        source_file = entry["source_file"]
        original_page = entry["original_page"]
        merged_page = entry["merged_page"]
        mapping[source_file][original_page] = merged_page

    logger.info(f"Loaded mappings for {len(mapping)} documents")
    return mapping

def format_consecutive_ranges(pages, offset=0):
    """
    Convert a list of page numbers to consecutive ranges with optional offset.
    Example: [1,2,3,4,43,45,46,47,354,356] with offset=0 -> "1-4, 43, 45-47, 354, 356"
    Example: [1,2,3] with offset=15 -> "16-18"
    """
    if not pages:
        return ""

    # Apply offset and sort
    sorted_pages = sorted(set(p + offset for p in pages))

    if len(sorted_pages) == 1:
        return str(sorted_pages[0])

    ranges = []
    range_start = sorted_pages[0]
    range_end = sorted_pages[0]

    for i in range(1, len(sorted_pages)):
        if sorted_pages[i] == range_end + 1:
            # Consecutive - extend current range
            range_end = sorted_pages[i]
        else:
            # Gap found - close current range and start new
            if range_start == range_end:
                ranges.append(str(range_start))
            else:
                ranges.append(f"{range_start}-{range_end}")
            range_start = sorted_pages[i]
            range_end = sorted_pages[i]

    # Don't forget the last range
    if range_start == range_end:
        ranges.append(str(range_start))
    else:
        ranges.append(f"{range_start}-{range_end}")

    return ", ".join(ranges)

def get_merged_pages(sources, page_mapping):
    """
    Convert sources[].pages to merged page numbers.
    Returns: (merged_pages_list, page_range_string)
    Note: page_range_string uses offset=0 here; offset applied in Step 4/5
    """
    all_merged_pages = []
    for source in sources:
        source_name = source.get("source") or source.get("document", "")
        pages = source.get("pages", [])

        for page in pages:
            try:
                page_num = int(page)
            except (ValueError, TypeError):
                continue

            if source_name in page_mapping and page_num in page_mapping[source_name]:
                merged_page = page_mapping[source_name][page_num]
                all_merged_pages.append(merged_page)

    if not all_merged_pages:
        return [], ""

    # Sort pages
    all_merged_pages.sort()

    # Create consecutive range string (offset=0, will be applied later)
    page_range = format_consecutive_ranges(all_merged_pages, offset=0)

    return all_merged_pages, page_range

def update_json():
    """Update JSON with merged page numbers."""
    logger.info("=" * 80)
    logger.info("STEP 3: UPDATE JSON WITH MERGED PAGE NUMBERS")
    logger.info("=" * 80)

    try:
        setup_folders()

        # Load page mapping from Step 2
        mapping_file = Path(OUTPUT_FOLDER) / "page_mapping.json"
        if not mapping_file.exists():
            raise FileNotFoundError(f"Page mapping not found. Run Step 2 first: {mapping_file}")

        page_mapping = load_page_mapping(str(mapping_file))

        # Load original JSON
        logger.info(f"Loading JSON: {JSON_INPUT_PATH}")
        with open(JSON_INPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        events = data.get("events", [])
        logger.info(f"Found {len(events)} events")

        # Build timeline
        timeline = []
        updated_count = 0
        missing_count = 0

        for idx, event in enumerate(events):
            date = event.get("date", "")
            facility = event.get("facility", "")
            provider = event.get("provider", "")
            title = event.get("title", "")
            notes = event.get("notes", "")
            sources = event.get("sources", [])

            # Get merged pages
            merged_pages, page_range = get_merged_pages(sources, page_mapping)

            if merged_pages:
                updated_count += 1
            else:
                missing_count += 1
                if idx < 5:
                    logger.debug(f"Event {idx}: No page mapping found")

            timeline.append({
                "date": date,
                "facility": facility,
                "provider": provider,
                "title": title,
                "notes": notes,
                "page_number": page_range,  # Display format with consecutive ranges
                "merged_pages": merged_pages,  # Raw page numbers (for offset calculation)
                "sources": sources,
            })

            if (idx + 1) % 100 == 0:
                logger.debug(f"Processed {idx + 1} events")

        # Save updated JSON
        out_dir = Path(OUTPUT_FOLDER)
        out_dir.mkdir(parents=True, exist_ok=True)
        output_file = out_dir / "timeline_updated.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "medical_timeline": timeline,
                "metadata": {
                    "total_events": len(timeline),
                    "events_with_pages": updated_count,
                    "events_without_pages": missing_count,
                },
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"\n✓ Timeline updated: {output_file}")
        logger.info(f"  Total entries: {len(timeline)}")
        logger.info(f"  With pages: {updated_count}")
        logger.info(f"  Without pages: {missing_count}")
        logger.info("\n" + "=" * 80)
        logger.info("✓ Step 3 Complete: JSON updated with merged page numbers")
        logger.info("=" * 80)

        return str(output_file)

    except Exception as e:
        logger.error(f"Step 3 FAILED: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    update_json()
