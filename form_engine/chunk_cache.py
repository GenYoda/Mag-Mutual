"""
ChunkCache - Page-wise caching layer
Retrieves chunks once per page instead of per question
"""

from typing import Dict, List, Optional
from collections import defaultdict

class ChunkCache:
    """
    Cache retrieved document chunks by page number
    Massively speeds up batch processing
    """
    
    def __init__(self):
        """Initialize empty cache"""
        self.cache = {}  # {page_number: chunks}
        self.hit_count = 0
        self.miss_count = 0
    
    def get_chunks(self, page_number: int) -> Optional[List[Dict]]:
        """
        Get cached chunks for a page
        
        Args:
            page_number: Page number to retrieve
        
        Returns:
            Cached chunks or None if not cached
        """
        if page_number in self.cache:
            self.hit_count += 1
            return self.cache[page_number]
        
        self.miss_count += 1
        return None
    
    def cache_chunks(self, page_number: int, chunks: List[Dict]) -> None:
        """
        Cache chunks for a page
        
        Args:
            page_number: Page number
            chunks: Retrieved chunks from RAG
        """
        self.cache[page_number] = chunks
    
    def clear(self):
        """Clear all cached chunks"""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
    
    def get_stats(self) -> Dict:
        """Get cache hit/miss statistics"""
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0
        
        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'total_accesses': total,
            'hit_rate': hit_rate,
            'cached_pages': len(self.cache)
        }
