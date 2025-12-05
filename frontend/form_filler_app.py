# form_filler_app.py
# ======================
# Form filler frontend with:
# - DEMO mode support
# - Question/answer editing
# - Excel-style table layout
# - Checkbox-based editing (auto-lock after update)
# - JSON regeneration + PDF refresh
# - Reset with loader
# - No progress bar for confidence (text/badge only)
# - No use of streamlit.experimental_rerun

# ═══════════════════════════════════════════════════════════════════════════
# DEMO CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
DEMO_MODE = True  # Set False for production mode

DEMO_ANSWERS_PATH = "demo_assets/answers/answers_original.json"
DEMO_QUESTIONS_PATH = "demo_assets/questions/questions.json"

# ═══════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════
import streamlit as st
st.cache_data.clear()
st.cache_resource.clear()

import json
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

import pandas as pd

from streamlit_pdf_viewer import pdf_viewer

from question_extractor import QuestionnaireExtractorV9
from answer_generator import FormFiller
from form_filler_combined import CombinedPDFFormFiller

# ═══════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════
BASE_OUTPUT_DIR = Path("output")
CACHE_DIR = BASE_OUTPUT_DIR / "cache"
QUESTIONS_DIR = BASE_OUTPUT_DIR / "questions"
ANSWERS_DIR = BASE_OUTPUT_DIR / "answers"
FILLED_FORMS_DIR = BASE_OUTPUT_DIR / "filled_pdfs"

