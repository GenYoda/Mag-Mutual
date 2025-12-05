"""
Cosine Similarity Retriever

A wrapper around advance_rag_memory that provides cosine similarity search
without rebuilding the FAISS index.

Usage:
    from cosine_retriever import CosineRetriever
    
    retriever = CosineRetriever("knowledge_base")
    results = retriever.retrieve("2012-12-25", topk=20)
"""

import os
import numpy as np
from typing import List, Dict
from advance_rag_memory import SimpleRAGChatbot


class CosineRetriever:
    """
    Retrieves chunks using cosine similarity instead of L2 distance.
    
    Works with existing L2-based FAISS index by computing cosine 
    similarity manually at query time.
    """
    
    def __init__(self, kb_path: str = "knowledge_base"):
        """
        Initialize cosine retriever
        
        Args:
            kb_path: Path to knowledge base folder
        """
        print(f"\n[Cosine Retriever Initialization]")
        print(f"  Loading knowledge base from: {kb_path}")
        
        # Load the underlying RAG chatbot
        self.chatbot = SimpleRAGChatbot(kb_path)
        
        if not self.chatbot.load_index():
            raise ValueError(f"Failed to load FAISS index from {kb_path}")
        
        print(f"  ✓ FAISS index loaded: {self.chatbot.faiss_index.ntotal} vectors")
        print(f"  ✓ Using COSINE similarity (computed at query time)")
        
        # Precompute normalized embeddings for all chunks
        print(f"  → Precomputing normalized embeddings...")
        self._precompute_normalized_embeddings()
        print(f"  ✓ Normalized {len(self.normalized_embeddings)} chunk embeddings")
    
    def _precompute_normalized_embeddings(self):
        """Precompute and store normalized embeddings for all chunks"""
        self.normalized_embeddings = []
        
        for i in range(self.chatbot.faiss_index.ntotal):
            # Extract embedding from FAISS index
            embedding = self.chatbot.faiss_index.reconstruct(int(i))
            
            # Normalize to unit length
            norm = np.linalg.norm(embedding)
            if norm > 0:
                normalized = embedding / norm
            else:
                normalized = embedding
            
            self.normalized_embeddings.append(normalized)
        
        # Convert to numpy array for faster computation
        self.normalized_embeddings = np.array(self.normalized_embeddings)
    
    def retrieve(self, query: str, topk: int = 10) -> List[Dict]:
        """
        Retrieve most similar chunks using cosine similarity
        
        Args:
            query: Search query (e.g., date string)
            topk: Number of results to return
            
        Returns:
            List of dicts with keys: chunk, metadata, distance, similarity
        """
        # Get query embedding
        query_embedding = self.chatbot.get_embedding(query)
        
        # Normalize query embedding
        query_norm = np.linalg.norm(query_embedding)
        if query_norm > 0:
            query_normalized = query_embedding / query_norm
        else:
            query_normalized = query_embedding
        
        # Compute cosine similarity with all chunks
        # Cosine similarity = dot product of normalized vectors
        similarities = np.dot(self.normalized_embeddings, query_normalized)
        
        # Get top k indices (argsort returns ascending, so reverse)
        top_indices = np.argsort(similarities)[::-1][:topk]
        
        # Build results
        results = []
        for idx in top_indices:
            similarity = float(similarities[idx])
            distance = 1.0 - similarity  # Convert to distance for consistency
            
            results.append({
                'chunk': self.chatbot.chunks[idx],
                'metadata': self.chatbot.metadata[idx],
                'distance': distance,
                'similarity': similarity,
                'cosine_similarity': similarity  # Explicit field
            })
        
        return results
    
    def _get_openai_client(self):
        """Get OpenAI client from underlying chatbot"""
        return self.chatbot._get_openai_client()


