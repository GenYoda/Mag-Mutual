"""
Chronology App Module
=====================
Chronology of events functionality with PDF preview and download
"""

import streamlit as st
import time
from pathlib import Path
import fitz  # PyMuPDF

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
DEMO_CHRONOLOGY_PATH = "demo_assets/chronology/file.pdf"
PREVIEW_PAGES = 10  # Number of pages to show in preview (change this value as needed)

# ═══════════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════
def init_chronology_session_state():
    """Initialize all session state variables for chronology"""
    if 'chronology_generated' not in st.session_state:
        st.session_state.chronology_generated = False
    if 'chronology_kb_sync_status' not in st.session_state:
        st.session_state.chronology_kb_sync_status = None
    if 'chronology_input_files_data' not in st.session_state:
        st.session_state.chronology_input_files_data = []

# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════
def load_pdf_file(pdf_path: str) -> bytes:
    """Load PDF file and return bytes"""
    try:
        with open(pdf_path, "rb") as f:
            return f.read()
    except Exception as e:
        st.error(f"Error loading PDF: {str(e)}")
        return None

def extract_first_n_pages(pdf_path: str, num_pages: int) -> tuple:
    """Extract first N pages from PDF and return as bytes"""
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        # Create a new PDF with only first N pages
        new_doc = fitz.open()
        pages_to_extract = min(num_pages, total_pages)
        
        for page_num in range(pages_to_extract):
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        
        # Save to bytes
        pdf_bytes = new_doc.tobytes()
        
        # Close documents
        doc.close()
        new_doc.close()
        
        return pdf_bytes, pages_to_extract, total_pages
    except Exception as e:
        st.error(f"Error extracting pages: {str(e)}")
        return None, 0, 0

# ═══════════════════════════════════════════════════════════════════════════
# MAIN RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════
def render_chronology_app():
    """Main function to render the complete chronology app"""
    
    from streamlit_pdf_viewer import pdf_viewer
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1: Knowledge Base Upload (Dummy)
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown(
        '<p style="font-size:16px; font-weight:600; margin-bottom:5px;">'
        '📁 Upload Input Documents </p>',
        unsafe_allow_html=True,
    )
    
    # Show sync status if already synced
    if st.session_state.chronology_input_files_data and st.session_state.chronology_kb_sync_status == "synced":
        st.success("✅ Documents synced to knowledge base")
    
    # File uploader
    input_files = st.file_uploader(
        "Upload PDF documents for knowledge base",
        type=["pdf", "zip"],
        accept_multiple_files=True,
        key="chronology_input_docs",
        label_visibility="collapsed",
    )
    
    if input_files:
        # Store file metadata only (not bytes) to avoid issues with large ZIP files
        st.session_state.chronology_input_files_data = [
            {"name": f.name, "type": f.type, "size": f.size}
            for f in input_files
        ]
        
        # Display file info
        file_names = [f.name for f in input_files]
        st.info(f"📤 {len(input_files)} document(s) selected: {', '.join(file_names)}")
        
        if st.button("🔄 Sync to Knowledge Base", key="chronology_sync_kb_btn"):
            with st.spinner("Syncing documents to knowledge base..."):
                time.sleep(2)  # Simulated delay
                st.session_state.chronology_kb_sync_status = "synced"
                st.success(
                    f"✅ Successfully synced {len(input_files)} document(s) to knowledge base!"
                )
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2: Chronology of Events
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown(
        '<p style="font-size:20px; font-weight:700; margin-bottom:10px;">'
        '📅 Chronology of Events</p>',
        unsafe_allow_html=True,
    )
    
    # Get Chronology Button
    if st.button("📋 Get Chronology", key="get_chronology_btn", type="primary"):
        with st.spinner("Generating chronology... Please wait"):
            time.sleep(5)  # 5 second loader
            st.session_state.chronology_generated = True
        st.rerun()
    

    
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3: PDF Preview and Download
    # ═══════════════════════════════════════════════════════════════════════
    if st.session_state.chronology_generated:
        st.markdown("---")
        st.markdown(
            '<p style="font-size:16px; font-weight:600; margin-bottom:5px;">'
            '📄 Preview</p>',
            unsafe_allow_html=True,
        )
        
        # Check if PDF file exists
        pdf_path = Path(DEMO_CHRONOLOGY_PATH)
        
        if pdf_path.exists():
            # Extract first N pages for preview
            preview_bytes, pages_shown, total_pages = extract_first_n_pages(
                str(pdf_path), 
                PREVIEW_PAGES
            )
            
            if preview_bytes:
                # Show info about preview limitation
                if total_pages > PREVIEW_PAGES:
                    st.info(
                        f"ℹ️ Showing first {pages_shown} of {total_pages} pages in preview. "
                        f"Download the full document to see all pages."
                    )
                else:
                    st.info(f"ℹ️ Showing all {total_pages} pages.")
                
                # Centered, larger PDF Viewer
                st.markdown(
                    '<div style="display:flex; justify-content:center;">',
                    unsafe_allow_html=True,
                )
                pdf_viewer(preview_bytes, width=1100, height=650)
                st.markdown(
                    '</div>',
                    unsafe_allow_html=True,
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Download button (provides FULL PDF)
                full_pdf_bytes = load_pdf_file(str(pdf_path))
                if full_pdf_bytes:
                    st.download_button(
                        label="⬇️ Download Chronology",
                        data=full_pdf_bytes,
                        file_name="chronology.pdf",
                        mime="application/pdf",
                        key="download_chronology_btn",
                        type="primary"
                    )
        else:
            st.warning(f"⚠️ Chronology PDF not found at: {DEMO_CHRONOLOGY_PATH}")
            st.info("Please ensure the file exists at the specified path.")
 