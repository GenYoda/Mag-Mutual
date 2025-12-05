"""
advance_rag_bot.py
RAG chatbot with AUTO-SYNC capability for progressive knowledge base
OPTIMIZED: Auto-detects new files and appends them without rebuilding
Version: 3.3 - AUTO-SYNC ENABLED
"""

import os
from pathlib import Path
import pickle
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv

# Azure services
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# Vector search
import faiss
import numpy as np

# Text processing
from typing import List, Dict, Set

# Enhancement modules (with graceful fallback)
try:
    from enhancements.retrieval_enhancer import filter_by_distance
    from enhancements.reranker import rerank_chunks
    from enhancements.query_enhancer import enhance_query_simple
    from enhancements.conversation_memory import ConversationBufferMemory
    ENHANCEMENTS_AVAILABLE = True
    print("✓ Enhancement modules loaded successfully")
except ImportError as e:
    ENHANCEMENTS_AVAILABLE = False
    print(f"⚠ Enhancement modules not available: {e}")
    print("  Running in basic mode without enhancements")

load_dotenv()


class SimpleRAGChatbot:
    """
    Advanced RAG chatbot with AUTO-SYNC:
    - Automatically detects new files in input folder
    - Incrementally appends to knowledge base
    - No manual rebuild needed
    - File tracking with hash-based duplicate detection
    """
    
    def __init__(self, index_path="knowledge_base", enable_memory: bool = True, max_exchanges: int = 5):
        """
        Initialize RAG chatbot
        
        Args:
            index_path: Path to store/load FAISS index
            enable_memory: Whether to use conversation memory
            max_exchanges: Number of Q&A pairs to remember (default: 5)
        """
        self.index_path = index_path
        os.makedirs(index_path, exist_ok=True)
        
        # Document tracking
        self.tracker_file = os.path.join(index_path, "document_tracker.json")
        self.indexed_files = {}
        
        # Azure clients
        self.doc_intel_client = None
        self.openai_client = None
        
        # Vector database
        self.faiss_index = None
        self.chunks = []
        self.metadata = []
        self.embedding_dim = None
        
        # Conversation memory
        self.enable_memory = enable_memory and ENHANCEMENTS_AVAILABLE
        if self.enable_memory:
            self.memory = ConversationBufferMemory(max_exchanges=max_exchanges)
            print(f"✓ RAG Chatbot initialized with conversation memory ({max_exchanges} exchanges)")
        else:
            self.memory = None
            print("✓ RAG Chatbot initialized (memory disabled)")
    
    def _get_doc_intel_client(self):
        """Initialize Azure Document Intelligence client"""
        if self.doc_intel_client is None:
            endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
            
            if not endpoint or not key:
                raise ValueError("Azure Document Intelligence credentials not found in .env")
            
            self.doc_intel_client = DocumentIntelligenceClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )
        
        return self.doc_intel_client
    
    def _get_openai_client(self):
        """Initialize Azure OpenAI client"""
        if self.openai_client is None:
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            key = os.getenv("AZURE_OPENAI_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION")
            
            if not endpoint or not key or not api_version:
                raise ValueError("Azure OpenAI credentials not found in .env")
            
            self.openai_client = AzureOpenAI(
                api_key=key,
                api_version=api_version,
                azure_endpoint=endpoint
            )
        
        return self.openai_client
    
    # ========================================================================
    # FILE TRACKING METHODS (NEW)
    # ========================================================================
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file for change detection"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _load_document_tracker(self):
        """Load document tracking information"""
        if os.path.exists(self.tracker_file):
            with open(self.tracker_file, 'r') as f:
                self.indexed_files = json.load(f)
        else:
            self.indexed_files = {}
    
    def _save_document_tracker(self):
        """Save document tracking information"""
        with open(self.tracker_file, 'w') as f:
            json.dump(self.indexed_files, f, indent=2)
    
    def _get_all_pdfs(self, pdf_folder: str) -> List[Path]:
        """Get all PDF files from folder recursively"""
        pdf_folder_path = Path(pdf_folder)
        return list(pdf_folder_path.rglob("*.pdf"))
    
    def _find_new_and_modified_files(self, pdf_folder: str) -> tuple:
        """
        Find new and modified PDF files
        
        Returns:
            (new_files, modified_files, unchanged_files)
        """
        all_pdfs = self._get_all_pdfs(pdf_folder)
        pdf_folder_path = Path(pdf_folder)
        
        new_files = []
        modified_files = []
        unchanged_files = []
        
        # Track current files
        current_file_paths = set()
        
        for pdf_path in all_pdfs:
            relative_path = str(pdf_path.relative_to(pdf_folder_path))
            current_file_paths.add(relative_path)
            
            file_hash = self._calculate_file_hash(str(pdf_path))
            
            if relative_path not in self.indexed_files:
                # New file
                new_files.append((pdf_path, relative_path, file_hash))
            elif self.indexed_files[relative_path]['hash'] != file_hash:
                # Modified file
                modified_files.append((pdf_path, relative_path, file_hash))
            else:
                # Unchanged file
                unchanged_files.append(relative_path)
        
        return new_files, modified_files, unchanged_files
    
    def _update_file_tracker(self, relative_path: str, file_hash: str, 
                            chunk_count: int, start_idx: int, end_idx: int):
        """Update tracker with newly indexed file info"""
        self.indexed_files[relative_path] = {
            'hash': file_hash,
            'last_indexed': datetime.now().isoformat(),
            'chunk_count': chunk_count,
            'vector_start_idx': start_idx,
            'vector_end_idx': end_idx
        }
    
    # ========================================================================
    # CORE EXTRACTION AND CHUNKING (EXISTING)
    # ========================================================================
    
    def extract_text_from_pdf(self, pdf_path: str) -> tuple:
        """Extract text from PDF with page-level tracking"""
        print(f"  Extracting: {pdf_path}")
        client = self._get_doc_intel_client()
        
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        poller = client.begin_analyze_document(
            "prebuilt-read",
            pdf_bytes,
            content_type="application/pdf"
        )
        
        result = poller.result()
        
        # Extract text with page numbers
        page_texts = []
        for page in result.pages:
            page_num = page.page_number
            page_content = ""
            if hasattr(page, 'lines') and page.lines:
                for line in page.lines:
                    page_content += line.content + " "
            
            page_texts.append({
                'page_number': page_num,
                'text': page_content.strip()
            })
        
        full_text = result.content
        
        print(f"  ✓ {len(result.pages)} pages, {len(full_text)} characters")
        return full_text, page_texts
    
    def chunk_text_with_pages(self, full_text: str, page_texts: List[Dict], 
                              chunk_size: int = 1024, overlap: int = 200) -> List[Dict]:
        """Split text into chunks while tracking which pages each chunk spans"""
        char_chunk_size = chunk_size * 4
        char_overlap = overlap * 4
        
        # Build character position → page number mapping
        char_to_page = []
        current_pos = 0
        
        for page_info in page_texts:
            page_num = page_info['page_number']
            page_text = page_info['text']
            
            page_start = full_text.find(page_text, current_pos)
            if page_start == -1:
                page_start = current_pos
            
            page_end = page_start + len(page_text)
            
            char_to_page.append({
                'start': page_start,
                'end': page_end,
                'page': page_num
            })
            
            current_pos = page_end
        
        # Create chunks with page tracking
        chunks_with_pages = []
        start = 0
        
        while start < len(full_text):
            end = start + char_chunk_size
            chunk_text = full_text[start:end]
            
            # Sentence boundary detection
            if end < len(full_text):
                last_sentence = max(
                    chunk_text.rfind('.'),
                    chunk_text.rfind('?'),
                    chunk_text.rfind('!')
                )
                if last_sentence > char_chunk_size * 0.5:
                    chunk_text = chunk_text[:last_sentence + 1]
                    end = start + last_sentence + 1
            
            if chunk_text.strip():
                # Determine which pages this chunk spans
                chunk_pages = set()
                
                for page_map in char_to_page:
                    chunk_start = start
                    chunk_end = end
                    page_start = page_map['start']
                    page_end = page_map['end']
                    
                    if not (chunk_end <= page_start or chunk_start >= page_end):
                        chunk_pages.add(page_map['page'])
                
                page_list = sorted(list(chunk_pages))
                
                chunks_with_pages.append({
                    'text': chunk_text.strip(),
                    'pages': page_list if page_list else [1]
                })
            
            start = end - char_overlap
        
        return chunks_with_pages
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector for single text (used for queries)"""
        client = self._get_openai_client()
        embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        
        if not embedding_deployment:
            raise ValueError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT not found in .env")
        
        response = client.embeddings.create(
            model=embedding_deployment,
            input=text
        )
        
        embedding_array = np.array(response.data[0].embedding, dtype=np.float32)
        
        if self.embedding_dim is None:
            self.embedding_dim = len(embedding_array)
            print(f"✓ Detected embedding dimension: {self.embedding_dim}")
        
        return embedding_array
    
    def get_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """OPTIMIZED: Generate embeddings for multiple texts in one API call"""
        client = self._get_openai_client()
        embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        
        if not embedding_deployment:
            raise ValueError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT not found in .env")
        
        response = client.embeddings.create(
            model=embedding_deployment,
            input=texts
        )
        
        embeddings = []
        for item in response.data:
            embedding_array = np.array(item.embedding, dtype=np.float32)
            embeddings.append(embedding_array)
        
        if self.embedding_dim is None:
            self.embedding_dim = len(embedding_array)
            print(f"✓ Detected embedding dimension: {self.embedding_dim}")
        
        return embeddings
    
    # ========================================================================
    # BUILD INDEX (EXISTING - Modified for tracking)
    # ========================================================================
    
    def build_index_from_pdfs(self, pdf_folder: str = "input"):
        """Build FAISS index from all PDFs with page tracking"""
        print("\n" + "="*70)
        print("BUILDING KNOWLEDGE BASE (with Page Tracking)")
        print("="*70)
        
        pdf_folder_path = Path(pdf_folder)
        pdf_files = list(pdf_folder_path.rglob("*.pdf"))
        
        if len(pdf_files) == 0:
            print(f"No PDFs found in {pdf_folder}/")
            return
        
        print(f"Found {len(pdf_files)} PDF(s) in folder tree:\n")
        for pdf_file in pdf_files:
            relative_path = pdf_file.relative_to(pdf_folder_path)
            print(f"  • {relative_path}")
        print()
        
        all_chunks = []
        all_metadata = []
        
        for pdf_path in pdf_files:
            relative_path = str(pdf_path.relative_to(pdf_folder_path))
            file_hash = self._calculate_file_hash(str(pdf_path))
            
            try:
                start_idx = len(all_chunks)
                
                # Extract with page tracking
                full_text, page_texts = self.extract_text_from_pdf(str(pdf_path))
                
                # Create chunks with page numbers
                chunks_with_pages = self.chunk_text_with_pages(full_text, page_texts)
                print(f"  ✓ Created {len(chunks_with_pages)} chunks")
                
                # Store chunks and metadata
                for idx, chunk_info in enumerate(chunks_with_pages):
                    all_chunks.append(chunk_info['text'])
                    all_metadata.append({
                        'source': relative_path,
                        'chunk_id': idx,
                        'total_chunks': len(chunks_with_pages),
                        'total_pages': len(page_texts),
                        'page_numbers': chunk_info['pages'],
                        'chunk_preview': chunk_info['text'][:150]
                    })
                
                # Update tracker
                end_idx = len(all_chunks) - 1
                self._update_file_tracker(relative_path, file_hash, 
                                         len(chunks_with_pages), start_idx, end_idx)
            
            except Exception as e:
                print(f"  ✗ Error processing {relative_path}: {str(e)}")
                continue
        
        if len(all_chunks) == 0:
            print("\n✗ No chunks created")
            return
        
        print(f"\nTotal chunks: {len(all_chunks)}")
        
        # Generate embeddings in BATCHES
        print("Generating embeddings (batched - much faster!)...")
        embeddings = []
        BATCH_SIZE = 100
        total_batches = (len(all_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(0, len(all_chunks), BATCH_SIZE):
            batch_chunks = all_chunks[batch_idx:batch_idx + BATCH_SIZE]
            try:
                batch_embeddings = self.get_embeddings_batch(batch_chunks)
                embeddings.extend(batch_embeddings)
                current_batch = (batch_idx // BATCH_SIZE) + 1
                print(f"  Batch {current_batch}/{total_batches} complete ({len(embeddings)}/{len(all_chunks)} chunks)")
            except Exception as e:
                print(f"  ✗ Error in batch {current_batch}: {str(e)}")
                for _ in range(len(batch_chunks)):
                    if self.embedding_dim:
                        embeddings.append(np.zeros(self.embedding_dim, dtype=np.float32))
        
        print(f"✓ Generated {len(embeddings)} embeddings")
        
        # Create FAISS index
        print(f"Building FAISS index with dimension {self.embedding_dim}...")
        embeddings_matrix = np.array(embeddings)
        self.faiss_index = faiss.IndexFlatL2(self.embedding_dim)
        self.faiss_index.add(embeddings_matrix)
        self.chunks = all_chunks
        self.metadata = all_metadata
        
        print(f"✓ FAISS index built with {self.faiss_index.ntotal} vectors")
        self.save_index()
        
        print("\n" + "="*70)
        print("KNOWLEDGE BASE READY")
        print("="*70)
    
    # ========================================================================
    # APPEND TO INDEX (NEW - Auto-sync capability)
    # ========================================================================
    
    def append_to_index(self, new_files: List[tuple], pdf_folder: str = "input"):
        """
        Append new files to existing index without rebuilding
        
        Args:
            new_files: List of (pdf_path, relative_path, file_hash) tuples
            pdf_folder: Base folder path
        """
        print("\n" + "="*70)
        print(f"APPENDING {len(new_files)} NEW FILE(S) TO KNOWLEDGE BASE")
        print("="*70)
        
        for pdf_path, relative_path, file_hash in new_files:
            print(f"\n📄 Processing: {relative_path}")
        
        new_chunks = []
        new_metadata = []
        
        for pdf_path, relative_path, file_hash in new_files:
            try:
                start_idx = len(self.chunks) + len(new_chunks)
                
                # Extract with page tracking
                full_text, page_texts = self.extract_text_from_pdf(str(pdf_path))
                
                # Create chunks with page numbers
                chunks_with_pages = self.chunk_text_with_pages(full_text, page_texts)
                print(f"  ✓ Created {len(chunks_with_pages)} chunks")
                
                # Store chunks and metadata
                for idx, chunk_info in enumerate(chunks_with_pages):
                    new_chunks.append(chunk_info['text'])
                    new_metadata.append({
                        'source': relative_path,
                        'chunk_id': idx,
                        'total_chunks': len(chunks_with_pages),
                        'total_pages': len(page_texts),
                        'page_numbers': chunk_info['pages'],
                        'chunk_preview': chunk_info['text'][:150]
                    })
                
                # Update tracker
                end_idx = start_idx + len(chunks_with_pages) - 1
                self._update_file_tracker(relative_path, file_hash, 
                                         len(chunks_with_pages), start_idx, end_idx)
            
            except Exception as e:
                print(f"  ✗ Error processing {relative_path}: {str(e)}")
                continue
        
        if len(new_chunks) == 0:
            print("\n✗ No new chunks created")
            return
        
        print(f"\n✓ Total new chunks: {len(new_chunks)}")
        
        # Generate embeddings for new chunks
        print("Generating embeddings for new chunks...")
        embeddings = []
        BATCH_SIZE = 100
        total_batches = (len(new_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(0, len(new_chunks), BATCH_SIZE):
            batch_chunks = new_chunks[batch_idx:batch_idx + BATCH_SIZE]
            try:
                batch_embeddings = self.get_embeddings_batch(batch_chunks)
                embeddings.extend(batch_embeddings)
                current_batch = (batch_idx // BATCH_SIZE) + 1
                print(f"  Batch {current_batch}/{total_batches} complete ({len(embeddings)}/{len(new_chunks)} chunks)")
            except Exception as e:
                print(f"  ✗ Error in batch {current_batch}: {str(e)}")
        
        print(f"✓ Generated {len(embeddings)} new embeddings")
        
        # Append to existing FAISS index
        print("Appending to FAISS index...")
        embeddings_matrix = np.array(embeddings)
        self.faiss_index.add(embeddings_matrix)
        
        # Append to chunks and metadata
        self.chunks.extend(new_chunks)
        self.metadata.extend(new_metadata)
        
        print(f"✓ FAISS index now has {self.faiss_index.ntotal} vectors (added {len(embeddings)})")
        
        # Save everything
        self.save_index()
        
        print("\n" + "="*70)
        print("✅ KNOWLEDGE BASE UPDATED")
        print("="*70)
    
    # ========================================================================
    # AUTO-SYNC (NEW - Smart detection and update)
    # ========================================================================
    
    def auto_sync(self, pdf_folder: str = "input") -> bool:
        """
        Automatically sync knowledge base with input folder
        
        Returns:
            True if sync was performed, False if already up-to-date
        """
        print("\n" + "="*70)
        print("🔍 AUTO-SYNC: Checking for new files...")
        print("="*70)
        
        # Load existing tracker
        self._load_document_tracker()
        
        # Check if index exists
        index_exists = self.load_index()
        
        if not index_exists:
            # No index - build from scratch
            print("\n🆕 No knowledge base found - building from scratch...")
            self.build_index_from_pdfs(pdf_folder)
            return True
        
        # Find new and modified files
        new_files, modified_files, unchanged_files = self._find_new_and_modified_files(pdf_folder)
        
        total_indexed = len(unchanged_files)
        total_new = len(new_files)
        total_modified = len(modified_files)
        
        print(f"\n📊 Scan Results:")
        print(f"  ✅ Already indexed: {total_indexed} file(s)")
        print(f"  🆕 New files: {total_new}")
        print(f"  🔄 Modified files: {total_modified}")
        
        if total_new == 0 and total_modified == 0:
            print("\n✅ Knowledge base is up-to-date!")
            return False
        
        # Process new files
        if total_new > 0:
            print(f"\n📥 New files to index:")
            for _, relative_path, _ in new_files:
                print(f"  • {relative_path}")
            
            self.append_to_index(new_files, pdf_folder)
        
        # Process modified files (treat as new)
        if total_modified > 0:
            print(f"\n🔄 Modified files detected:")
            for _, relative_path, _ in modified_files:
                print(f"  • {relative_path}")
            print("\n⚠️  Note: Modified files will be appended. Old versions remain in index.")
            print("    Use --rebuild to fully reindex if needed.")
            
            self.append_to_index(modified_files, pdf_folder)
        
        return True
    
    # ========================================================================
    # SAVE/LOAD INDEX (Modified for tracker)
    # ========================================================================
    
    def save_index(self):
        """Save FAISS index, metadata, and document tracker to disk"""
        index_file = os.path.join(self.index_path, "faiss.index")
        chunks_file = os.path.join(self.index_path, "chunks.pkl")
        metadata_file = os.path.join(self.index_path, "metadata.json")
        config_file = os.path.join(self.index_path, "config.json")
        
        faiss.write_index(self.faiss_index, index_file)
        
        with open(chunks_file, 'wb') as f:
            pickle.dump(self.chunks, f)
        
        with open(metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        with open(config_file, 'w') as f:
            json.dump({'embedding_dim': self.embedding_dim}, f)
        
        # Save document tracker
        self._save_document_tracker()
        
        print(f"\n✓ Index saved to {self.index_path}/")
    
    def load_index(self):
        """Load FAISS index, metadata, and document tracker from disk"""
        index_file = os.path.join(self.index_path, "faiss.index")
        chunks_file = os.path.join(self.index_path, "chunks.pkl")
        metadata_file = os.path.join(self.index_path, "metadata.json")
        config_file = os.path.join(self.index_path, "config.json")
        
        if not os.path.exists(index_file):
            return False
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.embedding_dim = config['embedding_dim']
        
        self.faiss_index = faiss.read_index(index_file)
        
        with open(chunks_file, 'rb') as f:
            self.chunks = pickle.load(f)
        
        with open(metadata_file, 'r') as f:
            self.metadata = json.load(f)
        
        # Load document tracker
        self._load_document_tracker()
        
        print(f"✓ Loaded index with {self.faiss_index.ntotal} vectors (dimension: {self.embedding_dim})")
        return True
    
    # ========================================================================
    # RETRIEVAL AND GENERATION (EXISTING - Unchanged)
    # ========================================================================
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Dict]:
        """Retrieve most similar chunks"""
        if self.faiss_index is None:
            raise ValueError("Index not loaded. Please load or build index first.")
        
        query_embedding = self.get_embedding(query)
        query_vector = np.array([query_embedding])
        
        distances, indices = self.faiss_index.search(query_vector, top_k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            results.append({
                'chunk': self.chunks[idx],
                'metadata': self.metadata[idx],
                'distance': float(distance)
            })
        
        return results
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate CRISP, context-aware answer with conversation memory"""
        client = self._get_openai_client()
        chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        
        if not chat_deployment:
            raise ValueError("AZURE_OPENAI_CHAT_DEPLOYMENT not found in .env")
        
        # Build context from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            source = chunk['metadata']['source']
            distance = chunk.get('distance', 0)
            relevance = chunk.get('relevance_score', None)
            similarity_pct = (1 / (1 + distance)) * 100
            
            context_header = f"Document {i}: {source}"
            if relevance:
                context_header += f" (AI Relevance: {relevance:.1f}/10, Similarity: {similarity_pct:.0f}%)"
            else:
                context_header += f" (Similarity: {similarity_pct:.0f}%)"
            
            context_parts.append(f"""
{context_header}
{'=' * 70}
{chunk['chunk']}
{'=' * 70}
""")
        
        context = "\n".join(context_parts)
        
        # Add conversation history if memory is enabled
        conversation_history = ""
        if self.enable_memory and self.memory and not self.memory.is_empty():
            history_text = self.memory.get_conversation_string(
                user_prefix="User",
                assistant_prefix="Assistant"
            )
            
            if self._estimate_tokens(history_text) < 2000:
                conversation_history = f"""
PREVIOUS CONVERSATION:
{history_text}
"""
            else:
                recent_history = self.memory.get_last_n_exchanges(3)
                history_lines = []
                for msg in recent_history:
                    prefix = "User" if msg["role"] == "user" else "Assistant"
                    history_lines.append(f"{prefix}: {msg['content']}")
                conversation_history = f"""
RECENT CONVERSATION (last 3 exchanges):
{chr(10).join(history_lines)}
"""
        
        # System prompt
        system_prompt = """You are an expert medical document assistant that provides CONCISE, ACCURATE answers.

Answer Style Rules:
1. MATCH answer format to question type:
   - Yes/No questions → "Yes/No" + brief reason (1 sentence)
   - "What is X?" → Direct answer first, then context if needed
   - "How many?" → Number first, then brief list
   - Lists → Bullet points only

2. BE CONCISE - no unnecessary elaboration
3. Start with the direct answer IMMEDIATELY
4. Add supporting details ONLY if directly relevant
5. Cite sources using the file name from context, not "Document X"
6. Use conversation history to understand context and resolve references like "it", "that medication", "the patient"
7. Only say "I don't have enough information" if context contains NO relevant information

Answer Examples:
Q: "Was medication prescribed?" → A: "Yes. Metformin 500mg twice daily. [Source: Document 1]"
Q: "What medication?" → A: "Metformin 500mg twice daily for diabetes management. [Source: Document 1]"
Q: "Glucose level?" → A: "150 mg/dL (elevated, normal range: 70-100 mg/dL). [Source: Document 1]"
"""
        
        user_prompt = f"""{conversation_history}Based on the following documents, answer the question CONCISELY.

CONTEXT DOCUMENTS:
{context}

QUESTION: {query}

INSTRUCTIONS:
- Match answer length to question complexity
- Start with direct answer, add details only if needed
- Use information from ALL provided documents
- If this is a follow-up question, use the previous conversation context
- Cite which document(s) you used
- Prioritize documents with higher relevance scores

ANSWER:"""
        
        # Generate response
        response = client.chat.completions.create(
            model=chat_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )
        
        return response.choices[0].message.content
    
    def ask(self, query: str, top_k: int = 5, show_context: bool = False,
        enhancement_flags: dict = None, rerank_method: str = 'simple'):

        """Ask a question with GRANULAR enhancement controls"""
        print(f"\nQ: {query}")
        print("-" * 70)
        
        # Default flags if none provided
        if enhancement_flags is None:
            enhancement_flags = {'query': False, 'distance': False, 'rerank': False}
        
        # Track which enhancements are active
        active_enhancements = [k for k, v in enhancement_flags.items() if v]
        if active_enhancements:
            print(f"🔧 Active enhancements: {', '.join(active_enhancements)}")
        else:
            print("⚡ Fast mode (no enhancements)")
        
        enhanced_query = query
        
        # 1. QUERY ENHANCEMENT (Optional)
        if enhancement_flags.get('query') and ENHANCEMENTS_AVAILABLE:
            try:
                original_query = query
                enhanced_query = enhance_query_simple(query, domain='medical')
                if enhanced_query != original_query:
                    print(f"  ✓ Query enhanced: '{original_query[:40]}...' → '{enhanced_query[:40]}...'")
            except Exception as e:
                print(f"  ⚠ Query enhancement failed: {str(e)}")
                enhanced_query = query
        
        # Retrieve chunks
        print("Retrieving relevant information...")
        retrieve_count = top_k * 2 if any(enhancement_flags.values()) else top_k
        results = self.retrieve(enhanced_query, top_k=retrieve_count)
        print(f"  ✓ Retrieved {len(results)} chunks from vector database")
        
        # 2. DISTANCE FILTERING (Optional)
        if enhancement_flags.get('distance') and ENHANCEMENTS_AVAILABLE:
            try:
                before_count = len(results)
                results = filter_by_distance(results, max_distance=1.5, min_chunks=3)
                print(f"  ✓ Distance filtered: {before_count} → {len(results)} chunks")
            except Exception as e:
                print(f"  ⚠ Distance filtering failed: {str(e)}")
        
        # 3. LLM RERANKING (Optional)
        if enhancement_flags.get('rerank') and ENHANCEMENTS_AVAILABLE:
            try:
                print(f"  🤖 Reranking {len(results)} chunks using {rerank_method} method...")
                results = rerank_chunks(query, results, self._get_openai_client(),
                                    top_k=top_k, method=rerank_method, debug=True)
                
                if results and 'relevance_score' in results[0]:
                    top_score = results[0]['relevance_score']
                    print(f"  ✓ Reranked ({rerank_method}): top score={top_score:.1f}/10")

            except Exception as e:
                print(f"  ⚠ Reranking failed: {str(e)}")
                results = results[:top_k]
        else:
            results = results[:top_k]
        
        # Show context if requested
        if show_context:
            print("\nRetrieved Context:")
            for i, result in enumerate(results, 1):
                print(f"\n[{i}] From: {result['metadata']['source']}")
                print(f"    Distance: {result['distance']:.4f}")
                if 'relevance_score' in result:
                    print(f"    Relevance: {result['relevance_score']:.1f}/10")
                print(f"    {result['chunk'][:200]}...")
        
        # Generate answer
        print("Generating answer...\n")
        answer = self.generate_answer(query, results)
        
        # Store in conversation memory
        if self.enable_memory and self.memory:
            self.memory.add_exchange(query, answer)
        
        print("A:", answer)
        
        # Display sources
        sources = results
        print(f"\nSources:")
        for source in sources:
            doc_name = source['metadata']['source']
            pages = source['metadata'].get('page_numbers', [])
            if pages:
                if len(pages) == 1:
                    page_str = f"Page {pages[0]}"
                else:
                    page_str = f"Pages {pages[0]}-{pages[-1]}"
            else:
                page_str = "Page info unavailable"
            print(f"  • {doc_name} ({page_str})")
        
        # Show memory status
        if self.enable_memory and self.memory:
            print(f"\n💭 Memory: {self.memory.get_exchange_count()}/{self.memory.max_exchanges} exchanges stored")
        
        print("-" * 70)
        
        return answer, sources
    
    def chat(self):
        """Interactive chat interface"""
        print("\n" + "="*70)
        print("RAG CHATBOT - Interactive Mode (v3.3 AUTO-SYNC)")
        print("="*70)
        print("Commands:")
        print("  - Type your question (press Enter twice to submit)")
        print("  - Type 'context' to toggle context display")
        print("  - Type 'enhance [query|distance|rerank|all|none]' to toggle enhancements")
        print("  - Type 'history' to view conversation history")
        print("  - Type 'clear' to clear conversation history")
        print("  - Type 'memory' to toggle conversation memory")
        print("  - Type 'quit' or 'exit' to stop")
        
        if ENHANCEMENTS_AVAILABLE:
            print("  ✓ Enhancements: AVAILABLE")
        else:
            print("  ⚠ Enhancements: DISABLED (modules not found)")
        
        if self.enable_memory:
            print(f"  ✓ Memory: ENABLED (max {self.memory.max_exchanges} exchanges)")
        else:
            print("  ⚠ Memory: DISABLED")
        
        print("="*70 + "\n")
        
        show_context = False
        enhancement_flags = {'query': False, 'distance': False, 'rerank': False}
        
        while True:
            try:
                print("\nYou (press Enter twice to submit):")
                lines = []
                empty_count = 0
                
                while True:
                    line = input()
                    if line == '':
                        empty_count += 1
                        if empty_count >= 1 and len(lines) > 0:
                            break
                    else:
                        empty_count = 0
                        lines.append(line)
                
                user_input = ' '.join(lines).strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit']:
                    print("Goodbye!")
                    break
                
                if user_input.lower() == 'context':
                    show_context = not show_context
                    print(f"✓ Context display: {'ON' if show_context else 'OFF'}")
                    continue
                
                if user_input.lower().startswith('enhance'):
                    parts = user_input.lower().split()
                    if len(parts) > 1:
                        target = parts[1]
                        if target == 'all':
                            enhancement_flags = {'query': True, 'distance': True, 'rerank': True}
                            print("✓ All enhancements ENABLED")
                        elif target == 'none':
                            enhancement_flags = {'query': False, 'distance': False, 'rerank': False}
                            print("✓ All enhancements DISABLED")
                        elif target in ['query', 'distance', 'rerank']:
                            enhancement_flags[target] = not enhancement_flags[target]
                            status = 'ON' if enhancement_flags[target] else 'OFF'
                            print(f"✓ {target.capitalize()} enhancement: {status}")
                        else:
                            print("⚠ Usage: enhance [query|distance|rerank|all|none]")
                    else:
                        active = [k for k, v in enhancement_flags.items() if v]
                        print(f"Current: {', '.join(active) if active else 'none'}")
                    continue
                
                if user_input.lower() == 'history':
                    if self.enable_memory and self.memory:
                        if self.memory.is_empty():
                            print("💭 No conversation history yet")
                        else:
                            print("\n💭 Conversation History:")
                            print("=" * 70)
                            print(self.memory.get_conversation_string())
                            print("=" * 70)
                            print(f"\nStored: {self.memory.get_exchange_count()}/{self.memory.max_exchanges} exchanges")
                    else:
                        print("⚠ Memory is disabled")
                    continue
                
                if user_input.lower() == 'clear':
                    if self.enable_memory and self.memory:
                        self.memory.clear()
                        print("✓ Conversation history cleared")
                    else:
                        print("⚠ Memory is disabled")
                    continue
                
                if user_input.lower() == 'memory':
                    if ENHANCEMENTS_AVAILABLE and self.memory:
                        self.enable_memory = not self.enable_memory
                        print(f"✓ Conversation memory: {'ON' if self.enable_memory else 'OFF'}")
                    else:
                        print("⚠ Memory module not available")
                    continue
                
                # Process question
                # Process question
                rerank_method = getattr(self, 'rerank_method', 'simple')
                self.ask(user_input, show_context=show_context, enhancement_flags=enhancement_flags,
                        rerank_method=rerank_method)

            
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")


