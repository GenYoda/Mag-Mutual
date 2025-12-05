"""
ChatbotAdapter - Wrapper around SimpleRAGChatbot
Applies enhancement toggles from config
"""

import os
import sys
from typing import Dict, List, Optional
from advance_rag_memory import SimpleRAGChatbot
import config

class ChatbotAdapter:
    """
    Wraps SimpleRAGChatbot and applies configuration toggles
    - Enable/disable query enhancement
    - Enable/disable distance filtering
    - Skip reranking (disabled by default for speed)
    - Disable memory (for form filling)
    """

    def __init__(self, kb_path: str = "knowledge_base"):
        """Initialize chatbot with knowledge base"""
        self.chatbot = SimpleRAGChatbot(index_path=kb_path, enable_memory=False)
        
        # auto_sync() automatically loads or builds the index
        self.chatbot.auto_sync(pdf_folder="input")
        
        print(f"✓ ChatbotAdapter initialized")
        print(f"  - Query Enhancement: {config.ENABLE_QUERY_ENHANCEMENT}")
        print(f"  - Distance Filter: {config.ENABLE_DISTANCE_FILTER}")
        print(f"  - Reranking: {config.ENABLE_RERANKING} (disabled for speed)")


    def ask(self, query: str, top_k: int = None, context: str = None) -> Dict:
        """
        Ask a question and get answer with sources
        
        Args:
            query: Question text
            top_k: Number of chunks to retrieve
            context: Optional context from previous questions
        
        Returns:
            Dict with answer and sources
        """
        if top_k is None:
            top_k = config.TOP_K
        
        try:
            # If context provided, prepend it to the query
            enhanced_query = query
            if context and config.ENABLE_CONTEXT_INJECTION:
                enhanced_query = f"{context}\n\nNow answer this question:\n{query}"
            
            # Call chatbot.ask() with enhanced query
            answer, sources = self.chatbot.ask(
                query=enhanced_query,
                top_k=top_k,
                enhancement_flags={
                    'query': config.ENABLE_QUERY_ENHANCEMENT,
                    'distance': config.ENABLE_DISTANCE_FILTER,
                    'rerank': config.ENABLE_RERANKING,
                }
            )
            
            # Format sources correctly and convert distance to similarity
            formatted_sources = []
            for source in sources:
                distance = source.get('distance', float('inf'))
                # Convert distance to similarity
                similarity = (1.0 / (1.0 + distance)) * 100 if distance != float('inf') else 0.0
                
                formatted_sources.append({
                    'chunk': source.get('chunk', ''),
                    'metadata': source.get('metadata', {}),
                    'distance': distance,
                    'similarity': similarity
                })
            
            return {
                'answer': answer if answer else 'NOT_FOUND',
                'sources': formatted_sources,
                'success': True
            }
        
        except Exception as e:
            print(f"❌ Error in ChatbotAdapter.ask(): {str(e)}")
            return {
                'answer': 'NOT_FOUND',
                'sources': [],
                'success': False,
                'error': str(e)
            }

    def batch_ask(self, queries: List[str]) -> List[Dict]:
        """
        Ask multiple questions

        Args:
            queries: List of questions

        Returns:
            List of results (same structure as ask())
        """
        results = []
        for query in queries:
            result = self.ask(query)
            results.append(result)

        return results
