"""
STEP 5: Final Merge - Synopsis + Table + Separator + Documents

- Uses TWO-PASS approach to calculate correct page offsets:
  Pass 1: Generate table with offset=0 to get page count
  Pass 2: Calculate offset, regenerate table with correct page numbers
- Merges: [Synopsis] + Table PDF + Separator + Merged documents PDF
- Output: final_chronology.pdf
"""
import json
import logging
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Import from parent config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_FOLDER, SYNOPSIS_PDF, LOG_LEVEL, LOG_FILE, setup_folders

# Import create_table_pdf from step4 for two-pass approach
from . import step4_create_table

def setup_logging():
    """Configure logging."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logger = logging.getLogger("Step5_FinalMerge")
    logger.setLevel(getattr(logging, LOG_LEVEL))
    logger.handlers.clear()

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(log_format))
    logger.addHandler(ch)

    if LOG_FILE:
        fh = logging.FileHandler(LOG_FILE.replace(".log", "_step5.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format))
        logger.addHandler(fh)

    return logger

logger = setup_logging()

def create_separator_page(title="Source Documents"):
    """Create a separator page PDF."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header background
    c.setFillColorRGB(31/255, 78/255, 120/255)  # Dark blue
    c.rect(0, height - 100, width, 100, fill=1, stroke=0)

    # Title text
    c.setFillColorRGB(1, 1, 1)  # White
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2, height - 60, title)

    # Subtitle
    c.setFillColorRGB(0, 0, 0)  # Black
    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, height - 180, "Medical Records and Supporting Documentation")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def final_merge():
    """Merge synopsis + table + separator + documents with correct page offsets."""
    logger.info("=" * 80)
    logger.info("STEP 5: FINAL MERGE - CHRONOLOGY PDF")
    logger.info("=" * 80)

    try:
        setup_folders()
        out_dir = Path(OUTPUT_FOLDER)

        # Check required files
        merged_pdf = out_dir / "merged_index.pdf"
        if not merged_pdf.exists():
            raise FileNotFoundError(f"Merged PDF not found. Run Step 2 first: {merged_pdf}")

        # Get synopsis page count
        synopsis_reader = None
        synopsis_pages = 0
        if SYNOPSIS_PDF and Path(SYNOPSIS_PDF).exists():
            logger.info(f"Synopsis PDF: {SYNOPSIS_PDF}")
            synopsis_reader = PdfReader(SYNOPSIS_PDF)
            synopsis_pages = len(synopsis_reader.pages)
            logger.info(f"  Pages: {synopsis_pages}")
        else:
            logger.info("No synopsis PDF (skipping)")

        # ================================================================
        # TWO-PASS TABLE GENERATION FOR CORRECT PAGE OFFSETS
        # ================================================================

        logger.info("\n" + "-" * 60)
        logger.info("PASS 1: Generate table to determine page count...")
        logger.info("-" * 60)

        # Pass 1: Generate table with offset=0 to get page count
        _, table_pages_pass1 = step4_create_table.create_table_pdf(page_offset=0)
        logger.info(f"Pass 1 table pages: {table_pages_pass1}")

        # Calculate offset: synopsis + table + separator(1)
        separator_pages = 1
        page_offset = synopsis_pages + table_pages_pass1 + separator_pages

        logger.info(f"\nCalculated page offset: {page_offset}")
        logger.info(f"  Synopsis: {synopsis_pages} pages")
        logger.info(f"  Table: {table_pages_pass1} pages")
        logger.info(f"  Separator: {separator_pages} page")
        logger.info(f"  Documents will start at page: {page_offset + 1}")

        logger.info("\n" + "-" * 60)
        logger.info("PASS 2: Regenerate table with correct page offset...")
        logger.info("-" * 60)

        # Pass 2: Regenerate table with correct offset
        table_pdf_path, table_pages = step4_create_table.create_table_pdf(page_offset=page_offset)

        # Verify page count didn't change significantly
        if table_pages != table_pages_pass1:
            logger.warning(f"Table page count changed: {table_pages_pass1} -> {table_pages}")
            # Recalculate offset if needed (rare case)
            new_offset = synopsis_pages + table_pages + separator_pages
            if new_offset != page_offset:
                logger.info(f"Adjusting offset: {page_offset} -> {new_offset}")
                page_offset = new_offset
                # Third pass if necessary
                _, table_pages = step4_create_table.create_table_pdf(page_offset=page_offset)

        # ================================================================
        # FINAL MERGE
        # ================================================================

        logger.info("\n" + "-" * 60)
        logger.info("MERGING FINAL PDF...")
        logger.info("-" * 60)

        # Load table PDF
        table_reader = PdfReader(table_pdf_path)
        table_pages = len(table_reader.pages)
        logger.info(f"Table PDF: {table_pdf_path}")
        logger.info(f"  Pages: {table_pages}")

        # Load merged documents PDF
        logger.info(f"Merged PDF: {merged_pdf}")
        merged_reader = PdfReader(str(merged_pdf))
        merged_pages = len(merged_reader.pages)
        logger.info(f"  Pages: {merged_pages}")

        # Create final PDF
        logger.info("\nBuilding final PDF...")
        final_writer = PdfWriter()

        # Track page structure for hyperlinks (Step 6)
        page_structure = {
            "synopsis_start": 1,
            "synopsis_pages": synopsis_pages,
            "table_start": synopsis_pages + 1,
            "table_pages": table_pages,
            "separator_page": synopsis_pages + table_pages + 1,
            "documents_start": synopsis_pages + table_pages + 2,
            "documents_pages": merged_pages,
        }

        current_page = 0

        # 1. Add synopsis pages (if available)
        if synopsis_reader:
            logger.info(f"Adding synopsis (pages 1-{synopsis_pages})...")
            for page in synopsis_reader.pages:
                final_writer.add_page(page)
                current_page += 1

        # 2. Add table pages
        table_start = current_page + 1
        logger.info(f"Adding table (pages {table_start}-{table_start + table_pages - 1})...")
        for page in table_reader.pages:
            final_writer.add_page(page)
            current_page += 1

        # 3. Add separator page
        separator_page_num = current_page + 1
        logger.info(f"Adding separator (page {separator_page_num})...")
        sep_buffer = create_separator_page("Source Documents")
        sep_reader = PdfReader(sep_buffer)
        for page in sep_reader.pages:
            final_writer.add_page(page)
            current_page += 1

        # 4. Add merged document pages
        docs_start = current_page + 1
        docs_end = docs_start + merged_pages - 1
        logger.info(f"Adding documents (pages {docs_start}-{docs_end})...")
        for page in merged_reader.pages:
            final_writer.add_page(page)
            current_page += 1

        # Save final PDF
        final_pdf_path = out_dir / "final_chronology.pdf"
        with open(final_pdf_path, "wb") as f:
            final_writer.write(f)

        total_pages = len(final_writer.pages)
        size_mb = final_pdf_path.stat().st_size / (1024 * 1024)

        # Update page structure with actual values
        page_structure["total_pages"] = total_pages
        page_structure["documents_start"] = docs_start
        page_structure["page_offset_applied"] = page_offset

        # Save page structure for Step 6 (hyperlinks)
        structure_file = out_dir / "page_structure.json"
        with open(structure_file, "w", encoding="utf-8") as f:
            json.dump(page_structure, f, indent=2)

        logger.info(f"\n✓ Final PDF: {final_pdf_path}")
        logger.info(f"  Total pages: {total_pages}")
        logger.info(f"  Size: {size_mb:.2f} MB")
        logger.info(f"\nPage Structure:")
        if synopsis_pages > 0:
            logger.info(f"  Synopsis: Pages 1-{synopsis_pages}")
        logger.info(f"  Table: Pages {page_structure['table_start']}-{page_structure['table_start'] + table_pages - 1}")
        logger.info(f"  Separator: Page {page_structure['separator_page']}")
        logger.info(f"  Documents: Pages {docs_start}-{total_pages}")
        logger.info(f"\n✓ Page numbers in table correctly offset by {page_offset}")
        logger.info(f"✓ Page structure saved: {structure_file}")

        logger.info("\n" + "=" * 80)
        logger.info("✓ Step 5 Complete: Final PDF created")
        logger.info("=" * 80)

        return str(final_pdf_path)

    except Exception as e:
        logger.error(f"Step 5 FAILED: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    final_merge()
