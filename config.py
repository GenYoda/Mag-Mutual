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





#=======================CONFIG FOR chronology generation==========================



"""
Configuration for Chronology Generator with Pass 1 & Pass 2 separation
"""

# ============================================
# DATE EXTRACTION SETTINGS
# ============================================
DATE_FORMAT_PREFERENCE = "US"  # "US" (MM/DD/YYYY) or "EU" (DD/MM/YYYY)
OUTPUT_DATE_FORMAT = "%Y-%m-%d"  # Uniform output format
INCLUDE_VAGUE_DATES = False  # Extract fuzzy dates like "early 2023"
INCLUDE_FUTURE_DATES = True  # Include scheduled appointments

# ============================================
# OUTPUT SETTINGS
# ============================================
OUTPUT_DIR = "output"
CHECKPOINT_DIR = "output/checkpoints"

# ============================================
# DATE REGEX PATTERNS
# ============================================
DATE_PATTERNS = [
    # Month Day, Year
    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
    # Abbreviated Month Day, Year
    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(\d{1,2}),?\s+(\d{4})\b',
    # MM/DD/YYYY or MM-DD-YYYY
    r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',
    # YYYY-MM-DD
    r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',


    #additional Date patterns
    r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',  # 17 February 2023
    r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(\d{4})\b',  # 17 Feb 2023



]

# Common OCR errors to fix
OCR_CORRECTIONS = {
    'Febnary': 'February',
    'Febuary': 'February',
    'Januray': 'January',
    'Decemebr': 'December',
}

# ============================================
# PASS 1: MINIMAL EXTRACTION SETTINGS
# ============================================
PASS1_ENABLE_FILTERING = False  # Enable chunk classification before extraction

PASS1_FIELDS = [
    'date',           # Required: YYYY-MM-DD
    'time',           # Optional: HH:MM
    'event_type',     # imaging, lab, medication, procedure, consultation, other
    'facility',       # Name of the the Hospital or Institution
    'provider',       # Doctor Name or name of the person medical care or services
    'title',          # Title of the document Or Type of record or Procedure
    'description',    # COMPREHENSIVE narrative (120 - 200 words) - legally focused
    'sources'         # [{"document": "file.pdf", "pages": [1,2]}]
]


# Chunk classifier prompts (Pass 1 filtering)
CHUNK_CLASSIFIER_SYSTEM_PROMPT = """You are a medical-legal assistant. Your job is to decide whether each text chunk is related to the patient's medical care, or not."""

CHUNK_CLASSIFIER_USER_TEMPLATE = """You will receive several text chunks from medical records for a single claimant.

For EACH chunk, decide:
- is_claimant_event: true if the chunk clearly describes the claimant's own care, tests, procedures, symptoms, physical findings, diagnoses, or treatment.
- is_noise: true if the chunk is family history, other people, templates, educational text, admin/IT logs, or anything not clearly the claimant's own medical care.

Important:
- Respond ONLY with a JSON array.
- The array MUST have one object per chunk, in the same order as given.
- Do NOT include any extra text before or after the JSON.

The required JSON format is:
[
  {{
    "chunk_index": 0,
    "is_claimant_event": true,
    "is_noise": false,
    "reason": "Describes CT scan and findings for the claimant."
  }},
  {{
    "chunk_index": 1,
    "is_claimant_event": false,
    "is_noise": true,
    "reason": "Family history of mother, not claimant."
  }}
]

Here are the chunks:
{chunks_block}
"""



# Pass 1 extraction prompt (DETAILED event extraction for legal review)
PASS1_SYSTEM_PROMPT = """You are a medical-legal chronology analyst. Extract comprehensive, detailed information from medical records for legal case review. Capture everything medically and legally relevant. Do NOT summarize or shorten content."""