class HybridRetriever:
    """
    Combines both L2 and Cosine retrieval methods.
    
    Usage:
        retriever = HybridRetriever("knowledge_base", method="cosine")
        results = retriever.retrieve("2012-12-25", topk=20)
    """
    
    def __init__(self, kb_path: str = "knowledge_base", method: str = "L2"):
        """
        Initialize hybrid retriever
        
        Args:
            kb_path: Path to knowledge base
            method: "L2" or "COSINE"
        """
        self.method = method.upper()
        
        if self.method == "COSINE":
            self.retriever = CosineRetriever(kb_path)
        else:
            # Use standard L2 retriever
            self.retriever = SimpleRAGChatbot(kb_path)
            if not self.retriever.load_index():
                raise ValueError(f"Failed to load FAISS index from {kb_path}")
            print(f"\n[L2 Retriever]")
            print(f"  ✓ FAISS index loaded: {self.retriever.faiss_index.ntotal} vectors")
            print(f"  ✓ Using L2 distance (standard)")
    
    def retrieve(self, query: str, topk: int = 10) -> List[Dict]:
        """Retrieve using configured method"""
        return self.retriever.retrieve(query, topk)
    
    def _get_openai_client(self):
        """Get OpenAI client"""
        if hasattr(self.retriever, '_get_openai_client'):
            return self.retriever._get_openai_client()
        elif hasattr(self.retriever, 'chatbot'):
            return self.retriever.chatbot._get_openai_client()
        else:
            raise AttributeError("Cannot find OpenAI client")
    
    def get_method(self) -> str:
        """Get current retrieval method"""
        return self.method
    
    # Expose underlying attributes as properties
    @property
    def chunks(self):
        """Access chunks from underlying retriever"""
        if hasattr(self.retriever, 'chunks'):
            return self.retriever.chunks
        elif hasattr(self.retriever, 'chatbot'):
            return self.retriever.chatbot.chunks
        else:
            raise AttributeError("Chunks not available")
    
    @property
    def metadata(self):
        """Access metadata from underlying retriever"""
        if hasattr(self.retriever, 'metadata'):
            return self.retriever.metadata
        elif hasattr(self.retriever, 'chatbot'):
            return self.retriever.chatbot.metadata
        else:
            raise AttributeError("Metadata not available")
    
    @property
    def faiss_index(self):
        """Access FAISS index from underlying retriever"""
        if hasattr(self.retriever, 'faiss_index'):
            return self.retriever.faiss_index
        elif hasattr(self.retriever, 'chatbot'):
            return self.retriever.chatbot.faiss_index
        else:
            raise AttributeError("FAISS index not available")


if __name__ == '__main__':
    """Quick test to compare L2 vs Cosine"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python cosine_retriever.py <date>")
        print("Example: python cosine_retriever.py 2012-12-25")
        sys.exit(1)
    
    test_query = sys.argv[1]
    
    print("="*70)
    print(" COMPARING L2 vs COSINE RETRIEVAL")
    print("="*70)
    print(f"\nQuery: {test_query}")
    
    # Test L2
    print("\n" + "-"*70)
    print(" L2 DISTANCE (Current Method)")
    print("-"*70)
    l2_retriever = SimpleRAGChatbot("knowledge_base")
    l2_retriever.load_index()
    l2_results = l2_retriever.retrieve(test_query, 5)
    
    print(f"\nTop 5 chunks (L2):")
    for i, r in enumerate(l2_results, 1):
        meta = r.get('metadata', {})
        dist = r.get('distance', 0)
        src = meta.get('source', 'Unknown')
        text = r.get('chunk', '')[:80]
        print(f"  {i}. L2 dist: {dist:.3f} | {src}")
        print(f"     {text}...")
    
    # Test Cosine
    print("\n" + "-"*70)
    print(" COSINE SIMILARITY")
    print("-"*70)
    cosine_retriever = CosineRetriever("knowledge_base")
    cosine_results = cosine_retriever.retrieve(test_query, 5)
    
    print(f"\nTop 5 chunks (Cosine):")
    for i, r in enumerate(cosine_results, 1):
        meta = r.get('metadata', {})
        sim = r.get('similarity', 0)
        dist = r.get('distance', 0)
        src = meta.get('source', 'Unknown')
        text = r.get('chunk', '')[:80]
        print(f"  {i}. Cosine: {sim:.3f} (dist: {dist:.3f}) | {src}")
        print(f"     {text}...")
    
    print("\n" + "="*70)
    print(" COMPARISON COMPLETE")
    print("="*70)
