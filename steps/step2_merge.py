"""
STEP 2: Merge Trimmed PDFs and Create Page Mapping

- Reads trimmed PDFs from Step 1
- Merges them in order
- Creates mapping: (source_file, original_page) -> merged_page
- Output: merged_index.pdf and page_mapping.json
"""
import json
import logging
from pathlib import Path
from pypdf import PdfReader, PdfWriter

# Import from parent config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TRIMMED_PAGES_FOLDER, OUTPUT_FOLDER, LOG_LEVEL, LOG_FILE, setup_folders

def setup_logging():
    """Configure logging."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logger = logging.getLogger("Step2_Merge")
    logger.setLevel(getattr(logging, LOG_LEVEL))

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(log_format))
    logger.addHandler(ch)

    if LOG_FILE:
        fh = logging.FileHandler(LOG_FILE.replace(".log", "_step2.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format))
        logger.addHandler(fh)

    return logger

logger = setup_logging()

def merge_pdfs():
    """Merge all trimmed PDFs and create page mapping."""
    logger.info("=" * 80)
    logger.info("STEP 2: MERGE TRIMMED PDFs AND CREATE PAGE MAPPING")
    logger.info("=" * 80)

    try:
        setup_folders()
        trimmed_dir = Path(TRIMMED_PAGES_FOLDER)
        out_dir = Path(OUTPUT_FOLDER)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Load metadata from Step 1
        meta_file = trimmed_dir / "extraction_metadata.json"
        map_file = trimmed_dir / "detailed_page_mapping.json"

        if not meta_file.exists():
            raise FileNotFoundError(f"Metadata not found. Run Step 1 first: {meta_file}")
        if not map_file.exists():
            raise FileNotFoundError(f"Page mapping not found. Run Step 1 first: {map_file}")

        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        with open(map_file, "r", encoding="utf-8") as f:
            page_mapping_data = json.load(f)

        extracted_files = metadata.get("extracted_files", [])
        detailed_mappings = page_mapping_data.get("page_mappings", [])

        logger.info(f"Merging {len(extracted_files)} trimmed PDFs")
        logger.info(f"Using {len(detailed_mappings)} page mappings")

        # Build quick index: (source_file, extracted_index) -> original_page
        index = {}
        for entry in detailed_mappings:
            key = (entry["source_file"], entry["extracted_index"])
            index[key] = entry["original_page"]

        # Merge PDFs
        writer = PdfWriter()
        page_mapping = []
        merged_page_num = 1  # 1-based

        for file_info in extracted_files:
            trimmed_path = Path(file_info["trimmed_file"])
            source_name = file_info["source_name"]

            if not trimmed_path.exists():
                logger.warning(f"Trimmed PDF not found: {trimmed_path}")
                continue

            logger.info(f"\nAdding: {source_name}")
            logger.info(f"  File: {trimmed_path.name}")

            reader = PdfReader(str(trimmed_path))
            for extracted_idx, page in enumerate(reader.pages):
                writer.add_page(page)

                # Find original page number
                original_page = index.get((source_name, extracted_idx))
                if original_page is not None:
                    page_mapping.append({
                        "source_file": source_name,
                        "original_page": original_page,
                        "merged_page": merged_page_num,
                    })
                merged_page_num += 1

            logger.info(f"  ✓ Added {len(reader.pages)} pages")

        # Save merged PDF
        merged_pdf_path = out_dir / "merged_index.pdf"
        with open(merged_pdf_path, "wb") as f:
            writer.write(f)

        total_pages = len(writer.pages)
        size_mb = merged_pdf_path.stat().st_size / (1024 * 1024)

        logger.info(f"\n✓ Merged PDF: {merged_pdf_path}")
        logger.info(f"  Pages: {total_pages}")
        logger.info(f"  Size: {size_mb:.2f} MB")

        # Save page mapping
        mapping_out = out_dir / "page_mapping.json"
        with open(mapping_out, "w", encoding="utf-8") as f:
            json.dump({
                "page_mapping": page_mapping,
                "total_pages": total_pages,
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Page mapping: {mapping_out}")

        if page_mapping:
            logger.info(f"\nSample mappings (first 5):")
            for m in page_mapping[:5]:
                logger.info(f"  {m['source_file']} page {m['original_page']} -> merged page {m['merged_page']}")

        logger.info("\n" + "=" * 80)
        logger.info("✓ Step 2 Complete: PDFs merged successfully")
        logger.info("=" * 80)

        return str(merged_pdf_path)

    except Exception as e:
        logger.error(f"Step 2 FAILED: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    merge_pdfs()
