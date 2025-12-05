"""
Mag Mutual POC - Main Application
==================================
Modular structure with separate app files
Version: 5.0 - Added Chronology page and Medical Malpractice Claim Analyzer title
"""

import streamlit as st
st.cache_data.clear()
st.cache_resource.clear()

import base64
from pathlib import Path

# Import your app modules
from frontend.chatbot_app import render_chatbot_app, init_chatbot_session_state
from frontend.form_filler_app import render_form_filler_app, init_form_filler_session_state
from frontend.chronology_app import render_chronology_app, init_chronology_session_state

# ═══════════════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION (Must be first Streamlit command)
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Medical Malpractice Claim Analyzer",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════
def init_global_session_state():
    """Initialize session state for navigation and theme"""
    if 'current_app' not in st.session_state:
        st.session_state.current_app = 'form_filler'
    if 'theme_mode' not in st.session_state:
        st.session_state.theme_mode = 'light'

# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════
def get_base64_image(image_path):
    """Convert image to base64 for embedding in HTML"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

# ═══════════════════════════════════════════════════════════════════════════
# HEADER WITH NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════
def render_header():
    """Render the fixed header with logo on left, title in center, and navigation buttons on right"""
    
    # Enhanced CSS - FORCE BLUE color for primary buttons
    st.markdown("""
        <style>
        /* Force blue color for primary buttons */
        .stButton > button[kind="primary"] {
            background-color: #1E90FF !important;
            color: white !important;
            border: none !important;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #1873CC !important;
        }
        /* Secondary button styling */
        .stButton > button[kind="secondary"] {
            background-color: #f0f2f6 !important;
            color: #262730 !important;
            border: 1px solid #d1d5db !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background-color: #e0e2e6 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create header: Logo (left) + Title (center) + Navigation Buttons (right)
    header_col1, header_col2, header_col3 = st.columns([0.2, 0.4, 0.4])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LEFT: Logo Only
    # ═══════════════════════════════════════════════════════════════════════════
    with header_col1:
        st.markdown('<div style="margin-top: -50px;">', unsafe_allow_html=True)
        
        # Try to load and display logo
        logo_base64 = get_base64_image("assets/logo.png")
        if logo_base64:
            st.markdown(
                f'<img src="data:image/png;base64,{logo_base64}" style="height:100px;margin-top:-85px">',
                unsafe_allow_html=True
            )
        else:
            st.markdown('<span style="font-size:20px;">⚕️</span>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CENTER: Title
    # ═══════════════════════════════════════════════════════════════════════════
    with header_col2:
        st.markdown(
            '<div style="margin-top: -40px;">'
            '<p style="font-size:30px; font-weight:700;width:100%;white-space:nowrap; color:#1E90FF; margin:0; padding:0; text-align:center; margin-left:100px">'
            'Medical Malpractice Claim Analyzer</p>'
            '</div>',
            unsafe_allow_html=True
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RIGHT: Navigation Buttons (3 buttons)
    # ═══════════════════════════════════════════════════════════════════════════
    with header_col3:
        st.markdown('<div style="margin-top: 74px;">', unsafe_allow_html=True)
        
        nav_col1, nav_col2, nav_col3 = st.columns(3)
        
        # Form Filler Button
        with nav_col1:
            if st.session_state.current_app == 'form_filler':
                if st.button(
                    "📋 Form Filler",
                    key="nav_form",
                    use_container_width=True,
                    type="primary",
                    help="Currently viewing Form Filler"
                ):
                    st.session_state.current_app = 'form_filler'
                    st.rerun()
            else:
                if st.button(
                    "📋 Form Filler",
                    key="nav_form_inactive",
                    use_container_width=True,
                    type="secondary",
                    help="Switch to Form Filler"
                ):
                    st.session_state.current_app = 'form_filler'
                    st.rerun()
        
        # Chronology Button
        with nav_col2:
            if st.session_state.current_app == 'chronology':
                if st.button(
                    "📅 Chronology",
                    key="nav_chronology",
                    use_container_width=True,
                    type="primary",
                    help="Currently viewing Chronology"
                ):
                    st.session_state.current_app = 'chronology'
                    st.rerun()
            else:
                if st.button(
                    "📅 Chronology",
                    key="nav_chronology_inactive",
                    use_container_width=True,
                    type="secondary",
                    help="Switch to Chronology"
                ):
                    st.session_state.current_app = 'chronology'
                    st.rerun()
        
        # Chat Bot Button
        with nav_col3:
            if st.session_state.current_app == 'chatbot':
                if st.button(
                    "💬 Chat Bot",
                    key="nav_chatbot",
                    use_container_width=True,
                    type="primary",
                    help="Currently viewing Chat Bot"
                ):
                    st.session_state.current_app = 'chatbot'
                    st.rerun()
            else:
                if st.button(
                    "💬 Chat Bot",
                    key="nav_chatbot_inactive",
                    use_container_width=True,
                    type="secondary",
                    help="Switch to Chat Bot"
                ):
                    st.session_state.current_app = 'chatbot'
                    st.rerun()
    
    # Divider line below header
    st.divider()
  
# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════
def main():
    """Main application entry point"""
    
    # Initialize global state
    init_global_session_state()
    
    # Render header with navigation
    render_header()
    
    # Route to appropriate app
    if st.session_state.current_app == 'chatbot':
        init_chatbot_session_state()
        render_chatbot_app()
    elif st.session_state.current_app == 'form_filler':
        init_form_filler_session_state()
        render_form_filler_app()
    elif st.session_state.current_app == 'chronology':
        init_chronology_session_state()
        render_chronology_app()

if __name__ == "__main__":
    main()
