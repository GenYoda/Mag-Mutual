"""
Complete Pipeline Runner - Medical Chronology Generation

Runs the full chronology generation pipeline:
1. Pass 1: Event extraction from knowledge base (all years)
2. Pass 2: Event enrichment and merging (all years)
3. Consolidation: Combine all years into final JSON files in chronology_result/

Usage:
    python run_full_pipeline.py
    python run_full_pipeline.py --years 2019 2020
    python run_full_pipeline.py --rebuild
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Import from chronology_engine folder
from chronology_engine.pass1_window2 import WindowedPass1Extractor
from chronology_engine.pass2_enricher import Pass2Enricher
from chronology_engine.consolidate_result import run_consolidation
import config

def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(step: int, total: int, text: str):
    """Print a step header"""
    print(f"\n[Step {step}/{total}] {text}")
    print("-"*70)

def run_full_pipeline(years=None, rebuild=False, kb_path='knowledge_base'):
    """
    Run the complete chronology generation pipeline

    Args:
        years: List of years to process (e.g., [2019, 2020]). None = all years
        rebuild: Whether to rebuild from scratch
        kb_path: Path to knowledge base folder
    """
    start_time = datetime.now()

    print_header("MEDICAL CHRONOLOGY GENERATION PIPELINE")

    print(f"\nConfiguration:")
    print(f"  Knowledge base: {kb_path}")
    print(f"  Output directory: {config.OUTPUT_DIR}")
    print(f"  Years: {', '.join(map(str, years)) if years else 'All'}")
    print(f"  Rebuild: {rebuild}")

    total_steps = 3  # Pass 1 + Pass 2 + Consolidation
    current_step = 0

    # ========================================================================
    # STEP 1: Pass 1 - Event Extraction
    # ========================================================================
    current_step += 1
    print_step(current_step, total_steps, "PASS 1: EVENT EXTRACTION")

    try:
        print(f"\nInitializing Pass 1 Extractor...")
        extractor = WindowedPass1Extractor()

        print(f"\nRunning extraction for {'all years' if not years else f'years {years}'}...")
        extractor.run(years=years)

        print(f"\n✓ Pass 1 completed successfully")

    except Exception as e:
        print(f"\n✗ Pass 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # STEP 2: Pass 2 - Event Enrichment
    # ========================================================================
    current_step += 1
    print_step(current_step, total_steps, "PASS 2: EVENT ENRICHMENT & MERGING")

    try:
        # Find all Pass 1 files
        pass1_files = list(Path(config.OUTPUT_DIR).glob("pass1_*.json"))

        if not pass1_files:
            print(f"\n✗ No Pass 1 files found in {config.OUTPUT_DIR}/")
            return False

        print(f"\nFound {len(pass1_files)} Pass 1 file(s) to enrich:")
        for f in pass1_files:
            print(f"  - {f.name}")

        enricher = Pass2Enricher()

        for i, pass1_file in enumerate(pass1_files, 1):
            print(f"\n{'='*70}")
            print(f"  Enriching {i}/{len(pass1_files)}: {pass1_file.name}")
            print(f"{'='*70}")

            success = enricher.process_file(str(pass1_file))
            if not success:
                print(f"  ⚠ Warning: Failed to enrich {pass1_file.name}")

        print(f"\n✓ Pass 2 completed successfully")

    except Exception as e:
        print(f"\n✗ Pass 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # STEP 3: Consolidation - Create Final Combined Files
    # ========================================================================
    current_step += 1
    print_step(current_step, total_steps, "CONSOLIDATION: Creating Combined Results")

    try:
        # Create chronology_result directory
        result_dir = Path("chronology_result")
        result_dir.mkdir(exist_ok=True)

        print(f"\nCreating combined files in: {result_dir}/")

        # Temporarily change output dir for consolidation
        original_output_dir = config.OUTPUT_DIR

        # Run consolidation for both Pass 1 and Pass 2
        print(f"\n{'='*70}")
        print(f"  Consolidating Pass 1 Results")
        print(f"{'='*70}")

        success_pass1 = run_consolidation(pass1=True, pass2=False)

        print(f"\n{'='*70}")
        print(f"  Consolidating Pass 2 Results")
        print(f"{'='*70}")

        success_pass2 = run_consolidation(pass1=False, pass2=True)

        if not (success_pass1 and success_pass2):
            print(f"\n⚠ Warning: Consolidation had some issues")

        # Move consolidated files to chronology_result folder
        print(f"\n{'='*70}")
        print(f"  Moving Combined Files to chronology_result/")
        print(f"{'='*70}")

        for filename in ['combined_pass1.json', 'combined_pass1.csv', 
                         'combined_pass2.json', 'combined_pass2.csv']:
            src = Path(config.OUTPUT_DIR) / filename
            if src.exists():
                dst = result_dir / filename
                import shutil
                shutil.move(str(src), str(dst))
                print(f"  ✓ Moved: {filename} → chronology_result/")
            else:
                print(f"  ⚠ Not found: {filename}")

        print(f"\n✓ Consolidation completed successfully")

    except Exception as e:
        print(f"\n✗ Consolidation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print_header("PIPELINE COMPLETE")

    elapsed = datetime.now() - start_time
    minutes = int(elapsed.total_seconds() // 60)
    seconds = int(elapsed.total_seconds() % 60)

    print(f"\nTotal time: {minutes}m {seconds}s")

    print(f"\nOutput locations:")
    print(f"  Year-wise files: {config.OUTPUT_DIR}/")
    print(f"    - pass1_*.json (individual year extractions)")
    print(f"    - pass2_*.json (individual year enriched)")

    print(f"\n  Final Combined Results: chronology_result/")
    print(f"    - combined_pass1.json (all years - detailed extraction)")
    print(f"    - combined_pass1.csv")
    print(f"    - combined_pass2.json (all years - final chronology)")
    print(f"    - combined_pass2.csv")

    print(f"\n✓ All done!")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Complete chronology generation pipeline (Pass 1 → Pass 2 → Consolidation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline for all years
  python run_full_pipeline.py

  # Run for specific years only
  python run_full_pipeline.py --years 2019 2020 2021

  # Rebuild from scratch
  python run_full_pipeline.py --rebuild

  # Custom knowledge base path
  python run_full_pipeline.py --kb-path /path/to/knowledge_base
"""
    )

    parser.add_argument('--years', nargs='+', type=int,
                        help='Years to process (e.g., 2019 2020). Default: all years')
    parser.add_argument('--rebuild', action='store_true',
                        help='Rebuild from scratch (ignore cached dates)')
    parser.add_argument('--kb-path', default='knowledge_base',
                        help='Path to knowledge base folder (default: knowledge_base)')

    args = parser.parse_args()

    try:
        success = run_full_pipeline(
            years=args.years,
            rebuild=args.rebuild,
            kb_path=args.kb_path
        )

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
