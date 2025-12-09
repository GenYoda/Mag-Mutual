"""
STEP 4: Create Professional PDF Table

- Reads timeline_updated.json
- Creates a formatted table PDF with proper column layout
- Supports page_offset parameter for correct final PDF page numbers
- Auto-wrapping text
- Output: table_report.pdf
"""
import json
import logging
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Import from parent config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_FOLDER, LOG_LEVEL, LOG_FILE, setup_folders

def setup_logging():
    """Configure logging."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logger = logging.getLogger("Step4_Table")
    logger.setLevel(getattr(logging, LOG_LEVEL))
    logger.handlers.clear()

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(log_format))
    logger.addHandler(ch)

    if LOG_FILE:
        fh = logging.FileHandler(LOG_FILE.replace(".log", "_step4.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format))
        logger.addHandler(fh)

    return logger

logger = setup_logging()

def format_consecutive_ranges(pages, offset=0):
    """
    Convert a list of page numbers to consecutive ranges with offset.
    Example: [1,2,3,4,43,45,46,47] with offset=15 -> "16-19, 58, 60-62"
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
            range_end = sorted_pages[i]
        else:
            if range_start == range_end:
                ranges.append(str(range_start))
            else:
                ranges.append(f"{range_start}-{range_end}")
            range_start = sorted_pages[i]
            range_end = sorted_pages[i]

    if range_start == range_end:
        ranges.append(str(range_start))
    else:
        ranges.append(f"{range_start}-{range_end}")

    return ", ".join(ranges)

