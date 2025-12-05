"""
Logger - Performance tracking and statistics
"""

import time
from typing import Dict
from datetime import datetime

class FormFillerLogger:
    """Track execution stats and performance"""
    
    def __init__(self):
        self.start_time = None
        self.events = []
    
    def start(self):
        """Mark start of execution"""
        self.start_time = time.time()
        self.events.append(('START', datetime.now().isoformat()))
    
    def log_event(self, event_name: str, details: str = ""):
        """Log an event"""
        self.events.append((event_name, datetime.now().isoformat(), details))
    
    def get_elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    def print_summary(self, stats: Dict):
        """Print execution summary"""
        elapsed = self.get_elapsed()
        
        print(f"\n{'='*70}")
        print(f"📊 EXECUTION SUMMARY")
        print(f"{'='*70}")
        print(f"Total Time: {elapsed:.2f}s")
        print(f"Questions Processed: {stats.get('total_questions', 0)}")
        print(f"Successful: {stats.get('successful', 0)}")
        print(f"Failed: {stats.get('failed', 0)}")
        success_rate = (stats.get('successful', 0) / stats.get('total_questions', 1) * 100) if stats.get('total_questions', 0) > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Avg Time per Question: {elapsed / stats.get('total_questions', 1):.2f}s")
        print(f"{'='*70}\n")