# ========================================================================
# MAIN EXECUTION (Modified for auto-sync)
# ========================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced RAG Chatbot v3.3 with AUTO-SYNC')
    parser.add_argument('--build', action='store_true', help='Force rebuild index from PDFs')
    parser.add_argument('--input', default='input', help='Input PDF folder')
    parser.add_argument('--index', default='knowledge_base', help='Index storage path')
    parser.add_argument('--query', type=str, help='Single query mode')
    parser.add_argument('--no-memory', action='store_true', help='Disable conversation memory')
    parser.add_argument('--max-exchanges', type=int, default=5, help='Max conversation exchanges to remember')
    parser.add_argument('--no-sync', action='store_true', help='Skip auto-sync check')
    parser.add_argument('--rerank-method', type=str, default='simple',
                   choices=['simple', 'detailed', 'pairwise'],
                   help='Reranking method: simple (fast), detailed (explained), pairwise (best)')
    
    args = parser.parse_args()
    
    # Initialize
# Initialize
    enable_mem = not args.no_memory
    chatbot = SimpleRAGChatbot(
        index_path=args.index,
        enable_memory=enable_mem,
        max_exchanges=args.max_exchanges
    )

    # Store rerank method for interactive mode
    chatbot.rerank_method = args.rerank_method

    
    try:
        if args.build:
            # Force rebuild
            print("🔄 Force rebuild requested...")
            chatbot.build_index_from_pdfs(pdf_folder=args.input)
        elif args.no_sync:
            # Skip auto-sync, just load existing
            if not chatbot.load_index():
                print("\n✗ No index found. Please run without --no-sync first.")
                exit(1)
        else:
            # AUTO-SYNC (default behavior)
            chatbot.auto_sync(pdf_folder=args.input)
        
        # Run query or chat
# Print reranker method info (if using query mode)
        if args.query:
            print(f"\n⚙️  Reranker method: {args.rerank_method}")
            if args.rerank_method == 'simple':
                print("   ⚡ Fast scoring (~8-10s)")
            elif args.rerank_method == 'detailed':
                print("   📝 With explanations (~12-15s)")
            elif args.rerank_method == 'pairwise':
                print("   🏆 Most accurate (~25-30s)")

        # Run query or chat
        if args.query:
            flags = {'query': True, 'distance': True, 'rerank': True}  # Changed False → True
            chatbot.ask(args.query, show_context=True, 
                    enhancement_flags=flags,
                    rerank_method=args.rerank_method)  # Added this parameter
        else:
            chatbot.chat()

    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nPlease check your .env file has all required variables")
        exit(1)