PASS1_USER_PROMPT = """Extract DETAILED medical events from the texts below for date: {date}

Return a JSON array with these fields for EACH distinct event:
- "date": YYYY-MM-DD format
- "time": HH:MM format or null if not mentioned
- "event_type": Must be one of: imaging, lab, medication, procedure, consultation, communication, other
- "facility": Name of the the Hospital or Institution
- "provider": Doctor Name or name of the person medical care or services
-  "title": - Exact Title of the document Else Type of record or Procedure
        - Examples: "CT Head, ECG, Nursing Notes,Laboratory Results"
- "description": COMPREHENSIVE NARRATIVE (see requirements below)

**DESCRIPTION REQUIREMENTS:**
Provide a **full narrative** capturing everything medically and legally relevant in the document.

MUST INCLUDE (when documented):
• Patient complaints and symptoms (onset, duration, severity, character)
• Vitals, physical exam findings, physical assessment (all values, normal and abnormal)
• Diagnostic thinking, differential diagnoses, clinical reasoning
• Labs, imaging, tests ordered OR NOT ordered (include all results, values, reference ranges)
• Medications given (drug name, dosage, route, time, patient response)
• Provider actions, instructions, recommendations, follow-up plan
• Delays, omissions, gaps in care, missing documentation
• Discrepancies or contradictions between providers or notes
• Any potential deviations from standard of care
• Communication between providers, with patient, or with family
• Direct quotes when clarifying unusual or critical statements

FORMATTING RULES:
• Write as flowing narrative paragraphs, NOT bullet points
• Do NOT use headers like "Chief Complaint:" or "Assessment:"
• Minimum 120 - 200 words per description (unless source document is very short)
• Preserve all clinically relevant detail including measurements, trends, time-sensitive events
• Quote verbatim when documenting critical statements or unusual findings
• If conflicting documentation exists, note both versions with sources
• Do NOT shorten or paraphrase unless content is repeated verbatim across documents
• Use "The claimant" or "The patient" instead of pronouns

EXAMPLE GOOD DESCRIPTION:
"The claimant presented to the emergency department at 14:30 with acute onset right-sided weakness and slurred speech beginning approximately 30 minutes prior. NIHSS score documented as 10. Physical examination revealed right upper extremity weakness graded 3/5, right facial droop, and expressive aphasia. Blood pressure 168/92, heart rate 88, respiratory rate 16, oxygen saturation 98% on room air. CT head without contrast performed at 15:05 showed no acute intracranial hemorrhage, no mass effect, and age-appropriate volume loss. CT brain perfusion demonstrated CBF (<30%) volume of 0 mL, perfusion (Tmax >6.0s) volume of 212 mL, and mismatch volume of 212 mL with undefined mismatch ratio. CTA head revealed right M1 segment middle cerebral artery filling defect measuring approximately 8mm, consistent with acute thrombus. Neurology was consulted at 15:20. Dr. Smith recommended immediate tPA administration. Alteplase 90mg IV was administered at 15:45 per stroke protocol. Patient showed partial symptom improvement by 16:30 with NIHSS decreasing to 6. Transfer arranged to comprehensive stroke center for possible mechanical thrombectomy."

EXAMPLE BAD DESCRIPTION (DO NOT DO THIS):
"CT scan performed. Results showed stroke. Patient treated with tPA." (TOO SHORT, lacks detail)

CRITICAL RULES:
• Extract ONLY information explicitly stated in the source documents
• Do NOT infer, assume, or add medical details not directly mentioned
• If multiple distinct events occurred (e.g., CT scan AND lab work AND medication), list them as SEPARATE events
• If same event mentioned in multiple documents, combine all information with all source pages
• If time not documented, use null
• Prioritize completeness over brevity - this is for legal review

**IMPORTANT:**
- Do NOT include a "sources" field in your JSON response
- Sources will be added automatically from metadata
- Only extract: date, time, event_type, facility, provider, title, description

Return JSON array of events:
[
  {{
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "event_type": "imaging",
    "facility": "...",
    "provider": "...",
    "title": "...",
    "description": "..."
  }}
]

Texts:
{context_text}

Extract events as detailed JSON array:
"""


 


# ============================================
# PASS 2: CLEANING, MERGING & FINALIZATION
# ============================================

PASS2_FIELDS = [
    'date',
    'time',
    'event_type',
    'facility',
    'provider',
    'title',
    'notes',    # NEW: 80-120 word summary
    'description_full',     # From Pass 1 (preserved)
    'sources',
    'merged_from',          # List of merged event indices
    'confidence_score',     # 0-1 merge confidence
    'editor_notes'          # Any flags or notes
]

# Merge detection settings
PASS2_MERGE_SAME_DATE_PROVIDER = True  # Merge events with same date+provider+facility
PASS2_MERGE_TIME_WINDOW = 60           # Minutes - events within this window may be merged
PASS2_DEDUPLICATE = True                # Remove exact duplicates

# CSV Export - Choose which fields to include
CSV_EXPORT_FIELDS = [
    'date',
    'time', 
    'event_type',
    'facility',
    'provider',
    'title',
    'notes',               
    'sources',
]


# Pass 2 System Prompt
PASS2_SYSTEM_PROMPT = """You are a senior medico-legal chronology editor. Your task is to create clean, accurate, litigation-ready chronology entries from raw medical record extractions.

You will receive events that have already been extracted from medical records. Your job is to clean, merge, and format them into professional chronology entries."""

