"""

QUESTIONNAIRE EXTRACTOR V9.11 - HARDCODED PAGE 24 FIX

Key Improvements:
- Fixed section name cleaning to remove "SECTION X:" prefixes
- HARDCODED STANDARD OF CARE and CAUSATION sections (page 24)
- Removes incorrectly extracted questions and inserts correct structure
- No newlines in context text (LLM-ready)
- All sub-questions have proper trigger, explanation fields

"""

import json
import re
import fitz
import base64
import requests
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from collections import defaultdict

load_dotenv()


class QuestionnaireExtractorV9:
    """
    ENHANCED Questionnaire Extractor V9.11
    
    Changes from V9.10:
    - FIXED: Hardcoded STANDARD OF CARE and CAUSATION sections (page 24)
    - Removes LLM misinterpretation (each option as separate question)
    - Inserts correct question structure with all options in response_options
    """

    def __init__(self, pdf_filename: str = "MASTER_COPY_Medical_Faculty_Questionnaire.pdf"):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        self.deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "pra-poc-gpt-4o")
        self.pdf_filename = pdf_filename

        if not self.endpoint or not self.api_key:
            raise ValueError("❌ Azure credentials missing in .env")

        self.all_questions = []
        print(f"\n✅ Azure OpenAI GPT-4o Initialized (v9.11 - HARDCODED PAGE 24)")
        print(f"   Features: Fixed section cleaning + Hardcoded SOC/Causation")
        print(f"   PDF: {pdf_filename}")






    # ==================== PDF EXTRACTION ====================
    
    def extract_from_pdf_file(self, pdf_path: str) -> List[tuple]:
        """Convert ALL PDF pages to base64 images"""
        try:
            print(f"\n📄 Reading PDF: {pdf_path}")
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            print(f"✅ PDF opened — total pages: {total_pages}")

            images_base64 = []
            for page_num in range(total_pages):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image_data = pix.tobytes("png")
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                images_base64.append((image_base64, page_num + 1))

                if (page_num + 1) % 10 == 0 or page_num + 1 == total_pages:
                    print(f"   ✅ Converted {page_num + 1}/{total_pages} pages")

            doc.close()
            return images_base64

        except Exception as e:
            print(f"❌ Error reading PDF: {e}")
            return []

    # ==================== SECTION NAME PROCESSING ====================
    
    def _clean_section_name(self, section_name: str) -> str:
        """
        Clean and UPPERCASE section name
        Removes "SECTION II:", "SECTION III:" prefixes
        """
        if not section_name:
            return section_name

        # Remove "SECTION II:", "SECTION III:", "SECTION IV:", etc.
        cleaned = re.sub(r'SECTION\s+[IVX]+:\s*', '', section_name, flags=re.IGNORECASE)
        
        # Remove ", Cont" / ", Contd" / "Continued"
        cleaned = re.sub(r',\s*(Cont|Contd|Continued|cont|contd|continued)(\s|$)', '', cleaned)
        cleaned = re.sub(r'\s*(Cont|Contd|Continued|cont|contd|continued)(\s|$)', '', cleaned)
        
        cleaned = cleaned.strip().upper()
        return cleaned

    # ==================== JSON ERROR FIXING ====================
    
    def _fix_json_string(self, json_str: str) -> Optional[str]:
        """Fix common JSON formatting issues"""
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass

        print(f"   🔧 Attempting to fix malformed JSON...")
        fixed = json_str

        fixed = re.sub(r"'([^']*)':", r'"\1":', fixed)
        fixed = re.sub(r'}\s*{', '},\n{', fixed)
        fixed = re.sub(r']\s*{', '],\n{', fixed)
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)

        parts = fixed.split('"')
        for i in range(1, len(parts), 2):
            parts[i] = parts[i].replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        fixed = '"'.join(parts)

        fixed = re.sub(r'([\]\}\""])\s+([{\[\"0-9tfn])', r'\1,\2', fixed)

        try:
            json.loads(fixed)
            print(f"   ✅ JSON fixed successfully")
            return fixed
        except json.JSONDecodeError as e:
            print(f"   ⚠️ Could not fix JSON: {e}")
            return None

    # ==================== CONDITIONAL DISPLAY LOGIC ====================
    
    def _build_conditional_display(self, question: Dict) -> Optional[Dict]:
        """
        Build conditional_display from sub_question_trigger
        """
        trigger = question.get("sub_question_trigger", "").strip()
        if not trigger:
            return None

        q_id = question.get("question_id", "")
        if "." not in q_id:
            return None

        parent_id = q_id.split(".")[0]
        response_values = []

        trigger_lower = trigger.lower()

        if "yes" in trigger_lower and "unclear" in trigger_lower:
            response_values = ["Yes", "Unclear"]
        elif "yes" in trigger_lower and "no" in trigger_lower:
            response_values = ["Yes", "No"]
        elif "no" in trigger_lower and "unclear" in trigger_lower:
            response_values = ["No", "Unclear"]
        elif "yes" in trigger_lower:
            response_values = ["Yes"]
        elif "no" in trigger_lower:
            response_values = ["No"]
        elif "unclear" in trigger_lower:
            response_values = ["Unclear"]
        else:
            response_values = ["Yes", "Unclear"]

        if response_values:
            return {
                "parent_question_id": parent_id,
                "parent_response_values": response_values
            }

        return None

    # ==================== PAGE-SPECIFIC FIXES ====================
    
    def _apply_page_fixes(self, questions_data: List[Dict]) -> List[Dict]:
        """
        Apply targeted fixes based on SECTION NAMES
        HARDCODED fix for STANDARD OF CARE and CAUSATION (page 24)
        """
        if not questions_data:
            return questions_data
        
        # ============ FIX 1: DEGREE OF INJURY - Rating Scale ============
        injury_texts = [
            "1. No physical injury occurred; there were only emotional injuries such as fright, a claim of wrongful confinement to a mental hospital, etc.",
            "2. Very slight, if any physical injury at all; lacerations; contusions; minor scars. Limited medical treatment required with no delay in recovery.",
            "3. Relatively minor injuries where recovery is complete but delayed: infections; missed fractures that heal with acceptable results; delay in diagnosing appendicitis without complications.",
            "4. Serious temporary injuries where there was a delay in recovery with complication: temporary colostomy; temporary ventilator support; internal injury like bowel perforation with recovery, etc.",
            "5. Injuries that are permanent in nature but non-disabling and do not generally compromise the basic ADLs: removal of bowel due to circulatory compromise; loss of one ovary or one testicle; loss of fingers or toes, etc. OR a neurological injury resulting in slight disability, possibly not able to carry out all previous activities, but able to look after own affairs without assistance.",
            "6. Injuries that are permanent and affect ADLs: deafness; loss of one limb or one eye; loss of one kidney or one lung; permanent foot or wrist drop; failure to diagnose cancer without evidence of spread, etc. OR a neurological injury with moderate disability; requires some help, but able to walk without assistance.",
            "7. Severe permanent injury: loss of two legs as opposed to one; paraplegia; severe and visible disfigurement; total blindness; permanent renal failure; permanent colostomy; aseptic necrosis of a femoral head, etc. OR a neurological injury requiring assistance to walk and attend to bodily needs.",
            "8. Most significant injuries where patient survives but has fatal prognosis or requires lifelong care: severe brain damage; CP; quadriplegia; major burns; failure to diagnose cancer with evidence of spread and a poor prognosis, etc. OR a neurological injury resulting in being bedridden, incontinent and requiring constant nursing care and attention.",
            "9. Death of the patient"
        ]
        
        # Apply DEGREE OF INJURY fix
        for q in questions_data:
            section = q.get("section_name", "")
            
            if (section == "DEGREE OF INJURY" and 
                (("rating" in q.get("question_type", "").lower()) or
                 (len(q.get("response_options", [])) == 9))):
                q["question_type"] = "rating_scale_1_to_9"
                q["response_options"] = injury_texts.copy()
                print(f"   🔧 Applied DEGREE OF INJURY fix for Q{q.get('question_id')}")
        
        # ============ FIX 2: HARDCODE STANDARD OF CARE & CAUSATION ============
        
        # Detect if we have SOC or Causation sections (page 24)
        has_soc = any(q.get("section_name") == "STANDARD OF CARE" for q in questions_data)
        has_causation = any(q.get("section_name") == "CAUSATION" for q in questions_data)
        
        if has_soc or has_causation:
            print(f"   🔧 Detected page 24 - Applying hardcoded STANDARD OF CARE & CAUSATION fix")
            
            # Get page number from first question
            page_num = questions_data[0].get("page_number", 24) if questions_data else 24
            
            # REMOVE all SOC and Causation questions (they're wrongly extracted)
            filtered_questions = [
                q for q in questions_data 
                if q.get("section_name") not in ["STANDARD OF CARE", "CAUSATION"]
            ]
            
            # Context text (single paragraph, no newlines)
            soc_context = "Note: When responding to the below questions, Degree of Injury (DOI) does not imply the Standard of Care or Causation. It's possible for the Standard of Care to be of high quality and the Causation to be very good, and yet the Degree of Injury could be severe, including major permanent harm or even death. Conversely, even when the Standard of Care and Causation are significantly lacking, the Degree of Injury might be minimal. This distinction highlights that the severity of an injury does not directly correlate with the quality of care or show a causal relationship. The SOC is the care, skill, and treatment recognized as pertinent by similar, reasonably prudent health care providers. It is determined in the context of all relevant circumstances and available information. SOC serves as the benchmark in assessing the appropriateness of the provider's actions, including both direct patient care and in the supervision of or formal collaboration with other providers. Conceptually, the standard of care is a continuum, ranging from that which is minimally required to that which is exceptional. Accordingly, to meet the standard, a provider's care, at the very least, must be considered acceptable; otherwise, it is negligent care. The standard in any given situation is influenced by several factors, including but not limited to statutes, regulations, clinical guidelines, research, and facility policies and procedures. Based on your thorough assessment, provide a final rating of the standard of care. 1. SELECT ONE"
            
            causation_context = "Causation reflects whether a provider's actions (or inactions) caused or contributed to an injury. Causation is not dependent on whether the Standard of Care was met. For example, a patient presents with 3 days of left-sided weakness and the physician fails to diagnose cerebrovascular accident, but the onset of symptoms is further out than any emergent treatment window. Therefore, the physician has not met the SOC for missing the diagnosis of CVA, but the defendant's actions did not cause or contribute to the injury because thrombolytics and thrombectomy are no longer indicated by the time the patient presents. Thus, a timely diagnosis or any treatment rendered would not have changed the patient outcome. Based on your thorough assessment, please indicate your final opinion as to whether the defendant's care caused or contributed to the patient's injury. 1. SELECT ONE"
            
            # HARDCODED STANDARD OF CARE QUESTIONS
            soc_q1 = {
                "section_name": "STANDARD OF CARE",
                "question_id": "1",
                "parent_question_id": "",
                "main_question": soc_context,
                "question_type": "rating_scale_1_to_5",
                "response_options": [
                    "1. The defendant's actions (or inactions) deviated from acceptable standards to an unquestionable degree.",
                    "2. The defendant's actions (or inactions) differed from that which most members of the medical community would have utilized.",
                    "3. Standard of Care cannot be determined due to the need for additional information.",
                    "4. The defendant's actions (or inactions) would be viewed as acceptable by most members of the medical community.",
                    "5. The defendant's actions (or inactions) were unquestionably consistent with accepted medical practice."
                ],
                "is_sub_question": False,
                "sub_question_trigger": "",
                "requires_explanation": False,
                "explanation_trigger": "",
                "explanation_type": "",
                "page_number": page_num,
                "indentation_level": 0,
                "conditional_display": None
            }
            
            soc_q2 = {
                "section_name": "STANDARD OF CARE",
                "question_id": "2",             # ✅ CHANGED
                "parent_question_id": "",       # ✅ CHANGED
                "main_question": "If faced with the same circumstances as this defendant, what would most providers have done?",
                "question_type": "textarea",
                "response_options": [],
                "is_sub_question": False,       # ✅ CHANGED
                "sub_question_trigger": "",     # ✅ CHANGED
                "requires_explanation": False,  # ✅ CHANGED
                "explanation_trigger": "",      # ✅ CHANGED
                "explanation_type": "",
                "page_number": page_num,
                "indentation_level": 0,         # ✅ CHANGED
                "conditional_display": None     # ✅ CHANGED
            }

            
            # HARDCODED CAUSATION QUESTIONS
            causation_q1 = {
                "section_name": "CAUSATION",
                "question_id": "1",
                "parent_question_id": "",
                "main_question": causation_context,
                "question_type": "rating_scale_1_to_5",
                "response_options": [
                    "1. The defendant's actions (or inactions) clearly caused and were the sole source of the injuries.",
                    "2. The defendant's actions (or inactions) were not the sole cause but did contribute to the injuries.",
                    "3. Causation cannot be determined due to the need for additional information.",
                    "4. The defendant's actions (or inactions) were not the primary cause but may have contributed to the injuries.",
                    "5. The injuries were not caused by any of the actions (or inactions) of the defendant."
                ],
                "is_sub_question": False,
                "sub_question_trigger": "",
                "requires_explanation": False,
                "explanation_trigger": "",
                "explanation_type": "",
                "page_number": page_num,
                "indentation_level": 0,
                "conditional_display": None
            }
            
            # Add hardcoded questions back
            filtered_questions.extend([soc_q1, soc_q2, causation_q1])
            
            print(f"   ✅ Replaced STANDARD OF CARE & CAUSATION with hardcoded structure")
            
            return filtered_questions
        
        return questions_data

    # ==================== COMPREHENSIVE EXTRACTION PROMPT ====================
    
    def _extract_page_json_comprehensive(self, image_base64: str, actual_page_num: int) -> Dict[str, Any]:
        """
        Extract COMPREHENSIVE questions with ALL details
        Includes retry logic with validation for incomplete extractions
        """

        prompt = f"""You are an expert medical questionnaire analyzer. Extract EVERY single question from this page.

    CRITICAL: This is PDF page {actual_page_num}. All questions extracted must have "page_number": {actual_page_num}.

    Return ONLY valid JSON object. Start with {{ and end with }}.

    {{
    "page_number": {actual_page_num},
    "questions": [
        {{
        "question_id": "1",
        "section_name": "CLAIM INFO",
        "main_question": "MagMutual File #",
        "question_type": "textarea",
        "response_options": [],
        "is_sub_question": false,
        "sub_question_trigger": "",
        "page_number": {actual_page_num},
        "indentation_level": 0
        }}
    ]
    }}

    EXTRACTION RULES - MUST FOLLOW:

    1. PAGE NUMBER ASSIGNMENT:
    - ALL questions on THIS image are from page {actual_page_num}
    - Set "page_number": {actual_page_num} for EVERY question extracted
    - DO NOT use any other page number
    - This is critical for proper form automation

    2. EXTRACT ALL QUESTIONS - COMPLETE TEXT REQUIRED:
    - Do NOT skip ANY questions on the page
    - Include COMPLETE question text from PDF - do not truncate
    - Include questions in EVERY section
    - For questions with conditional text, include full text in main_question

    3. RESPONSE OPTIONS:
    - Extract EXACTLY as they appear on page
    - Yes | No | No timeline provided → ["Yes", "No", "No timeline provided"]
    - Degree of injury alleged (1-9) → list all options visible
    - Checkboxes → list all checkbox options visible
    - Custom lists → capture ALL options shown

    4. QUESTION TYPES (flexible):
    - "textarea" - text input/explain fields
    - "checkbox_group" - multiple checkboxes
    - "custom_options" - custom response list
    - "rating_scale_1_to_9" - 1-9 rating scales
    - "yes_no_unclear_not_applicable"
    - "yes_no_unclear"
    - "yes_no"

    5. SUB-QUESTIONS AND TRIGGERS - CRITICAL - MUST EXTRACT TRIGGER TEXT:
    - ALL indented/nested questions are sub-questions
    - MUST extract sub_question_trigger text EXACTLY AS SHOWN on the PDF
    - Common trigger patterns to look for:
        * "If Yes or Unclear" → set sub_question_trigger: "If Yes or Unclear"
        * "If Yes" → set sub_question_trigger: "If Yes"
        * "If No" → set sub_question_trigger: "If No"
        * "If Yes, explain" → set sub_question_trigger: "If Yes"
        * "If Yes or Unclear, explain" → set sub_question_trigger: "If Yes or Unclear"
    - Look for trigger text near the sub-question or in parent question
    - NEVER leave sub_question_trigger empty for sub-questions - always extract it
    - "indentation_level": 1 for first level, 2 for deeper nesting
    - Set "is_sub_question": true for all sub-questions

    6. COMPLETE QUESTION NAMES:
    - Extract the COMPLETE question text as shown on the PDF
    - Do not truncate or shorten
    - Include ALL parts including conditional statements

    7. SECTION NAMES:
    - ALL UPPERCASE
    - Remove ", Cont" / ", Contd"
    - Write section name ONE TIME per section

    8. QUESTION IDS:
    - Main: 1, 2, 3, 4, 5, ...
    - First sub: 1.1, 2.1, 3.1, ...
    - Second sub: 1.1.1, 2.1.1, ...
    - Nested: Increment last number for deeper levels

    9. JSON REQUIREMENTS:
    - NO trailing commas
    - ALL strings use double quotes
    - NO unescaped newlines in option strings
    - Proper comma between all objects
    - Return ONLY valid JSON (no markdown)

    10. COMPLETENESS:
        - Check page carefully for all sections
        - Verify no questions are skipped
        - Capture all sub-questions visible with their triggers
        - Include text input fields as textareas

    Return ONLY the JSON object with "page_number": {actual_page_num} and "questions" array."""

        url = f"{self.endpoint}openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_tokens": 16000,      
            "temperature": 0.0,       
                           
        }

        # Retry logic with validation
        max_retries = 2  # Total 3 attempts (1 original + 2 retries)
        
        for attempt in range(max_retries + 1):
            try:
                attempt_msg = f" (retry {attempt})" if attempt > 0 else ""
                print(f"   🔄 Extracting ALL questions from page {actual_page_num}...{attempt_msg}")
                
                # Make API request with reasonable timeout (120 seconds = 2 minutes)
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                response.raise_for_status()

                result = response.json()
                if result.get('choices') and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    json_match = re.search(r'\{[\s\S]*\}', content)

                    if json_match:
                        json_str = json_match.group()

                        try:
                            parsed = json.loads(json_str)
                            # Force correct page number
                            parsed['page_number'] = actual_page_num
                            for q in parsed.get('questions', []):
                                q['page_number'] = actual_page_num
                            
                            # VALIDATE EXTRACTION
                            if self._validate_page_extraction(parsed.get('questions', []), actual_page_num):
                                return parsed
                            else:
                                # Validation failed - retry if attempts remaining
                                if attempt < max_retries:
                                    print(f"   🔄 Validation failed, retrying page {actual_page_num}...")
                                    continue
                                else:
                                    print(f"   ⚠️ Using incomplete extraction for page {actual_page_num}")
                                    return parsed

                        except json.JSONDecodeError as e:
                            print(f"   ⚠️ JSON parse error on page {actual_page_num}: {e}")
                            fixed_json = self._fix_json_string(json_str)

                            if fixed_json:
                                try:
                                    parsed = json.loads(fixed_json)
                                    parsed['page_number'] = actual_page_num
                                    for q in parsed.get('questions', []):
                                        q['page_number'] = actual_page_num
                                    print(f"   ✅ JSON fixed and parsed")
                                    
                                    # Validate fixed JSON
                                    if self._validate_page_extraction(parsed.get('questions', []), actual_page_num):
                                        return parsed
                                    elif attempt < max_retries:
                                        continue
                                    else:
                                        return parsed
                                        
                                except json.JSONDecodeError as e2:
                                    print(f"   ❌ Could not fix JSON after attempt {attempt+1}")
                                    if attempt < max_retries:
                                        continue
                                    else:
                                        return {"page_number": actual_page_num, "questions": []}
                            else:
                                if attempt < max_retries:
                                    continue
                                else:
                                    return {"page_number": actual_page_num, "questions": []}

                # No valid response
                if attempt < max_retries:
                    print(f"   ⚠️ No valid response for page {actual_page_num}, retrying...")
                    continue
                else:
                    return {"page_number": actual_page_num, "questions": []}

            except requests.exceptions.Timeout:
                print(f"   ❌ Timeout on page {actual_page_num} (attempt {attempt+1}/{max_retries+1})")
                if attempt < max_retries:
                    continue
                else:
                    return {"page_number": actual_page_num, "questions": []}
                    
            except Exception as e:
                print(f"   ❌ API Error on page {actual_page_num} (attempt {attempt+1}): {e}")
                if attempt < max_retries:
                    continue
                else:
                    return {"page_number": actual_page_num, "questions": []}
        
        # Fallback (should never reach here)
        return {"page_number": actual_page_num, "questions": []}


    # Don't forget to add the validation method to your class:
    def _validate_page_extraction(self, questions: List[Dict], page_num: int) -> bool:
        """
        Validate if extraction seems complete based on expected question count
        Returns True if acceptable, False if needs retry
        """
        # Expected question counts per page (from your baseline)
        EXPECTED_COUNTS = {
            1: 15, 2: 6, 3: 4, 4: 18, 5: 18, 6: 10, 7: 18, 8: 18, 9: 13, 10: 12,
            11: 18, 12: 18, 13: 13, 14: 13, 15: 18, 16: 18, 17: 13, 18: 9, 
            19: 12, 20: 12, 21: 16, 22: 17, 23: 11, 24: 3, 25: 7
        }
        
        expected = EXPECTED_COUNTS.get(page_num)
        if not expected:
            return True  # No baseline, accept as-is
        
        actual = len(questions)
        tolerance = 0.05  # Allow 5% variance
        min_acceptable = int(expected * (1 - tolerance))
        
        if actual < min_acceptable:
            print(f"   ⚠️ Page {page_num}: Expected ~{expected} questions, got {actual}")
            return False
        
        return True

    # ==================== QUESTION PROCESSING ====================
    
    def _build_trigger_string_from_values(self, response_values: List[str]) -> str:
        """Build proper trigger string from parent_response_values"""
        if not response_values:
            return "if yes or unclear"

        sorted_values = sorted(response_values, key=lambda x: (x != "Yes", x != "No", x != "Unclear", x))

        if len(sorted_values) == 1:
            return f"if {sorted_values[0].lower()}"
        elif len(sorted_values) == 2:
            return f"if {sorted_values[0].lower()} or {sorted_values[1].lower()}"
        else:
            return "if " + ", ".join(v.lower() for v in sorted_values[:-1]) + f" or {sorted_values[-1].lower()}"

    def _infer_sub_question_trigger(self, question: Dict, parent_question: Optional[Dict]) -> str:
        """Infer trigger for sub-questions based on parent's response options"""
        if not question.get("is_sub_question", False):
            return ""

        if not parent_question:
            return "if yes or unclear"

        parent_options = parent_question.get("response_options", [])
        has_yes = "Yes" in parent_options
        has_no = "No" in parent_options
        has_unclear = "Unclear" in parent_options

        if has_yes and has_unclear:
            return "if yes or unclear"
        elif has_yes and not has_unclear:
            return "if yes"
        elif has_no and has_unclear and not has_yes:
            return "if no or unclear"
        elif has_unclear and not has_yes and not has_no:
            return "if unclear"
        else:
            return "if yes or unclear"

    def _process_questions_comprehensive(self, questions_data: List[Dict], current_page: int) -> List[Dict]:
        """Process questions with comprehensive parent ID assignment"""
        question_map = {}
        for q in questions_data:
            q["page_number"] = current_page
            q["section_name"] = self._clean_section_name(q.get("section_name", ""))
            question_map[q.get("question_id", "")] = q

        for q in questions_data:
            q_id = q.get("question_id", "")

            if "." in q_id:
                parts = q_id.split(".")
                parent_id = parts[0]
                q["parent_question_id"] = parent_id
                q["is_sub_question"] = True

                parent_q = question_map.get(parent_id)
                trigger = self._infer_sub_question_trigger(q, parent_q)
                q["sub_question_trigger"] = trigger

                conditional = self._build_conditional_display(q)
                q["conditional_display"] = conditional

                q["requires_explanation"] = True
                q["explanation_trigger"] = trigger
                q["explanation_type"] = "textarea"

            else:
                q["parent_question_id"] = ""
                q["is_sub_question"] = False
                q["sub_question_trigger"] = ""
                q["conditional_display"] = None

                if "requires_explanation" not in q:
                    q["requires_explanation"] = False
                if "explanation_trigger" not in q:
                    q["explanation_trigger"] = ""
                if "explanation_type" not in q:
                    q["explanation_type"] = ""

        return questions_data

    def _flatten_questions(self, questions_data: List[Dict]) -> List[Dict]:
        """Ensure all required fields exist"""
        flattened = []
        for q in questions_data:
            flattened.append({
                "section_name": q.get("section_name", ""),
                "question_id": q.get("question_id", ""),
                "parent_question_id": q.get("parent_question_id", ""),
                "main_question": q.get("main_question", ""),
                "question_type": q.get("question_type", "textarea"),
                "response_options": q.get("response_options", []),
                "is_sub_question": q.get("is_sub_question", False),
                "sub_question_trigger": q.get("sub_question_trigger", ""),
                "requires_explanation": q.get("requires_explanation", False),
                "explanation_trigger": q.get("explanation_trigger", ""),
                "explanation_type": q.get("explanation_type", ""),
                "page_number": q.get("page_number", 1),
                "indentation_level": q.get("indentation_level", 0),
                "conditional_display": q.get("conditional_display", None)
            })
        return flattened

    # ==================== MAIN EXTRACTION ====================
    
    def extract_from_pdf(self) -> List[Dict]:
        """Extract comprehensive questions from entire PDF"""
        self.all_questions = []

        print("\n" + "=" * 80)
        print("QUESTIONNAIRE EXTRACTION V9.11 - HARDCODED PAGE 24 FIX")
        print("Features: Fixed section cleaning + Hardcoded SOC/Causation")
        print("=" * 80)

        images_base64 = self.extract_from_pdf_file(self.pdf_filename)
        if not images_base64:
            print("❌ Could not extract images from PDF")
            return []

        total_images = len(images_base64)

        for idx, (image_base64, seq_page_num) in enumerate(images_base64):
            print(f"\n📖 Processing page {seq_page_num}/{total_images}...")
            page_data = self._extract_page_json_comprehensive(image_base64, seq_page_num)

            if page_data.get("questions"):
                questions = page_data["questions"]

                # Process: clean sections, assign parent IDs
                questions = self._process_questions_comprehensive(questions, seq_page_num)

                # Apply section-based fixes (includes hardcoded page 24)
                questions = self._apply_page_fixes(questions)

                # Flatten & ensure all fields
                flattened = self._flatten_questions(questions)
                self.all_questions.extend(flattened)

                print(f"   ✅ Extracted {len(flattened)} questions from page {seq_page_num}")

                for q in flattened[:3]:
                    opts = f" ({len(q['response_options'])} options)" if q['response_options'] else ""
                    trigger = f" [Trigger: {q['sub_question_trigger']}]" if q['sub_question_trigger'] else ""
                    print(f"     Q{q['question_id']} [{q['section_name']}]: {q['main_question'][:50]}{opts}{trigger}")
            else:
                print(f"   ⚠️ No questions found on page {seq_page_num}")

        print(f"\n✅ Extraction complete!")
        print(f"📊 Total questions: {len(self.all_questions)}")

        return self.all_questions

    # ==================== SAVE & SUMMARY ====================
    
    def save_to_json(self, output_filename: str = "questionnaire_v9_11_final.json") -> str:
        """Save extraction to JSON"""
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(self.all_questions, f, indent=4, ensure_ascii=False)

            print(f"\n💾 JSON saved to: {output_filename}")
            print(f"📊 Total questions: {len(self.all_questions)}")
            return output_filename

        except Exception as e:
            print(f"❌ Error saving: {e}")
            return None

    def print_summary(self):
        """Print detailed summary"""
        print("\n" + "=" * 80)
        print("EXTRACTION SUMMARY - V9.11 HARDCODED PAGE 24 FIX")
        print("=" * 80)

        main_qs = [q for q in self.all_questions if not q.get("is_sub_question")]
        sub_qs = [q for q in self.all_questions if q.get("is_sub_question")]

        print(f"\n📊 QUESTIONS:")
        print(f"   Total: {len(self.all_questions)}")
        print(f"   Main Questions: {len(main_qs)}")
        print(f"   Sub-Questions: {len(sub_qs)}")

        sub_qs_with_triggers = [q for q in sub_qs if q.get("sub_question_trigger")]
        sub_qs_with_explanations = [q for q in sub_qs if q.get("requires_explanation")]

        print(f"   Sub-Questions with Triggers: {len(sub_qs_with_triggers)}/{len(sub_qs)}")
        print(f"   Sub-Questions with Explanations: {len(sub_qs_with_explanations)}/{len(sub_qs)}")

        types = defaultdict(int)
        for q in self.all_questions:
            types[q.get("question_type", "unknown")] += 1

        print(f"\n   By Type:")
        for qtype, count in sorted(types.items()):
            print(f"     {qtype}: {count}")

        pages = defaultdict(int)
        for q in self.all_questions:
            pages[q.get("page_number", 0)] += 1

        print(f"\n📄 BY PAGE:")
        for page_num in sorted(pages.keys()):
            print(f"   Page {page_num}: {pages[page_num]} questions")

        print(f"\n📋 SECTIONS:")
        sections = set()
        for q in self.all_questions:
            section = q.get("section_name", "")
            if section:
                sections.add(section)

        for section in sorted(sections):
            count = sum(1 for q in self.all_questions if q.get("section_name") == section)
            print(f"   {section}: {count} questions")

        conditional_count = sum(1 for q in self.all_questions if q.get("conditional_display"))
        print(f"\n🔗 CONDITIONAL QUESTIONS: {conditional_count}")


# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    try:
        print("🚀 Starting Enhanced Extraction (V9.11 - HARDCODED PAGE 24)...\n")

        PDF_NAME = "MASTER_COPY_Medical_Faculty_Questionnaire.pdf"
        extractor = QuestionnaireExtractorV9(pdf_filename=PDF_NAME)

        questions = extractor.extract_from_pdf()

        if questions:
            extractor.save_to_json()
            extractor.print_summary()

            print("\n✅ Extraction complete!")
            print(f"📁 Output file: questionnaire_v9_11_final.json")
        else:
            print("\n⚠️ No questions extracted")

    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
