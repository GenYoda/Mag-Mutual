"""
Consolidate year-wise JSON files into a single combined file

Creates:
- combined_pass1.json (all years from Pass 1)
- combined_pass2.json (all years from Pass 2)  
- combined_pass1.csv
- combined_pass2.csv

Usage:
    python consolidate_results.py --pass1
    python consolidate_results.py --pass2
    python consolidate_results.py --both
"""
import config
import json
import csv
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict


def consolidate_json(input_pattern: str, output_file: str, pass_number: int, 
                     input_dir: str = None, output_dir: str = None) -> bool:
    """Consolidate multiple year JSON files into one"""

    if input_dir is None:
        input_dir = config.OUTPUT_DIR
    if output_dir is None:
        output_dir = config.OUTPUT_DIR

    # Find all matching files
    input_files = sorted(Path(input_dir).glob(input_pattern))

    if not input_files:
        print(f"✗ No files found matching: {input_pattern} in {input_dir}")
        return False

    print(f"\n{'='*70}")
    print(f"  CONSOLIDATING PASS {pass_number} FILES")
    print(f"{'='*70}")
    print(f"\nFound {len(input_files)} file(s):")
    for f in input_files:
        print(f"  - {f.name}")

    # Collect all events
    all_events = []
    years_processed = []
    total_by_year = {}

    for json_file in input_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            year = data.get('year', 'unknown')
            events = data.get('events', [])

            years_processed.append(year)
            total_by_year[year] = len(events)
            all_events.extend(events)

            print(f"  ✓ {year}: {len(events)} events")

        except Exception as e:
            print(f"  ✗ Failed to load {json_file.name}: {e}")
            continue

    if not all_events:
        print(f"\n✗ No events found in any file")
        return False

    # Sort all events by date and time
    all_events_sorted = sorted(
        all_events,
        key=lambda x: (x.get('date', ''), x.get('time', '') or '')
    )

    # Calculate statistics
    event_types = {}
    for e in all_events_sorted:
        et = e.get('event_type', 'unknown')
        event_types[et] = event_types.get(et, 0) + 1

    # Create consolidated output
    output = {
        'pass': pass_number,
        'version': '1.0',
        'consolidated': True,
        'generated_at': datetime.now().isoformat(),
        'years_included': sorted(years_processed),
        'total_events': len(all_events_sorted),
        'events_by_year': total_by_year,
        'events_by_type': event_types,
        'events': all_events_sorted
    }

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Save consolidated JSON
    output_path = os.path.join(output_dir, output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Consolidated JSON saved: {output_path}")
    print(f"  Total events: {len(all_events_sorted)}")
    print(f"  Years: {', '.join(map(str, sorted(years_processed)))}")
    print(f"  By type: {dict(sorted(event_types.items()))}")

    return True


def json_to_csv_consolidated(json_file: str, csv_file: str = None) -> bool:
    """Convert consolidated JSON to CSV"""

    if csv_file is None:
        csv_file = json_file.replace('.json', '.csv')

    print(f"\n{'='*70}")
    print(f"  CONVERTING TO CSV")
    print(f"{'='*70}")
    print(f"\nInput: {json_file}")

    # Load JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"✗ Failed to load JSON: {e}")
        return False

    events = data.get('events', [])
    if not events:
        print(f"✗ No events found in file")
        return False

    pass_num = data.get('pass', 'unknown')

    # Determine fields based on pass
    if pass_num == 1:
        fieldnames = [
            'date', 'time', 'event_type', 'facility', 'provider', 
            'description', 'source_documents', 'source_pages'
        ]
    elif pass_num == 2:
        fieldnames = [
            'date', 'time', 'event_type',
            'facility', 'provider', 'title',
            'notes', 'description_full',
            'source_documents', 'source_pages'
        ]

    else:
        # Auto-detect
        fieldnames = [
            'date', 'time', 'event_type', 'facility', 'provider', 'title',
            'description', 'source_documents', 'source_pages'
        ]

    # Flatten events
    rows = []
    for event in events:
        row = {}

        # Copy all fields except sources
        for field in fieldnames:
            if field in ['source_documents', 'source_pages']:
                continue
            row[field] = event.get(field, '')

        # Flatten sources
        sources = event.get('sources', [])
        if sources:
            docs = []
            pages = []
            for source in sources:
                if isinstance(source, dict):
                    docs.append(source.get('document', '') or source.get('source', ''))
                    source_pages = source.get('pages', [])
                    if isinstance(source_pages, list):
                        pages.append(', '.join(map(str, source_pages)))
                    else:
                        pages.append(str(source_pages))

            row['source_documents'] = '; '.join(docs)
            row['source_pages'] = '; '.join(pages)
        else:
            row['source_documents'] = ''
            row['source_pages'] = ''

        rows.append(row)

    # Write CSV
    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)

        print(f"✓ CSV saved: {csv_file}")
        print(f"  Rows: {len(rows)}")
        print(f"  Columns: {', '.join(fieldnames)}")
        return True

    except Exception as e:
        print(f"✗ Failed to write CSV: {e}")
        return False


