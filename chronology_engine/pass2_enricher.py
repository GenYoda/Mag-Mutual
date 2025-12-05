"""
Pass 2: Clean, Merge, and Finalize Medical Chronology

Takes Pass 1 output and:
- Removes duplicates
- Merges related events
- Creates brief 50-90 word descriptions
- Standardizes fields
- Sorts chronologically

Usage:
    python pass2_enricher.py --input output/pass1_2019.json
    python pass2_enricher.py --batch  # Process all Pass 1 files
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import config


class Pass2Enricher:
    """Clean and merge Pass 1 events into final chronology"""
    
    def __init__(self):
        print("\n" + "="*70)
        print(" PASS 2: CLEANING, MERGING & FINALIZATION")
        print("="*70)
        
        # Load OpenAI client same way as Pass 1
        # We just need the client, don't need full RAG chatbot
        from advance_rag_memory import SimpleRAGChatbot
        
        print(f"\n[Loading OpenAI Client]")
        temp_chatbot = SimpleRAGChatbot()
        self.client = temp_chatbot._get_openai_client()
        
        # Get model name from environment or use default
        import os
        self.model_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "pra-poc-gpt-4o")
        
        print(f"  ✓ Azure OpenAI client loaded")
        print(f"  Model: {self.model_name}")
        
        print(f"\n[Configuration]")
        print(f"  Merge same date/provider: {config.PASS2_MERGE_SAME_DATE_PROVIDER}")
        print(f"  Deduplicate: {config.PASS2_DEDUPLICATE}")
        print(f"  Time window: {config.PASS2_MERGE_TIME_WINDOW} minutes")
    
    def load_pass1_file(self, filepath: str) -> Dict:
        """Load Pass 1 JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def enrich_batch(self, events: List[Dict]) -> List[Dict]:
        """
        Send a batch of events to LLM for cleaning and merging
        
        Args:
            events: List of Pass 1 events
            
        Returns:
            List of cleaned/merged events
        """
        # Prepare events for LLM (remove internal fields)
        clean_events = []
        for i, e in enumerate(events):
            clean_event = {
                'index': i,  # Track original position
                'date': e.get('date'),
                'time': e.get('time'),
                'event_type': e.get('event_type'),
                'facility': e.get('facility'),
                'provider': e.get('provider'),
                'title': e.get('title'),
                'description': e.get('description'),  # Pass 1 description
                'sources': e.get('sources', [])
            }
            clean_events.append(clean_event)
        
        # Build prompt
        events_json = json.dumps(clean_events, indent=2)
        user_prompt = config.PASS2_USER_PROMPT.format(events_json=events_json)
        
        messages = [
            {"role": "system", "content": config.PASS2_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,  # Low temp for consistent formatting
                max_tokens=4000
            )
            
            llm_output = response.choices[0].message.content.strip()
            
            # Parse JSON
            enriched_events = self._parse_json_response(llm_output)
            
            return enriched_events
            
        except Exception as e:
            print(f"  ✗ LLM error: {e}")
            return []
    
    def _parse_json_response(self, text: str) -> List[Dict]:
        """Parse LLM JSON response"""
        fence = '`' + '`' + '`'
        text = text.strip()
        
        # Remove markdown fences
        lower = text.lower()
        fence_json = fence + 'json'
        if lower.startswith(fence_json.lower()):
            text = text[len(fence_json):]
        elif text.startswith(fence):
            text = text[len(fence):]
        if text.endswith(fence):
            text = text[:-len(fence)]
        
        text = text.strip()
        
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'events' in data:
                return data['events']
            else:
                return []
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON parse error: {e}")
            return []
    
    def process_file(self, input_file: str) -> bool:
        """Process a single Pass 1 file"""
        
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"✗ File not found: {input_file}")
            return False
        
        print(f"\n[Processing: {input_path.name}]")
        
        # Load Pass 1 data
        pass1_data = self.load_pass1_file(input_file)
        year = pass1_data.get('year', 'unknown')
        events = pass1_data.get('events', [])
        
        print(f"  Year: {year}")
        print(f"  Pass 1 events: {len(events)}")
        
        if not events:
            print(f"  ⚠ No events to process")
            return False
        
        # Process in batches (to avoid token limits)
        batch_size = 20
        all_enriched = []
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i+batch_size]
            print(f"  → Processing batch {i//batch_size + 1} ({len(batch)} events)...", end='', flush=True)
            
            enriched_batch = self.enrich_batch(batch)
            
            if enriched_batch:
                all_enriched.extend(enriched_batch)
                print(f" ✓ {len(enriched_batch)} final events")
            else:
                print(f" ✗ Failed")
                # Fallback: keep original events
                all_enriched.extend(batch)
        
        # Sort final events chronologically
        all_enriched.sort(key=lambda x: (
            x.get('date', ''),
            x.get('time', '') or 'ZZZ'  # null times go last
        ))
        
        # Build output
        output_data = {
            'pass': 2,
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'year': year,
            'total_events': len(all_enriched),
            'events_by_type': self._count_by_type(all_enriched),
            'events': all_enriched
        }
        
        # Save Pass 2 file
        output_file = input_path.parent / input_path.name.replace('pass1_', 'pass2_')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n  ✓ Saved: {output_file}")
        print(f"    Final events: {len(all_enriched)} (merged from {len(events)})")
        print(f"    By type: {dict(output_data['events_by_type'])}")
        
        return True
    
    def _count_by_type(self, events: List[Dict]) -> Dict[str, int]:
        """Count events by type"""
        counts = {}
        for e in events:
            et = e.get('event_type', 'unknown')
            counts[et] = counts.get(et, 0) + 1
        return counts
    
    def process_batch(self, directory: str = None):
        """Process all Pass 1 files in directory"""
        
        if directory is None:
            directory = config.OUTPUT_DIR
        
        dir_path = Path(directory)
        pass1_files = sorted(dir_path.glob('pass1_*.json'))
        
        if not pass1_files:
            print(f"\n✗ No Pass 1 files found in {directory}/")
            return False
        
        print(f"\nFound {len(pass1_files)} Pass 1 file(s):")
        for f in pass1_files:
            print(f"  - {f.name}")
        
        success_count = 0
        for pass1_file in pass1_files:
            if self.process_file(str(pass1_file)):
                success_count += 1
        
        print(f"\n{'='*70}")
        print(f" PASS 2 COMPLETE")
        print(f"{'='*70}")
        print(f"\nProcessed: {success_count}/{len(pass1_files)} files")
        
        return success_count == len(pass1_files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Pass 2: Clean, merge, and finalize medical chronology",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pass2_enricher.py --input output/pass1_2019.json
  python pass2_enricher.py --batch
        """
    )
    
    parser.add_argument('--input', help='Path to Pass 1 JSON file')
    parser.add_argument('--batch', action='store_true', help='Process all Pass 1 files')
    parser.add_argument('--directory', default=None, help='Directory containing Pass 1 files')
    
    args = parser.parse_args()
    
    if not args.input and not args.batch:
        parser.error("Specify either --input or --batch")
    
    try:
        enricher = Pass2Enricher()
        
        if args.batch:
            success = enricher.process_batch(args.directory)
        else:
            success = enricher.process_file(args.input)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
