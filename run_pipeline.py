#!/usr/bin/env python3
"""
Chronology PDF Generator - Main Pipeline Runner

This script runs all 6 steps to generate a complete chronology PDF:
1. Extract pages from source PDFs
2. Merge extracted pages
3. Update JSON with merged page numbers
4. Create table PDF
5. Final merge (synopsis + table + separator + documents)
6. Add hyperlinks to page numbers

Usage:
    python run_pipeline.py [--skip-step STEP_NUM]

Example:
    python run_pipeline.py              # Run all steps
    python run_pipeline.py --skip-step 6  # Run steps 1-5 only
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import config first
import config

# Import all step modules
from steps import step1_extract
from steps import step2_merge
from steps import step3_update_json
from steps import step4_create_table
from steps import step5_final_merge
from steps import step6_hyperlink

def setup_main_logger():
    """Setup main pipeline logger."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logger = logging.getLogger("MainPipeline")
    logger.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(log_format))
    logger.addHandler(ch)

    # File handler
    if config.LOG_FILE:
        fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format))
        logger.addHandler(fh)

    return logger

def print_banner():
    """Print startup banner."""
    banner = f"""
{'='*80}
    CHRONOLOGY PDF GENERATOR - PIPELINE
{'='*80}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Configuration:
    - JSON Input: {config.JSON_INPUT_PATH}
    - Data Folder: {config.DATA_FOLDER}
    - Synopsis PDF: {config.SYNOPSIS_PDF or 'None (skipped)'}
    - Output Folder: {config.OUTPUT_FOLDER}
{'='*80}
"""
    print(banner)

def run_pipeline(skip_steps=None):
    """Run the complete pipeline."""
    logger = setup_main_logger()
    skip_steps = skip_steps or []

    print_banner()

    steps = [
        (1, "Extract Pages", step1_extract.extract_pages),
        (2, "Merge PDFs", step2_merge.merge_pdfs),
        (3, "Update JSON", step3_update_json.update_json),
        (4, "Create Table", step4_create_table.create_table_pdf),
        (5, "Final Merge", step5_final_merge.final_merge),
        (6, "Add Hyperlinks", step6_hyperlink.add_hyperlinks),
    ]

    start_time = datetime.now()
    completed_steps = []

    try:
        for step_num, step_name, step_func in steps:
            if step_num in skip_steps:
                logger.info(f"\n⏭️  SKIPPING Step {step_num}: {step_name}")
                continue

            logger.info(f"\n{'='*80}")
            logger.info(f"▶️  STARTING Step {step_num}: {step_name}")
            logger.info(f"{'='*80}")

            try:
                result = step_func()
                completed_steps.append(step_num)
                logger.info(f"✓ Step {step_num} completed successfully")

            except Exception as e:
                logger.error(f"✗ Step {step_num} FAILED: {e}", exc_info=True)
                raise

        # Final summary
        elapsed = datetime.now() - start_time
        print(f"\n{'='*80}")
        print(f"✓ PIPELINE COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")
        print(f"  Steps completed: {len(completed_steps)}/{len(steps)}")
        print(f"  Time elapsed: {elapsed}")
        print(f"  Output folder: {config.OUTPUT_FOLDER}")
        print(f"\n📄 Final output: {Path(config.OUTPUT_FOLDER) / 'Final_Chronology.pdf'}")
        print(f"{'='*80}\n")

        return True

    except Exception as e:
        elapsed = datetime.now() - start_time
        print(f"\n{'='*80}")
        print(f"✗ PIPELINE FAILED")
        print(f"{'='*80}")
        print(f"  Error: {e}")
        print(f"  Steps completed: {len(completed_steps)}/{len(steps)}")
        print(f"  Time elapsed: {elapsed}")
        print(f"{'='*80}\n")
        return False

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the complete chronology PDF generation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                    # Run all 6 steps
  python run_pipeline.py --skip-step 6      # Skip hyperlink generation
        """
    )

    parser.add_argument(
        '--skip-step',
        type=int,
        action='append',
        dest='skip_steps',
        help='Skip specific step number (can be used multiple times)'
    )

    args = parser.parse_args()

    # Run pipeline
    success = run_pipeline(skip_steps=args.skip_steps or [])

    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
