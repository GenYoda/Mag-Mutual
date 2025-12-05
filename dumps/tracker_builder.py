# Run this ONCE to create document_tracker.json
import json
import hashlib
from pathlib import Path
from datetime import datetime

# Load existing metadata
with open('knowledge_base/metadata.json', 'r') as f:
    metadata = json.load(f)

# Build tracker from metadata
tracker = {}
current_source = None
start_idx = 0

for idx, meta in enumerate(metadata):
    source = meta['source']
    
    if source != current_source:
        # New document started
        if current_source is not None:
            # Finalize previous document
            tracker[current_source]['vector_end_idx'] = idx - 1
        
        # Start new document tracking
        tracker[source] = {
            'hash': 'unknown',  # Can't recreate hash without original file
            'last_indexed': datetime.now().isoformat(),
            'chunk_count': 0,
            'vector_start_idx': idx,
            'vector_end_idx': idx
        }
        current_source = source
    
    tracker[current_source]['chunk_count'] += 1
    tracker[current_source]['vector_end_idx'] = idx

# Save tracker
with open('knowledge_base/document_tracker.json', 'w') as f:
    json.dump(tracker, f, indent=2)

print("✓ Created document_tracker.json")
print(f"✓ Tracked {len(tracker)} documents")