def create_table_pdf(page_offset=0):
    """
    Create PDF table from timeline JSON.

    Args:
        page_offset: Number of pages before documents in final PDF.
                    Page numbers will be adjusted by this offset.
                    Default=0 for first pass to determine table page count.

    Returns:
        tuple: (pdf_path, page_count)
    """
    logger.info("=" * 80)
    logger.info("STEP 4: CREATE TABLE PDF")
    if page_offset > 0:
        logger.info(f"  (Page offset: {page_offset})")
    logger.info("=" * 80)

    try:
        setup_folders()
        out_dir = Path(OUTPUT_FOLDER)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Load JSON
        timeline_file = out_dir / "timeline_updated.json"
        if not timeline_file.exists():
            raise FileNotFoundError(f"Timeline not found. Run Step 3 first: {timeline_file}")

        logger.info(f"Loading: {timeline_file}")
        with open(timeline_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        timeline_data = data.get("medical_timeline", [])
        logger.info(f"Loaded {len(timeline_data)} entries")

        if not timeline_data:
            raise ValueError("No timeline data found in JSON")

        # Create styles
        styles = getSampleStyleSheet()

        # Colors
        color_header = colors.HexColor("#1F4E78")
        color_text_header = colors.white
        color_white = colors.white
        color_light = colors.HexColor("#F8F8F8")
        color_border = colors.HexColor("#CCCCCC")
        color_link = colors.HexColor("#0066CC")

        # Header style
        header_style = ParagraphStyle(
            "CustomHeader",
            parent=styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=color_text_header,
            alignment=TA_CENTER,
            leading=10,
        )

        # Cell style with word wrap
        cell_style = ParagraphStyle(
            "CustomCell",
            parent=styles["Normal"],
            fontSize=8,
            fontName="Helvetica",
            textColor=colors.black,
            alignment=TA_LEFT,
            leading=9,
            wordWrap="CJK",
            splitLongWords=True,
        )

        # Date style - centered
        date_style = ParagraphStyle(
            "DateCell",
            parent=cell_style,
            fontSize=8,
            alignment=TA_CENTER,
        )

        # Page link style
        page_link_style = ParagraphStyle(
            "PageLink",
            parent=styles["Normal"],
            fontSize=7,
            fontName="Courier-Bold",
            textColor=color_link,
            alignment=TA_CENTER,
        )

        # Build table data
        logger.info("Creating table...")

        # Column widths
        col_widths = [
            0.9 * inch,   # Date
            1.1 * inch,   # Facility
            1.1 * inch,   # Provider
            1.2 * inch,   # Title
            0.7 * inch,   # Page #
            3.25 * inch,  # Notes
        ]

        # Headers
        headers = ["Date", "Facility", "Provider", "Title", "Page #", "Notes"]
        table_data = [[Paragraph(h, header_style) for h in headers]]

        # Data rows
        for idx, entry in enumerate(timeline_data):
            date_val = str(entry.get("date", "")).strip()
            facility_val = str(entry.get("facility", "")).strip()
            provider_val = str(entry.get("provider", "")).strip()
            title_val = str(entry.get("title", "")).strip()
            notes_val = str(entry.get("notes", "")).strip()

            # Get page numbers with offset applied
            merged_pages = entry.get("merged_pages", [])
            if merged_pages and page_offset > 0:
                # Apply offset and format consecutive ranges
                page_val = format_consecutive_ranges(merged_pages, offset=page_offset)
            else:
                # Use pre-computed page_number (no offset or offset=0)
                page_val = str(entry.get("page_number", "")).strip()

            row = [
                Paragraph(date_val, date_style),
                Paragraph(facility_val, cell_style),
                Paragraph(provider_val, cell_style),
                Paragraph(title_val, cell_style),
                Paragraph(page_val, page_link_style),
                Paragraph(notes_val, cell_style),
            ]

            table_data.append(row)

            if (idx + 1) % 100 == 0:
                logger.debug(f"Processed {idx + 1} entries")

        logger.info(f"Table data created: {len(table_data)} rows (including header)")

        # Create table
        table = Table(
            table_data,
            colWidths=col_widths,
            repeatRows=1,
        )

        # Apply styling
        table.setStyle(TableStyle([
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), color_header),
            ("TEXTCOLOR", (0, 0), (-1, 0), color_text_header),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),

            # Data rows
            ("ALIGN", (0, 1), (0, -1), "CENTER"),  # Date
            ("ALIGN", (1, 1), (3, -1), "LEFT"),  # Facility, Provider, Title
            ("ALIGN", (4, 1), (4, -1), "CENTER"),  # Page #
            ("ALIGN", (5, 1), (5, -1), "LEFT"),  # Notes
            ("VALIGN", (0, 1), (-1, -1), "TOP"),

            # Padding
            ("LEFTPADDING", (0, 1), (-1, -1), 5),
            ("RIGHTPADDING", (0, 1), (-1, -1), 5),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),

            # Alternating colors
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [color_white, color_light]),

            # Borders
            ("GRID", (0, 0), (-1, -1), 0.5, color_border),
            ("LINEBELOW", (0, 0), (-1, 0), 2, color_header),
        ]))

        # Create PDF
        pdf_path = out_dir / "table_report.pdf"
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            rightMargin=0.2 * inch,
            leftMargin=0.2 * inch,
            topMargin=0.3 * inch,
            bottomMargin=0.3 * inch,
        )

        # Title
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=14,
            fontName="Helvetica-Bold",
            textColor=color_header,
            spaceAfter=6,
            alignment=TA_LEFT,
        )

        elements = [
            Paragraph("Medical Timeline - Chronology", title_style),
            Spacer(1, 0.1 * inch),
            table,
        ]

        logger.info("Building PDF...")
        doc.build(elements)

        # Get page count
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        page_count = len(reader.pages)

        size_mb = pdf_path.stat().st_size / (1024 * 1024)

        logger.info(f"✓ Table PDF: {pdf_path}")
        logger.info(f"  Entries: {len(timeline_data)}")
        logger.info(f"  Pages: {page_count}")
        logger.info(f"  Size: {size_mb:.2f} MB")

        if page_offset > 0:
            logger.info(f"  Page offset applied: {page_offset}")

        logger.info("\n" + "=" * 80)
        logger.info("✓ Step 4 Complete: Table PDF created")
        logger.info("=" * 80)

        return str(pdf_path), page_count

    except Exception as e:
        logger.error(f"Step 4 FAILED: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    create_table_pdf(page_offset=0)
