"""
Form Filler Configuration
Easy-to-toggle enhancement flags and settings
"""

# ════════════════════════════════════════════════════════════════════════════
# ⚙️  ENHANCEMENT CONFIGURATION - EASY TO TOGGLE
# ════════════════════════════════════════════════════════════════════════════

ENABLE_QUERY_ENHANCEMENT = True      # Query expansion with keywords/synonyms
ENABLE_DISTANCE_FILTER = True        # Distance-based similarity filtering
ENABLE_RERANKING = False             # LLM-based reranking (DISABLED for speed)
ENABLE_CACHING = True                # Page/section-wise chunk caching
ENABLE_PARALLEL = True               # Thread-based parallel processing

# ════════════════════════════════════════════════════════════════════════════
# 🔄 PARALLELIZATION SETTINGS
# ════════════════════════════════════════════════════════════════════════════

MAX_WORKERS = 5                      # Number of parallel worker threads
TIMEOUT_PER_QUESTION = 30            # Max seconds per question

# ════════════════════════════════════════════════════════════════════════════
# 🔍 RAG PARAMETERS (Balanced mode - matching chatbot config)
# ════════════════════════════════════════════════════════════════════════════

TOP_K = 5                            # Retrieve top 5 chunks
DISTANCE_THRESHOLD = 1.5             # Max distance for relevance
SIMILARITY_TO_CONFIDENCE_SCALE = 0.01  # Convert similarity % to confidence (85 → 0.85)
TEMPERATURE = 0.3                    # LLM temperature (locked)
MAX_TOKENS = 400                     # LLM max tokens (locked)

# ════════════════════════════════════════════════════════════════════════════
# 📊 OUTPUT FORMAT - Configurable fields
# ════════════════════════════════════════════════════════════════════════════

OUTPUT_FIELDS = [
    "section_name",      # Section name from question
    "question_id",       # Question ID (e.g., "1", "2.1")
    "parent_question_id",# Parent ID if subquestion
    "main_question",     # The question text
    "question_type",     # Type: text, checkbox, radio, multi_select, date, numeric
    "answer",            # The answer
    "page_number",       # Page number(s) where answer found
    "confidence",        # Confidence score (0.0-1.0)
    "similarity",        # Similarity score (0-100)
]

# ════════════════════════════════════════════════════════════════════════════
# 📁 PATHS
# ════════════════════════════════════════════════════════════════════════════

KB_PATH = "knowledge_base"           # Knowledge base directory
QUESTIONS_DIR = "forms/questions"    # Input questions folder
ANSWERS_DIR = "forms/answers"        # Output answers folder

# ════════════════════════════════════════════════════════════════════════════
# 📝 QUESTION TYPES SUPPORTED
# ════════════════════════════════════════════════════════════════════════════

QUESTION_TYPES = {
    "text": "Free text input",
    "checkbox": "Yes/No/Unclear/Not Applicable",
    "yes_no_unclear": "Yes/No/Unclear (3 options)",
    "radio": "Single option from list",
    "multi_select": "Multiple options (select all that apply)",
    "date": "Date field (MM/DD/YYYY format)",
    "numeric": "Numeric input",
}

# ════════════════════════════════════════════════════════════════════════════
# ✅ CONFIDENCE THRESHOLDS
# ════════════════════════════════════════════════════════════════════════════

HIGH_CONFIDENCE_THRESHOLD = 0.75     # 75% similarity = high confidence
LOW_CONFIDENCE_THRESHOLD = 0.50      # Below 50% = flag for review



# Context System Configuration
ENABLE_CONTEXT_INJECTION = True  # Enable section-level context for dependent questions
CONTEXT_MAX_TOKENS = 2000        # Maximum tokens for context string (safety limit)