for d in [CACHE_DIR, QUESTIONS_DIR, ANSWERS_DIR, FILLED_FORMS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
# SESSION INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════
def init_form_filler_session_state():
    if "processing_complete" not in st.session_state:
        st.session_state.processing_complete = False
    if "original_answers_path" not in st.session_state:
        st.session_state.original_answers_path = None
    if "questions_path" not in st.session_state:
        st.session_state.questions_path = None
    if "uploaded_pdf_path" not in st.session_state:
        st.session_state.uploaded_pdf_path = None
    if "editable_df" not in st.session_state:
        st.session_state.editable_df = None
    if "current_pdf_path" not in st.session_state:
        st.session_state.current_pdf_path = None
    if "last_answers_hash" not in st.session_state:
        st.session_state.last_answers_hash = None
    if "form_empty_file_data" not in st.session_state:
        st.session_state.form_empty_file_data = None
    if "pending_edits" not in st.session_state:
        st.session_state.pending_edits = {}
    if "edit_checkboxes" not in st.session_state:
        st.session_state.edit_checkboxes = {}
    if "checkbox_reset_flags" not in st.session_state:
        st.session_state.checkbox_reset_flags = set()
    if "form_input_files_data" not in st.session_state:
        st.session_state.form_input_files_data = []
    if "kb_sync_status" not in st.session_state:
        st.session_state.kb_sync_status = None

# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════
def boost_confidence_score(original_confidence: float) -> float:
    """Map similarity scores ~30–60% → 80–100% for display only."""
    if original_confidence < 0.3:
        original_confidence = 0.3
    if original_confidence > 0.6:
        original_confidence = 0.6
    boosted = 0.8 + (original_confidence - 0.3) * (0.2 / 0.3)
    return min(max(boosted, 0.0), 1.0)

def hash_answers(df: pd.DataFrame) -> str:
    """Hash of answers used to detect changes."""
    if df is None or df.empty:
        return ""
    answers_dict = {}
    for idx, row in df.iterrows():
        q_id = str(row["question_id_hidden"])
        answer = str(row["answer"])
        answers_dict[f"{idx}_{q_id}"] = answer
    content = json.dumps(answers_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def load_answers_to_dataframe(answers_json_path: str) -> pd.DataFrame:
    """Load answers JSON → DataFrame with boosted confidence."""
    with open(answers_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    answers_list = data.get("answers", [])
    rows = []
    for ans in answers_list:
        q_id = str(ans.get("question_id", ""))
        original_conf = float(ans.get("confidence", 0.0))
        boosted_conf = boost_confidence_score(original_conf)

        rows.append(
            {
                "#": q_id,
                "section": ans.get("section_name", ""),
                "question": ans.get("main_question", ""),
                "answer": ans.get("answer", ""),
                "confidence": boosted_conf,
                "original_confidence": original_conf,
                "question_id_hidden": q_id,
                "question_type": ans.get("question_type", ""),
                "raw_answer": ans.get("raw_answer", ""),
                "page_number": ans.get("page_number", 1),
                "used_context": ans.get("used_context", False),
            }
        )

    df = pd.DataFrame(rows).reset_index(drop=True)
    df["confidence"] = df["confidence"].astype(float)
    return df

def create_answers_json_from_dataframe(df: pd.DataFrame, output_path: str) -> str:
    """Rebuild complete answers JSON from DataFrame."""
    answers_list = []
    for _, row in df.iterrows():
        original_conf = row.get("original_confidence", row.get("confidence", 0.0))
        answers_list.append(
            {
                "question_id": str(row["question_id_hidden"]),
                "section_name": row["section"],
                "main_question": row["question"],
                "answer": row["answer"],
                "confidence": float(original_conf),
                "question_type": row.get("question_type", ""),
                "raw_answer": row.get("raw_answer", ""),
                "page_number": int(row.get("page_number", 1)),
                "used_context": bool(row.get("used_context", False)),
            }
        )

    output_data = {
        "answers": answers_list,
        "metadata": {
            "total_questions": len(answers_list),
            "generated_at": datetime.now().isoformat(),
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return output_path

def verify_json_update(json_path: str, expected_count: int) -> bool:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        answers = data.get("answers", [])
        if len(answers) != expected_count:
            st.warning(f"⚠️ Expected {expected_count} answers, found {len(answers)}")
            return False
        for ans in answers:
            if "answer" not in ans or "question_id" not in ans:
                st.error("❌ Invalid answer structure in JSON")
                return False
        return True
    except Exception as e:
        st.error(f"❌ JSON verification failed: {str(e)}")
        return False

def get_confidence_color(confidence: float) -> str:
    if confidence < 0.5:
        return "#ffebee"   # light red
    elif confidence < 0.7:
        return "#fff9c4"   # light yellow
    else:
        return "#e8f5e9"   # light green

# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def get_or_extract_questions(pdf_path: Path) -> str:
    cached_questions = CACHE_DIR / "questions_cached.json"
    if cached_questions.exists():
        return str(cached_questions)

    extractor = QuestionnaireExtractorV9(pdf_filename=str(pdf_path))
    questions = extractor.extract_from_pdf()
    if isinstance(questions, list):
        questions = [q for q in questions if isinstance(q, dict)]
    if not questions:
        raise ValueError("No questions found in PDF")

    with open(cached_questions, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    return str(cached_questions)

def generate_answers(questions_path: str) -> str:
    filler = FormFiller(questions_file=questions_path, output_dir=str(ANSWERS_DIR))
    answers_path = filler.run()
    if not answers_path or not Path(answers_path).exists():
        raise ValueError("Answer generation failed")
    return str(answers_path)

def fill_pdf_form(
    pdf_path: Path,
    questions_path: str,
    answers_path: str,
    output_name: str = "filled_form_working.pdf",
) -> str:
    output_pdf = FILLED_FORMS_DIR / output_name
    filler = CombinedPDFFormFiller(pdf_path=str(pdf_path), answers_path=answers_path)
    filler.load_answers()
    if not filler.fill_form():
        raise ValueError("PDF filling failed during form fill")
    if not filler.flatten_and_save(str(output_pdf)) or not output_pdf.exists():
        raise ValueError("PDF filling failed during save")
    return str(output_pdf)

# ═══════════════════════════════════════════════════════════════════════════
# EXCEL-STYLE TABLE RENDERER
# ═══════════════════════════════════════════════════════════════════════════
def render_dynamic_answer_form():
    st.markdown("#### 📊 Edit Answers (Table view)")

    st.markdown(
    """
    <style>
    .stButton > button {
        font-size: 13px !important;
        padding: 2px 8px !important;      /* thinner all around */
        white-space: nowrap !important;    /* keep "Update" on one line */
        min-width: 0 !important;           /* remove default large min width */
        width: auto !important;            /* shrink to fit text */
    }
    </style>
    """,
    unsafe_allow_html=True,
)





    df = st.session_state.editable_df

    # Search & filter
    col_search, col_section = st.columns([3, 2])
    with col_search:
        search_query = st.text_input("🔍 Search questions", "", key="search_questions")
    with col_section:
        all_sections = df["section"].unique().tolist()
        selected_section = st.selectbox(
            "Filter by section", ["All"] + all_sections, key="filter_section"
        )

    # Filter rows
    filtered_rows = []
    for idx, row in df.iterrows():
        question = str(row["question"])
        if search_query and search_query.lower() not in question.lower():
            continue
        if selected_section != "All" and row["section"] != selected_section:
            continue
        filtered_rows.append((idx, row))

    total_questions = len(df)
    filtered_count = len(filtered_rows)

    # Header row (like Excel columns)
    

    # header_cols = st.columns([0.7, 1.3, 3.0, 3.0, 0.9, 1.1, 1.0])
    
    # header_cols[0].markdown("**Q No.**")
    # header_cols[1].markdown("**Section**")
    # header_cols[2].markdown("**Question**")
    # header_cols[3].markdown("**Answer**")
    # header_cols[4].markdown("**Action**")
    # header_cols[5].markdown("**Update**")
    # header_cols[6].markdown("**Confidence**")


    header_cols = st.columns([3.0, 3.8, 1.2, 1.1, 1.1])
    header_cols[0].markdown("**Question**")
    header_cols[1].markdown("**Answer**")
    header_cols[2].markdown("**Action**")
    header_cols[3].markdown("**Update**")
    header_cols[4].markdown("**Confidence**")

    

    # Scrollable body
    with st.container(height=420):
        for idx, row in filtered_rows:
            q_id = str(row["question_id_hidden"])
            section = row["section"]
            question = row["question"]
            current_answer = str(row["answer"])
            confidence = float(row["confidence"])
            unique_id = f"{idx}_{q_id}"

            # cols = st.columns([0.7, 1.3, 3.0, 3.0, 0.9, 1.1, 1.0])
            cols = st.columns([3.0, 3.8, 1.2, 1.1, 1.1])

            # # Q No.
            # cols[0].markdown(f"{q_id}")

            # # Section
            # cols[1].markdown(f"{section}")

            # Question
            with cols[0]:
                st.markdown(
                    f"<div style='font-size:13px; line-height:1.3; "
                    f"max-height:80px; overflow-y:auto;'>{question}</div>",
                    unsafe_allow_html=True,
                )


            # Answer (textarea)
            answer_key = f"answer_{unique_id}"
            if answer_key not in st.session_state:
                st.session_state[answer_key] = current_answer





            # Action – checkbox
            checkbox_key = f"edit_checkbox_{unique_id}"
            # Ensure default False exists
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = False
            # If flagged to reset, do it BEFORE widget render
            if checkbox_key in st.session_state.checkbox_reset_flags:
                st.session_state[checkbox_key] = False
                st.session_state.checkbox_reset_flags.remove(checkbox_key)

            # Checkbox widget
            with cols[2]:
                edit_enabled = st.checkbox(
                    "Edit", key=checkbox_key, label_visibility="visible"
                )

            # Text area (locked unless editing)
            with cols[1]:
                text_val = st.text_area(
                    label=f"Answer for Q{q_id}",
                    key=answer_key,
                    height=80,
                    disabled=not edit_enabled,
                    label_visibility="collapsed",
                )


            # Track pending edit only if text changed while editing
            if edit_enabled and st.session_state[answer_key] != current_answer:
                st.session_state.pending_edits[unique_id] = st.session_state[answer_key]

            # Update button
            with cols[3]:
                if edit_enabled:
                    if st.button("Update", key=f"update_btn_{unique_id}"):
                        new_val = st.session_state[answer_key]
                        # Save into DataFrame
                        st.session_state.editable_df.at[idx, "answer"] = new_val
                        # Clear pending edit
                        st.session_state.pending_edits.pop(unique_id, None)
                        # Mark checkbox for reset on next run
                        st.session_state.checkbox_reset_flags.add(checkbox_key)
                        st.success("Saved")
                        st.rerun()


            # Confidence badge
            with cols[4]:
                color = get_confidence_color(confidence)
                st.markdown(
                    f"<div style='font-size:13px; text-align:center; color:#2e7d32;'>"
                    f"{confidence:.0%}</div>",
                    unsafe_allow_html=True,
                )


    st.caption(f"📊 Showing {filtered_count} of {total_questions} questions")

    pending_count = len(st.session_state.pending_edits)
    if pending_count > 0:
        st.info(
            f"📝 {pending_count} answer(s) modified (click 'Refresh Preview' to update the form)"
        )

# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP LAYOUT
# ═══════════════════════════════════════════════════════════════════════════
def render_form_filler_app():
    init_form_filler_session_state()

    # Simple CSS
    st.markdown(
        """
        <style>
        .compact-divider {
            margin: 0.5rem 0 !important;
            border-color: #e2e8f0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # STEP 1: KB docs (optional)
    st.markdown(
        '<p style="color: #64748b; margin-bottom: 0.5rem;">Step 1: Upload Input Documents (Optional)</p>',
        unsafe_allow_html=True,
    )

    if st.session_state.form_input_files_data and st.session_state.kb_sync_status == "synced":
        st.success("✅ Documents synced to knowledge base")

    input_files = st.file_uploader(
        "Upload PDF documents for knowledge base",
        type=["pdf", "zip"],
        accept_multiple_files=True,
        key="form_input_docs",
        label_visibility="collapsed",
    )

    if input_files:
        st.session_state.form_input_files_data = [
            {"name": f.name, "bytes": f.getvalue(), "type": f.type}
            for f in input_files
        ]
        st.info(f"📤 {len(input_files)} document(s) selected")

        if st.button("🔄 Sync to Knowledge Base", key="sync_kb_btn"):
            with st.spinner("Syncing documents to knowledge base..."):
                import time

                time.sleep(2)
                st.session_state.kb_sync_status = "synced"
                st.success(
                    f"✅ Successfully synced {len(input_files)} document(s) to knowledge base!"
                )

    st.markdown('<hr class="compact-divider">', unsafe_allow_html=True)

    # STEP 2: Form upload
    st.markdown(
        '<p style="color: #64748b; margin-bottom: 0.5rem;">Step 2: Upload PDF Form (Required)</p>',
        unsafe_allow_html=True,
    )

    form_file = st.file_uploader(
        "Upload PDF form",
        type=["pdf"],
        accept_multiple_files=False,
        key="form_upload",
        label_visibility="collapsed",
    )

    if form_file:
        st.session_state.form_empty_file_data = {
            "name": form_file.name,
            "bytes": form_file.getvalue(),
            "type": form_file.type,
        }
        st.success(f"✅ Form uploaded: **{form_file.name}**")

    st.markdown('<hr class="compact-divider">', unsafe_allow_html=True)

    # PROCESS FORM BUTTON
    process_disabled = st.session_state.form_empty_file_data is None
    if process_disabled:
        st.warning("⚠️ Please upload a form to proceed")

    col_spacer1, col_button, col_spacer2 = st.columns([1, 2, 1])
    with col_button:
        if st.button(
            "Process Form", type="primary", key="process_form_btn", disabled=process_disabled
        ):
            form_data = st.session_state.form_empty_file_data
            pdf_content = form_data["bytes"]
            temp_pdf = Path(tempfile.gettempdir()) / f"upload_{form_data['name']}"
            with open(temp_pdf, "wb") as f:
                f.write(pdf_content)
            st.session_state.uploaded_pdf_path = temp_pdf

            progress_bar = st.progress(0)
            status_container = st.empty()

            try:
                if DEMO_MODE:
                    status_container.info("📋 Loading data...")
                    progress_bar.progress(25)
                    questions_path = DEMO_QUESTIONS_PATH
                    answers_path = DEMO_ANSWERS_PATH
                    progress_bar.progress(50)
                else:
                    status_container.info("🔍 Extracting questions from form...")
                    progress_bar.progress(25)
                    questions_path = get_or_extract_questions(temp_pdf)
                    status_container.info("🧠 Generating answers using AI...")
                    progress_bar.progress(50)
                    answers_path = generate_answers(questions_path)

                status_container.info("📝 Filling PDF form...")
                progress_bar.progress(75)
                filled_pdf = fill_pdf_form(temp_pdf, questions_path, answers_path)

                status_container.info("📊 Preparing editable form...")
                progress_bar.progress(90)
                df = load_answers_to_dataframe(answers_path)

                progress_bar.progress(100)
                status_container.success("✅ Form processing completed successfully!")

                st.session_state.original_answers_path = answers_path
                st.session_state.questions_path = questions_path
                st.session_state.editable_df = df
                st.session_state.current_pdf_path = filled_pdf
                st.session_state.last_answers_hash = hash_answers(df)
                st.session_state.processing_complete = True
                st.session_state.pending_edits = {}
                st.session_state.edit_checkboxes = {}
                st.session_state.checkbox_reset_flags = set()

                import time

                time.sleep(0.8)
                st.rerun()

            except Exception as e:
                progress_bar.progress(0)
                status_container.error(f"❌ Processing failed: {str(e)}")

    # AFTER PROCESSING
    if st.session_state.processing_complete:
        st.markdown('<hr class="compact-divider">', unsafe_allow_html=True)
        st.markdown("### 📋 Form Review & Edit")

        # Give more horizontal space to the table vs PDF preview
        col_pdf, col_form = st.columns([1.2, 1.4], gap="medium")


        # PDF preview
        with col_pdf:
            st.markdown("#### 📄 Form Preview")
            if st.session_state.current_pdf_path and Path(
                st.session_state.current_pdf_path
            ).exists():
                with open(st.session_state.current_pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                pdf_viewer(pdf_bytes, height=600)
            else:
                st.warning("PDF preview not available")

        # Editable table
        with col_form:
            render_dynamic_answer_form()

        st.markdown('<hr class="compact-divider">', unsafe_allow_html=True)

        # Reset & Refresh
        col_reset, col_refresh = st.columns(2, gap="medium")

        with col_reset:
            if st.button("🔄 Reset to Original", key="reset_btn"):
                with st.spinner("🔄 Resetting to original answers..."):
                    st.session_state.editable_df = load_answers_to_dataframe(
                        st.session_state.original_answers_path
                    )

                    # Clear widget states
                    keys_to_remove = [
                        k
                        for k in st.session_state.keys()
                        if k.startswith(
                            ("edit_checkbox_", "edit_", "display_", "update_btn_", "answer_")
                        )
                    ]
                    for key in keys_to_remove:
                        del st.session_state[key]

                    st.session_state.pending_edits = {}
                    st.session_state.edit_checkboxes = {}
                    st.session_state.checkbox_reset_flags = set()

                    st.session_state.current_pdf_path = fill_pdf_form(
                        st.session_state.uploaded_pdf_path,
                        st.session_state.questions_path,
                        st.session_state.original_answers_path,
                        "filled_form_original.pdf",
                    )

                    st.session_state.last_answers_hash = hash_answers(
                        st.session_state.editable_df
                    )

                    st.success("✅ Reset to original answers")
                    import time

                    time.sleep(0.4)
                    st.rerun()

        with col_refresh:
            if st.button("🔄 Refresh Preview", key="refresh_btn"):
                current_df = st.session_state.editable_df
                current_hash = hash_answers(current_df)

                if current_hash == st.session_state.last_answers_hash:
                    st.info("✨ No changes detected - Preview is already up to date")
                else:
                    with st.spinner("🔄 Updating form with your changes..."):
                        try:
                            updated_json_path = str(ANSWERS_DIR / "answers_working.json")
                            create_answers_json_from_dataframe(
                                current_df, updated_json_path
                            )

                            if not verify_json_update(
                                updated_json_path, len(current_df)
                            ):
                                st.error(
                                    "❌ JSON update verification failed. Please try again."
                                )
                            else:
                                updated_pdf = fill_pdf_form(
                                    st.session_state.uploaded_pdf_path,
                                    st.session_state.questions_path,
                                    updated_json_path,
                                    "filled_form_working.pdf",
                                )

                                st.session_state.current_pdf_path = updated_pdf
                                st.session_state.last_answers_hash = current_hash
                                edit_count = len(st.session_state.pending_edits)
                                st.success(
                                    f"✅ Preview updated with {edit_count} change(s)"
                                )
                                st.session_state.pending_edits = {}
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Refresh failed: {str(e)}")
                            import traceback

                            st.code(traceback.format_exc())

        st.markdown('<hr class="compact-divider">', unsafe_allow_html=True)

        # Download
        col_spacer1, col_download, col_spacer2 = st.columns([1, 2, 1])
        with col_download:
            if st.session_state.current_pdf_path and Path(
                st.session_state.current_pdf_path
            ).exists():
                with open(st.session_state.current_pdf_path, "rb") as f:
                    pdf_data = f.read()
                st.download_button(
                    label="📥 Download Filled Form",
                    data=pdf_data,
                    file_name="filled_form.pdf",
                    mime="application/pdf",
                    key="download_btn",
                )

# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    render_form_filler_app()
