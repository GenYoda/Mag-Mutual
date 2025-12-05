"""
Pass 1: Windowed Event Extraction using existing DateExtractor
"""

import os
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import config
from chronology_engine.date_extractor import DateExtractor


class WindowedPass1Extractor:
    """Window-based extraction using existing date extraction logic"""
    
    def __init__(self):
        print("\n" + "="*70)
        print(" PASS 1: WINDOWED EVENT EXTRACTION")
        print("="*70)
        
        # Load OpenAI client
        from advance_rag_memory import SimpleRAGChatbot
        temp_chatbot = SimpleRAGChatbot()
        self.client = temp_chatbot._get_openai_client()
        self.model_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "pra-poc-gpt-4o")
        
        # Load KB
        self.kb_dir = "knowledge_base"
        self.chunks = []
        self.metadata = []
        self.date_extractor = None
        self._load_kb()
        
        print(f"\n[Configuration]")
        print(f"  Model: {self.model_name}")
        print(f"  Chunks: {len(self.chunks)}")
        print(f"  Max window chars: {getattr(config, 'MAX_WINDOW_CHARS', 15000)}")
    
    def _load_kb(self):
        """Load chunks and metadata"""
        print(f"\n[Loading Knowledge Base]")
        
        with open(os.path.join(self.kb_dir, "chunks.pkl"), 'rb') as f:
            self.chunks = pickle.load(f)
        
        with open(os.path.join(self.kb_dir, "metadata.json"), 'r') as f:
            self.metadata = json.load(f)
        
        # Initialize date extractor
        self.date_extractor = DateExtractor(self.chunks, self.metadata)
        
        print(f"  ✓ Loaded {len(self.chunks)} chunks")
    
    def extract_dates_from_kb(self) -> Dict[str, List[str]]:
        """Phase 1: Use existing DateExtractor"""
        dates_by_year = self.date_extractor.extract_all_dates()
        return dates_by_year
    
    def build_windows_for_date(self, date_iso: str) -> List[Dict]:
        """Build windows for a specific date using keyword matching"""
        # Generate date variants
        variants = self._get_date_variants(date_iso)
        
        # Find all chunks containing this date
        matching_chunks = []
        for i, chunk in enumerate(self.chunks):
            chunk_lower = chunk.lower()
            if any(v.lower() in chunk_lower for v in variants):
                meta = self.metadata[i] if i < len(self.metadata) else {}
                matching_chunks.append({
                    'index': i,
                    'text': chunk,
                    'metadata': meta,
                    'document': meta.get('source', 'Unknown'),
                    'pages': meta.get('page_numbers', []) or meta.get('pages', [])
                })
        
        if not matching_chunks:
            return []
        
        # Group into windows
        windows = self._group_into_windows(matching_chunks, date_iso)
        return windows
    
    def _get_date_variants(self, date_iso: str) -> List[str]:
        """Generate date variants for matching"""
        try:
            dt = datetime.strptime(date_iso, '%Y-%m-%d')
            return [
                date_iso,
                dt.strftime('%m/%d/%Y'),
                dt.strftime('%m-%d-%Y'),
                dt.strftime('%B %d, %Y'),
                dt.strftime('%b %d, %Y'),
                dt.strftime('%d %B %Y'),
                dt.strftime('%d %b %Y'),
                dt.strftime('%B %d %Y'),
                dt.strftime('%b %d %Y'),
            ]
        except:
            return [date_iso]
    
    def _group_into_windows(self, chunks: List[Dict], date: str) -> List[Dict]:
        """Group chunks into windows by document + proximity"""
        chunks = sorted(chunks, key=lambda x: (x['document'], x['index']))
        
        windows = []
        current_group = []
        prev_doc = None
        prev_idx = None
        
        MAX_GAP = getattr(config, 'MAX_CHUNK_GAP_FOR_SAME_EVENT', 5)
        
        for chunk in chunks:
            doc = chunk['document']
            idx = chunk['index']
            
            # Start new window if different document or large gap
            if prev_doc is not None:
                if doc != prev_doc or (idx - prev_idx) > MAX_GAP:
                    if current_group:
                        windows.append(self._create_window(current_group, date))
                    current_group = []
            
            current_group.append(chunk)
            prev_doc = doc
            prev_idx = idx
        
        # Flush last group
        if current_group:
            windows.append(self._create_window(current_group, date))
        
        return windows
    
    def _create_window(self, chunks: List[Dict], date: str) -> Dict:
        """Create window with context"""
        # Core indices: chunks that matched the date
        core_indices = [c['index'] for c in chunks]
        
        # Add context
        context_span = getattr(config, 'LOCAL_CONTEXT_SPAN', 1)
        context_indices = set()
        
        for idx in core_indices:
            for offset in range(-context_span, context_span + 1):
                ctx_idx = idx + offset
                if 0 <= ctx_idx < len(self.chunks):
                    context_indices.add(ctx_idx)
        
        # Gather text from context
        context_indices = sorted(context_indices)
        texts = [self.chunks[idx] for idx in context_indices]
        combined_text = '\n\n'.join(texts)
        
        # NEW: Collect CORE pages only (evidence pages)
        core_pages = set()
        for idx in core_indices:
            meta = self.metadata[idx] if idx < len(self.metadata) else {}
            pages = meta.get('page_numbers', []) or meta.get('pages', [])
            if isinstance(pages, list):
                core_pages.update(pages)
        
        # Optional: still collect all context pages if needed
        all_pages = set()
        for idx in context_indices:
            meta = self.metadata[idx] if idx < len(self.metadata) else {}
            pages = meta.get('page_numbers', []) or meta.get('pages', [])
            if isinstance(pages, list):
                all_pages.update(pages)
        
        # Limit size
        max_chars = getattr(config, 'MAX_WINDOW_CHARS', 15000)
        if len(combined_text) > max_chars:
            combined_text = combined_text[:max_chars] + '\n[TRUNCATED]'
        
        # DEBUG
        doc_name = chunks[0]['document']
        print(f"\n  [DEBUG] Window for {date}: document='{doc_name}', core_pages={sorted(core_pages)}, context_pages={sorted(all_pages)}")
        
        return {
            'date': date,
            'document': chunks[0]['document'],
            'pages': sorted(all_pages),          # Full context (optional)
            'core_pages': sorted(core_pages),    # NEW: tight evidence pages
            'text': combined_text,
            'chunk_indices': context_indices
        }
    
    def extract_events_from_window(self, window: Dict) -> List[Dict]:
        """Extract events from window using Pass 1 prompt"""
        user_prompt = config.PASS1_USER_PROMPT.format(
            date=window['date'],
            context_text=window['text']
        )
        
        messages = [
            {"role": "system", "content": config.PASS1_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            if content is None:
                print(f" (empty LLM response)")
                return []
            
            llm_output = content.strip()
            if not llm_output:
                print(f" (blank response)")
                return []
            
            events = self._parse_json(llm_output)
            
            # NEW: Use core_pages for tight source attribution
            core_pages = window.get('core_pages', [])
            if not core_pages:
                # Fallback to full window pages if core_pages missing
                core_pages = window.get('pages', [])
            
            for event in events:
                # Always override with correct document and tight pages
                event['sources'] = [{
                    'document': window['document'],
                    'pages': core_pages
                }]
            
            return events
            
        except Exception as e:
            print(f" (error: {e})")
            return []
        
    def _parse_json(self, text: str) -> List[Dict]:
        """Parse JSON from LLM response"""
        text = text.strip()
        
        try:
            data = json.loads(text)
            return data if isinstance(data, list) else [data]
        except:
            pass
        
        # Extract JSON array
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
        
        return []
    
    def run(self, years: Optional[List[int]] = None):
        """Main extraction workflow"""
        # Phase 1: Extract dates
        dates_by_year = self.extract_dates_from_kb()
        
        # Filter years
        if years:
            dates_by_year = {str(y): dates for y, dates in dates_by_year.items() if int(y) in years}
        
        print("\n" + "="*70)
        print(" PHASE 2: EVENT EXTRACTION")
        print("="*70)
        
        all_results = {}
        
        for year in sorted(dates_by_year.keys()):
            dates = dates_by_year[year]
            print(f"\n[Year {year}]")
            print(f"  Dates to process: {len(dates)}")
            
            year_events = []
            
            for date in dates:
                windows = self.build_windows_for_date(date)
                
                if not windows:
                    print(f"  [{date}] No windows found")
                    continue
                
                date_events = []
                for window in windows:
                    events = self.extract_events_from_window(window)
                    date_events.extend(events)
                
                print(f"  [{date}] {len(windows)} windows → {len(date_events)} events")
                year_events.extend(date_events)
            
            all_results[int(year)] = year_events
        
        # Save results
        self._save_results(all_results)
        return all_results
    
    def _save_results(self, results: Dict[int, List[Dict]]):
        """Save extraction results"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        for year, events in results.items():
            if not events:
                continue
            
            output_file = output_dir / f"pass1_{year}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "extraction_date": datetime.now().isoformat(),
                    "year": year,
                    "total_events": len(events),
                    "events": events
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Saved: {output_file} ({len(events)} events)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--years', type=int, nargs='+', help='Years to extract')
    args = parser.parse_args()
    
    extractor = WindowedPass1Extractor()
    extractor.run(years=args.years)