def run_consolidation(pass1=False, pass2=False, 
                     input_dir=None, output_dir=None):
    """
    Run consolidation for specified passes

    Args:
        pass1: Consolidate Pass 1 files
        pass2: Consolidate Pass 2 files
        input_dir: Directory containing pass1_*.json and pass2_*.json files
        output_dir: Directory to save combined files (default: same as input_dir)
    """

    if not pass1 and not pass2:
        print("Error: Specify pass1=True, pass2=True, or both")
        return False

    if input_dir is None:
        input_dir = config.OUTPUT_DIR
    if output_dir is None:
        output_dir = input_dir

    success = True

    # Consolidate Pass 1
    if pass1:
        json_success = consolidate_json(
            input_pattern='pass1_*.json',
            output_file='combined_pass1.json',
            pass_number=1,
            input_dir=input_dir,
            output_dir=output_dir
        )

        if json_success:
            csv_success = json_to_csv_consolidated(
                json_file=os.path.join(output_dir, 'combined_pass1.json')
            )
            success = success and csv_success
        else:
            success = False

    # Consolidate Pass 2
    if pass2:
        json_success = consolidate_json(
            input_pattern='pass2_*.json',
            output_file='combined_pass2.json',
            pass_number=2,
            input_dir=input_dir,
            output_dir=output_dir
        )

        if json_success:
            csv_success = json_to_csv_consolidated(
                json_file=os.path.join(output_dir, 'combined_pass2.json')
            )
            success = success and csv_success
        else:
            success = False

    if success:
        print(f"\n{'='*70}")
        print(f"  CONSOLIDATION COMPLETE")
        print(f"{'='*70}")
        print(f"\nOutput files in: {output_dir}/")
        if pass1:
            print(f"  - combined_pass1.json")
            print(f"  - combined_pass1.csv")
        if pass2:
            print(f"  - combined_pass2.json")
            print(f"  - combined_pass2.csv")

    return success


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Consolidate year-wise JSON files into single combined file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python consolidate_results.py --pass1
    python consolidate_results.py --pass2  
    python consolidate_results.py --both
    python consolidate_results.py --both --output-dir chronology_result
"""
    )

    parser.add_argument('--pass1', action='store_true', help='Consolidate Pass 1 files')
    parser.add_argument('--pass2', action='store_true', help='Consolidate Pass 2 files')
    parser.add_argument('--both', action='store_true', help='Consolidate both Pass 1 and Pass 2')
    parser.add_argument('--input-dir', default=None, help='Input directory (default: config.OUTPUT_DIR)')
    parser.add_argument('--output-dir', default=None, help='Output directory (default: same as input)')

    args = parser.parse_args()

    # Handle --both flag
    if args.both:
        args.pass1 = True
        args.pass2 = True

    try:
        success = run_consolidation(
            pass1=args.pass1, 
            pass2=args.pass2,
            input_dir=args.input_dir,
            output_dir=args.output_dir
        )
        exit(0 if success else 1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