# Pass 2 User Prompt
PASS2_USER_PROMPT = """You are reviewing medical events extracted from records for the claimant's case.

### EVENTS TO REVIEW:
{events_json}

### YOUR TASKS:

1. **IDENTIFY DUPLICATES & RELATED EVENTS**
   - Duplicates: Same event described multiple times (keep one, merge sources)
   - Related: Different parts of same encounter (e.g., "CT ordered" + "CT performed" + "CT results")
   - Merge related events that share: same date + same provider + same facility + related subject matter
   - DO NOT merge unrelated events even if same date (e.g., CT scan + blood draw = separate unless clearly same encounter)

2. **CREATE NOTES (80-120 words)**
   For each final event, write a concise medico-legal narrative using this structure:
   
   **Format:**
   - Start with time if available: "At [time], ..."
   - What happened: Brief statement of the event/encounter
   - Organize details into natural subsections when applicable:
     * History/Presentation: Chief complaint, symptoms
     * Findings: Exam findings, test results, measurements
     * Impression/Assessment: Diagnoses, clinical thinking
     * Plan/Action: Treatments, medications, follow-up
   
   **Style:**
   - Use natural flowing prose, not bullet points
   - Remove redundancy and filler
   - Keep medical terminology and specific values
   - Write as if continuing a chronological story
   - Reference prior events when relevant ("Following the CT scan from earlier...")
   
   **Example:**
   "At 14:30, the claimant underwent CT head without contrast per stroke protocol. Technique: Axial images acquired from skull base to vertex. Findings: No acute intracranial hemorrhage, mass effect, or midline shift identified. Age-appropriate volume loss noted. Impression: Negative for acute process. Results discussed with Dr. Chen at 15:00."

3. **PRESERVE CRITICAL INFORMATION**
   - All measurements, values, dosages
   - Provider names and actions
   - Timing and sequence
   - Any delays, contradictions, or deviations from standard care
   - Direct quotes when legally significant

4. **STANDARDIZE FIELDS**
   - event_type: Use lowercase (imaging, lab, medication, procedure, consultation, communication, other)
   - facility: Full official name
   - provider: "Dr. [Name], [credentials]" or "Nurse [Name]" format
   - time: Always HH:MM format or null

5. **FIX TIMING ISSUES**
   - If time in description conflicts with time field, use time from description
   - If no time documented anywhere, keep null

6. **OUTPUT FORMAT**
   Return a JSON array with these fields for EACH final event:
   
   {{
     "date": "YYYY-MM-DD",
     "time": "HH:MM" or null,
     "event_type": "imaging|lab|medication|procedure|consultation|communication|other",
     "facility": "Hospital Name",
     "provider": "Dr. Name, MD",
     "title": "Brief title of event",
     "notes": "80-120 word narrative following format above",
     "description_full": "Original Pass 1 description (preserve as-is)",
     "sources": [
       {{"source": "file.pdf", "pages": [1, 2]}}
     ],
     "merged_from": [0, 1],  // Indices of merged events, empty array if none
     "confidence_score": 0.95,  // 0-1, how confident merge decision is
     "editor_notes": ""  // Any flags or concerns
   }}

### MERGE DECISION RULES:

**DO MERGE if:**
- Same event mentioned in multiple documents (duplicate)
- Sequential steps of same procedure (order → performed → results)
- Same encounter, same provider, same date, related clinical matter
- Time gap < 1 hour and clearly related

**DO NOT MERGE if:**
- Different clinical matters (even if same date/provider)
- Different providers or facilities
- Time gap > 2 hours (unless explicitly stated as related)
- One is an order, another is completely different event

### IMPORTANT:
- Respond ONLY with valid JSON array
- Do NOT add explanatory text before or after JSON
- Maintain chronological order (date ascending, time ascending)
- Events with null time come AFTER events with times on same date

Return the cleaned, merged chronology as JSON array:"""








# ============================================
# RETRIEVAL SETTINGS
# ============================================


CHUNKS_PER_DATE = 100  # Max chunks to retrieve per date query

# Similarity metric: "L2" or "COSINE"
# L2 = Euclidean distance (default, fast with FAISS)
# COSINE = Cosine similarity (better for semantic matching, computed at query time)
SIMILARITY_METRIC = "COSINE"  # Change to "COSINE" to use cosine similarity


# ============================================
# ENABLE/DISABLE FEATURES
# ============================================
ENABLE_QUERY_ENHANCEMENT = False  # Not needed for date-based retrieval
ENABLE_DISTANCE_FILTERING = False
ENABLE_RERANKING = False




# ============================================
# WINDOWING SETTINGS (for large KB scaling)
# ============================================

# Maximum gap in chunk indices to consider same event
MAX_CHUNK_GAP_FOR_SAME_EVENT = 5

# Number of chunks to include as context on each side
LOCAL_CONTEXT_SPAN = 1

# Maximum characters per window sent to LLM
MAX_WINDOW_CHARS = 15000



