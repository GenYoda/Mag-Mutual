"""
Chatbot App Module
==================
Complete chatbot functionality with RAG system
Extracted and modularized from app.py
"""

import streamlit as st
from advance_rag_memory import SimpleRAGChatbot
import time

SKIP_KB_SYNC = True 

# ═══════════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════
def init_chatbot_session_state():
    """Initialize all session state variables for chatbot"""
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'index_loaded' not in st.session_state:
        st.session_state.index_loaded = False
    if 'enable_memory' not in st.session_state:
        st.session_state.enable_memory = True
    if 'max_exchanges' not in st.session_state:
        st.session_state.max_exchanges = 5
    if 'enhancement_flags' not in st.session_state:
        # Enhancement flags default to True (kept internally enabled)
        st.session_state.enhancement_flags = {
            'query': True,      # Query Enrichment - enabled by default
            'distance': True,   # Distance Filtering - enabled by default
            'rerank': False     # Reranking - disabled
        }
    if 'show_sources' not in st.session_state:
        st.session_state.show_sources = True
    if 'show_sources_pane' not in st.session_state:
        st.session_state.show_sources_pane = True
    if 'all_sources' not in st.session_state:
        st.session_state.all_sources = {}
    if 'selected_question' not in st.session_state:
        st.session_state.selected_question = None
    if 'rerank_method' not in st.session_state:
        st.session_state.rerank_method = 'simple'

# ═══════════════════════════════════════════════════════════════════════════
# CHATBOT LOADING
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_resource
def load_chatbot(enable_memory, max_exchanges):
    """Load the RAG chatbot with caching"""
    try:
        chatbot = SimpleRAGChatbot(
            index_path="knowledge_base",
            enable_memory=enable_memory,
            max_exchanges=max_exchanges
        )
        if chatbot.load_index():
            return chatbot, True
        return None, False
    except Exception as e:
        st.error(f"Error loading chatbot: {str(e)}")
        return None, False

# ═══════════════════════════════════════════════════════════════════════════
# MESSAGE DISPLAY
# ═══════════════════════════════════════════════════════════════════════════
def display_message(role, content, response_time=None):
    """Display chat message with proper formatting"""
    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            st.markdown(content)
            if response_time:
                st.caption(f"⚡ Response time: {response_time:.1f}s")

# ═══════════════════════════════════════════════════════════════════════════
# CHAT AREA RENDERING
# ═══════════════════════════════════════════════════════════════════════════
def render_chat_area():
    """Render chat messages and input area"""
    st.subheader("💬 Conversation")
    
    # Display all messages
    for msg in st.session_state.chat_history:
        display_message(
            msg['role'], 
            msg['content'],
            msg.get('response_time')
        )
    
    # Chat input
    if st.session_state.index_loaded:
        user_input = st.chat_input("Ask a question about your medical documents...")
        
        if user_input:
            # Add user message
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_input
            })
            
            # Get AI response
            with st.spinner("Thinking..."):
                start_time = time.time()
                try:
                    answer, sources = st.session_state.chatbot.ask(
                        query=user_input,
                        top_k=5,
                        show_context=False,
                        enhancement_flags=st.session_state.enhancement_flags,
                        rerank_method=st.session_state.rerank_method
                    )
                    response_time = time.time() - start_time
                    
                    # Calculate question index
                    question_index = len([m for m in st.session_state.chat_history if m['role'] == 'assistant'])
                    
                    # Add assistant message
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': answer,
                        'response_time': response_time,
                        'question_index': question_index
                    })
                    
                    # Store sources
                    st.session_state.all_sources[question_index] = {
                        'question': user_input,
                        'answer': answer,
                        'sources': sources
                    }
                    st.session_state.selected_question = question_index
                    
                    st.rerun()
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': error_msg
                    })
    else:
        st.info("👈 Please load the chatbot from the sidebar first")

# ═══════════════════════════════════════════════════════════════════════════
# SOURCE REFERENCES PANE - WITH NESTED EXPANDERS
# ═══════════════════════════════════════════════════════════════════════════
def render_source_pane():
    """Render source references panel with nested expanders"""
    st.subheader("📚 Source References")
    
    if st.session_state.all_sources:
        # Build question options
        question_options = []
        question_map = {}
        for idx in sorted(st.session_state.all_sources.keys()):
            src_data = st.session_state.all_sources[idx]
            q_text = src_data['question']
            q_display = q_text[:45] + "..." if len(q_text) > 45 else q_text
            display_text = f"Q{idx + 1}: {q_display}"
            question_options.append(display_text)
            question_map[display_text] = idx
        
        # Question selector
        selected_display = st.selectbox(
            "Select Question:",
            question_options,
            index=len(question_options) - 1,
            key="chat_question_selector"
        )
        
        selected_idx = question_map[selected_display]
        source_data = st.session_state.all_sources[selected_idx]
        
        st.caption(f"**Question:** {source_data['question']}")
        st.caption(f"Showing **{len(source_data['sources'])}** sources")
        st.markdown("---")
        
        # Display sources with nested expanders
        for i, source in enumerate(source_data['sources'], 1):
            if isinstance(source, dict):
                meta = source.get('metadata', {})
                doc_name = meta.get('source', 'Unknown')
                chunk_text = source.get('chunk', 'No text available')
                page_num = meta.get('page', 'Unknown')
                
                # LEVEL 1: Collapsed - Just show source name
                with st.expander(f"📄 **[Source {i}]** {doc_name}", expanded=False):
                    # LEVEL 2: Preview text + page number
                    preview_text = chunk_text[:150] + "..." if len(chunk_text) > 150 else chunk_text
                    st.markdown(f"**Preview:**")
                    st.text(preview_text)
                    st.caption(f"📄 Page: {page_num}")
                    
                    # LEVEL 3: Full text in nested expander
                    with st.expander("📖 View Full Text", expanded=False):
                        st.text_area(
                            "Full Chunk Content",
                            chunk_text,
                            height=300,
                            key=f"source_full_text_{selected_idx}_{i}",
                            disabled=True,
                            label_visibility="collapsed"
                        )
    else:
        st.info("No sources yet. Start chatting to see source references!")

# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR RENDERING
# ═══════════════════════════════════════════════════════════════════════════
def render_sidebar():
    """Render chatbot sidebar with settings"""
    with st.sidebar:
        st.header("🤖 Chat Bot Settings")
        
        # Load/Reload button
        if st.button("🔄 Load/Reload Chatbot", type="primary", use_container_width=True, key="chat_load_button"):
            with st.spinner("Loading chatbot..."):
                chatbot, success = load_chatbot(
                    st.session_state.enable_memory,
                    st.session_state.max_exchanges
                )
                if success:
                    st.session_state.chatbot = chatbot
                    st.session_state.index_loaded = True
                    st.success("✅ Chatbot loaded successfully!")
                else:
                    st.error("❌ Failed to load chatbot")
        
        st.markdown("---")
        
        # Memory settings
        st.subheader("💾 Memory Settings")
        st.session_state.enable_memory = st.checkbox(
            "Enable Conversation Memory",
            value=st.session_state.enable_memory,
            key="chat_enable_memory"
        )
        
        if st.session_state.enable_memory:
            st.session_state.max_exchanges = st.slider(
                "Max Memory Exchanges",
                min_value=1,
                max_value=10,
                value=st.session_state.max_exchanges,
                key="chat_max_exchanges"
            )
        
        st.markdown("---")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True, key="chat_clear_history"):
            st.session_state.chat_history = []
            st.session_state.all_sources = {}
            st.session_state.selected_question = None
            st.rerun()
        
        st.markdown("---")
        st.subheader("📚 Knowledge Base")
        upload_and_sync_documents()

# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT UPLOAD & SYNC
# ═══════════════════════════════════════════════════════════════════════════
def upload_and_sync_documents():
    """Upload PDFs and sync with knowledge base"""
    import shutil
    from pathlib import Path
    
    # Define input directory
    INPUT_DIR = Path("input")
    INPUT_DIR.mkdir(exist_ok=True)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "📄 Upload Medical Documents (PDF)",
        type=['pdf','zip'],
        accept_multiple_files=True,
        help="Upload one or more PDF files to add to the knowledge base",
        key="chat_doc_uploader"
    )
    
    if uploaded_files:
        st.info(f"📤 {len(uploaded_files)} file(s) selected")
        
        if st.button("🔄 Add to Knowledge Base", type="primary", use_container_width=True, key="chat_sync_kb"):
            saved_files = []
            with st.spinner("Uploading documents..."):
                for uploaded_file in uploaded_files:
                    file_path = INPUT_DIR / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    saved_files.append(uploaded_file.name)
                    st.success(f"✅ Saved: {uploaded_file.name}")

            if SKIP_KB_SYNC:
                import time
                time.sleep(2)  # simulate delay
                st.session_state.kb_sync_status = "synced"
                st.success(f"✅ (Demo) Knowledge base sync skipped. {len(saved_files)} document(s) ready.")
            else:
                with st.spinner("🔄 Syncing knowledge base... This may take a moment."):
                    try:
                        if st.session_state.chatbot:
                            synced = st.session_state.chatbot.auto_sync(pdf_folder="input")
                            if synced:
                                st.success(f"✅ Knowledge base updated with {len(saved_files)} document(s)!")
                                st.info("💡 The chatbot is now ready with updated knowledge.")
                                st.cache_resource.clear()
                                st.session_state.index_loaded = False
                                st.warning("⚠️ Please reload the chatbot to use the updated knowledge base.")
                            else:
                                st.info("ℹ️ Documents saved. Knowledge base was already up to date.")
                        else:
                            st.warning("⚠️ Please load the chatbot first, then upload documents.")
                    except Exception as e:
                        st.error(f"❌ Error syncing knowledge base: {str(e)}")

            with st.spinner("Uploading documents..."):
                # Save uploaded files to input directory
                for uploaded_file in uploaded_files:
                    file_path = INPUT_DIR / uploaded_file.name
                    
                    # Save file
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    saved_files.append(uploaded_file.name)
                    st.success(f"✅ Saved: {uploaded_file.name}")
            
            # Trigger auto-sync to rebuild knowledge base
            with st.spinner("🔄 Syncing knowledge base... This may take a moment."):
                try:
                    if st.session_state.chatbot:
                        # Run auto-sync to detect and add new files
                        synced = st.session_state.chatbot.auto_sync(pdf_folder="input")
                        
                        if synced:
                            st.success(f"✅ Knowledge base updated with {len(saved_files)} document(s)!")
                            st.info("💡 The chatbot is now ready with updated knowledge.")
                            
                            # Clear cache to reload chatbot with new index
                            st.cache_resource.clear()
                            st.session_state.index_loaded = False
                            st.warning("⚠️ Please reload the chatbot to use the updated knowledge base.")
                        else:
                            st.info("ℹ️ Documents saved. Knowledge base was already up to date.")
                    else:
                        st.warning("⚠️ Please load the chatbot first, then upload documents.")
                except Exception as e:
                    st.error(f"❌ Error syncing knowledge base: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════
# MAIN RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════
def render_chatbot_app():
    """Main function to render the complete chatbot app - called from main app"""
    
    # Render sidebar
    render_sidebar()
    
    # Main area with columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_chat_area()
    
    with col2:
        render_source_pane()
