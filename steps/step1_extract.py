"""
STEP 1: Extract and Filter Pages from JSON

- Reads JSON with events[].sources[].source and events[].sources[].pages
- Finds PDFs in PDF_ROOT_FOLDER recursively
- Extracts ONLY referenced pages into trimmed_pages/
- Creates page mapping for later steps
"""
import json
import logging
from pathlib import Path
from collections import defaultdict
from pypdf import PdfReader, PdfWriter

# Import from parent config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import JSON_INPUT_PATH, PDF_ROOT_FOLDER, TRIMMED_PAGES_FOLDER, LOG_LEVEL, LOG_FILE, setup_folders

def setup_logging():
    """Configure logging."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logger = logging.getLogger("Step1_Extract")
    logger.setLevel(getattr(logging, LOG_LEVEL))

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(log_format))
    logger.addHandler(ch)

    if LOG_FILE:
        fh = logging.FileHandler(LOG_FILE.replace(".log", "_step1.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format))
        logger.addHandler(fh)

    return logger

logger = setup_logging()

def find_pdf_path(source_name, pdf_root):
    """Find PDF by searching recursively in pdf_root."""
    pdf_root = Path(pdf_root).resolve()

    # Try exact path first
    candidate = pdf_root / source_name
    if candidate.exists() and candidate.is_file():
        return candidate

    # Search recursively by filename
    fname = Path(source_name).name
    matches = list(pdf_root.rglob(fname))
    if matches:
        return matches[0]

    return None

def extract_pages():
    """Extract referenced pages from all PDFs."""
    logger.info("=" * 80)
    logger.info("STEP 1: EXTRACT REFERENCED PAGES FROM PDFs")
    logger.info("=" * 80)

    try:
        setup_folders()

        # Verify inputs exist
        if not Path(JSON_INPUT_PATH).exists():
            raise FileNotFoundError(f"JSON file not found: {JSON_INPUT_PATH}")
        if not Path(PDF_ROOT_FOLDER).exists():
            raise FileNotFoundError(f"PDF folder not found: {PDF_ROOT_FOLDER}")

        logger.info(f"JSON file: {JSON_INPUT_PATH}")
        logger.info(f"PDF root: {Path(PDF_ROOT_FOLDER).resolve()}")
        logger.info(f"Output: {TRIMMED_PAGES_FOLDER}")

        # Load JSON
        with open(JSON_INPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        events = data.get("events", [])
        logger.info(f"Loaded {len(events)} events from JSON")

        if not events:
            raise ValueError("No 'events' found in JSON")

        # Build extraction plan: source_name -> set of page numbers
        extraction_plan = defaultdict(set)
        pdf_paths_cache = {}

        for ev_idx, event in enumerate(events):
            for source in event.get("sources", []):
                source_name = source.get("source") or source.get("document", "")
                pages = source.get("pages", [])

                if not source_name or not pages:
                    continue

                # Find PDF path (cache it)
                if source_name not in pdf_paths_cache:
                    pdf_path = find_pdf_path(source_name, PDF_ROOT_FOLDER)
                    pdf_paths_cache[source_name] = pdf_path

                pdf_path = pdf_paths_cache[source_name]
                if not pdf_path:
                    logger.warning(f"PDF not found: {source_name}")
                    continue

                # Add pages to extraction plan
                for page in pages:
                    try:
                        extraction_plan[source_name].add(int(page))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid page number '{page}' in {source_name}")

        logger.info(f"Found {len(extraction_plan)} unique PDFs to process")

        if not extraction_plan:
            logger.warning("No pages to extract! Check your JSON file.")
            return TRIMMED_PAGES_FOLDER

        # Extract pages per PDF
        detailed_mappings = []
        extracted_files_meta = []
        out_dir = Path(TRIMMED_PAGES_FOLDER)
        out_dir.mkdir(parents=True, exist_ok=True)

        for source_name, pages_set in extraction_plan.items():
            pdf_path = pdf_paths_cache[source_name]
            sorted_pages = sorted(pages_set)

            logger.info(f"\nProcessing: {source_name}")
            logger.info(f"  Path: {pdf_path}")
            logger.info(f"  Pages: {len(sorted_pages)}")

            try:
                reader = PdfReader(str(pdf_path))
                writer = PdfWriter()

                for original_page_num in sorted_pages:
                    idx = original_page_num - 1  # Convert 1-based to 0-based
                    if 0 <= idx < len(reader.pages):
                        writer.add_page(reader.pages[idx])
                        extracted_index = len(writer.pages) - 1
                        detailed_mappings.append({
                            "source_file": source_name,
                            "original_page": original_page_num,
                            "extracted_index": extracted_index,
                        })
                    else:
                        logger.warning(f"  Page {original_page_num} out of range (PDF has {len(reader.pages)} pages)")

                if len(writer.pages) == 0:
                    logger.warning(f"  No valid pages extracted, skipping")
                    continue

                # Save trimmed PDF
                safe_name = source_name.replace("\\", "_").replace("/", "_")
                out_pdf = out_dir / safe_name
                with open(out_pdf, "wb") as f:
                    writer.write(f)

                extracted_files_meta.append({
                    "source_name": source_name,
                    "trimmed_file": str(out_pdf),
                    "original_pages": len(reader.pages),
                    "extracted_pages": len(writer.pages),
                    "pages_list": sorted_pages,
                })

                logger.info(f"  ✓ Saved: {safe_name} ({len(writer.pages)} pages)")

            except Exception as e:
                logger.error(f"  ✗ Failed to process {source_name}: {e}", exc_info=True)

        # Save mappings
        mapping_file = out_dir / "detailed_page_mapping.json"
        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump({"page_mappings": detailed_mappings}, f, indent=2, ensure_ascii=False)

        meta_file = out_dir / "extraction_metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "total_events": len(events),
                "total_pdfs_extracted": len(extracted_files_meta),
                "extracted_files": extracted_files_meta,
            }, f, indent=2, ensure_ascii=False)

        logger.info("\n" + "=" * 80)
        logger.info(f"✓ Step 1 Complete: Extracted {len(extracted_files_meta)} trimmed PDFs")
        logger.info(f"  Page mappings: {mapping_file}")
        logger.info(f"  Metadata: {meta_file}")
        logger.info("=" * 80)

        return TRIMMED_PAGES_FOLDER

    except Exception as e:
        logger.error(f"Step 1 FAILED: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    extract_pages()
