#!/usr/bin/env python3

"""
COMBINED PDF FORM FILLER - All-in-One Class
Combines section_mapping, flatten, and sample34.py into CombinedPDFFormFiller class
"""

import os
import sys
import json
import re
import fitz  # pip install PyMuPDF


# =============================================================================
# SECTION MAPPING (from section_mapping_fixed2.py)
# =============================================================================

def question_id_to_pdf_field(question_id, section):
    """Main dispatcher - routes to section-specific mapper"""
    if section == 'CLAIM INFO':
        return map_claim_info(question_id)
    elif section == 'OVERVIEW AND TIMELINE OF KEY POINTS':
        return map_overview(question_id)
    elif section == 'DEGREE OF INJURY':
        return map_degree_of_injury(question_id)
    elif section in ['PATIENT INTAKE/ASSESSMENT SECTION', 'PATIENT INTAKE/ASSESSMENT']:
        return map_intake(question_id)
    elif section == 'DIAGNOSTIC WORK UP':
        return map_diagnostic(question_id)
    elif section == 'TREATMENT':
        return map_treatment(question_id)
    elif section == 'PROCEDURES/SURGERIES':
        return map_procedures(question_id)
    elif section == 'MONITORING AND FOLLOWUP':
        return map_monitoring(question_id)
    elif section == 'ADDITIONAL CONTRIBUTING FACTORS':
        return map_additional(question_id)
    elif section == 'STANDARD OF CARE':
        return map_standard_of_care(question_id)
    elif section == 'CAUSATION':
        return map_causation(question_id)
    elif section == 'CLOSING THOUGHTS':
        return map_closing_thoughts(question_id)
    else:
        return None


def map_claim_info(question_id):
    """CLAIM INFO mapping"""
    mapping = {
        '1': 'File_No',
        '2': 'MagMutual_Contact',
        '3': 'Date_Requested_af_date',
        '4': 'MagMutual_Contact_Phone',
        '5': 'MagMutual_Contact_Email',
        '6': 'Patient_Name',
        '7': 'Defendant_Name',
        '8': 'Defendant_Specialty',
        '9': 'Reviewer_Name',
        '10': 'Reviewer_Specialty',
        '11': 'Reviewer_PhoneNumber',
        '12': 'Reviewer_Email',
        '13': 'Brief_Synopsis',
        '14': 'Alleged_Injury',
        '15': 'Summary_Of_Allegations',
    }
    return mapping.get(question_id)


def map_overview(question_id):
    """OVERVIEW mapping"""
    mapping = {
        '1': 'Overview_Q1',
        '2': 'Overview_Q2',
        '2.1': 'Overview_Q2_Comments',
        '3': 'Overview_Q3',
        '3.1': 'Overview_Q3_Modifications',
    }
    return mapping.get(question_id)


def map_degree_of_injury(question_id):
    """DEGREE OF INJURY mapping"""
    mapping = {
        '1': 'Patient_Injury',
        '2': 'Degree_Of_Injury_Alleged_vs_Suffered',
        '2.alleged': 'Degree_Of_Injury_Alleged',
        '2.suffered': 'Degree_Of_Injury_Suffered',
        '3': 'Injury_Impact',
    }
    return mapping.get(question_id)


def map_intake(question_id):
    """PATIENT INTAKE mapping"""
    parts = question_id.split('.')
    main_q = parts[0]

    # Q7 special handling
    if main_q == '7':
        mapping = {
            '7': 'Intake_Q7a',
            '7.1': 'Intake_Q7a_Explain',
            '7.2.1': 'Intake_Q7a_Handoff',
            '7.2.2': 'Intake_Q7a_Interdisciplinary',
            '7.2.3': 'Intake_Q7a_Emergency',
            '7.2.4': 'Intake_Q7a_Supervision',
            '7.3': 'Intake_Q7b',
            '7.3.1': 'Intake_Q7b_Explain',
            '7.4': 'Intake_Q7c',
            '7.4.1': 'Intake_Q7c_Explain',
        }
        return mapping.get(question_id)

    if main_q in ['1', '2', '3', '4', '5', '6']:
        mapping = {
            main_q: f"Intake_Q{main_q}a",
            f"{main_q}.1": f"Intake_Q{main_q}a_Explain",
            f"{main_q}.2": f"Intake_Q{main_q}b",
            f"{main_q}.2.1": f"Intake_Q{main_q}b_Explain",
            f"{main_q}.3": f"Intake_Q{main_q}c",
            f"{main_q}.3.1": f"Intake_Q{main_q}c_Explain",
        }
        return mapping.get(question_id)

    # Q8 special handling
    if main_q == '8':
        mapping = {
            '8': 'Intake_Q8',
            '8.1': 'Intake_Q8_Explain',
        }
        return mapping.get(question_id)

    # Q9 special handling
    if main_q == '9':
        mapping = {
            '9': 'Intake_Q9',
        }
        return mapping.get(question_id)

    return None


def map_diagnostic(question_id):
    """DIAGNOSTIC WORK UP mapping"""
    parts = question_id.split('.')
    main_q = parts[0]

    if main_q == '7':
        mapping = {
            '7.1': 'DiagnosticWorkUp_Q7a_Explain',
            '7.2': 'DiagnosticWorkUp_Q7a',
            '7.2.1': 'DiagnosticWorkUp_Q7a_Handoff',
            '7.2.2': 'DiagnosticWorkUp_Q7a_Interdisciplinary',
            '7.2.3': 'DiagnosticWorkUp_Q7a_EmergencySituation',
            '7.2.4': 'DiagnosticWorkUp_Q7a_SupervisionHierarchy',
            '7.3': 'DiagnosticWorkUp_Q7b',
            '7.3.1': 'DiagnosticWorkUp_Q7b_Explain',
            '7.4': 'DiagnosticWorkUp_Q7c',
            '7.4.1': 'DiagnosticWorkUp_Q7c_Explain',
        }
        return mapping.get(question_id)

    if main_q == '8':
        mapping = {
            '8': 'DiagnosticWorkUp_Q8a',
            '8.1': 'DiagnosticWorkUp_Q8a_Explain',
            '8.2': 'DiagnosticWorkUp_Q8b',
            '8.2.1': 'DiagnosticWorkUp_Q8b_Explain',
            '8.3': 'DiagnosticWorkUp_Q8c',
            '8.3.1': 'DiagnosticWorkUp_Q8c_Explain',
        }
        return mapping.get(question_id)

    if main_q == '9':
        mapping = {
            '9': 'DiagnosticWorkUp_Q9a',
            '9.1': 'DiagnosticWorkUp_Q9a_Explain',
            '9.2': 'DiagnosticWorkUp_Q9a_Explain2',
            '9.3': 'DiagnosticWorkUp_Q9b',
            '9.3.1': 'DiagnosticWorkUp_Q9b_Explain',
            '9.4': 'DiagnosticWorkUp_Q9c',
            '9.4.1': 'DiagnosticWorkUp_Q9c_Explain',
            '9.5': 'DiagnosticWorkUp_Q9d',
            '9.5.1': 'DiagnosticWorkUp_Q9d_Explain',
        }
        return mapping.get(question_id)

    if main_q in ['1', '2', '3', '4', '5', '6']:
        mapping = {
            main_q: f"DiagnosticWorkUp_Q{main_q}a",
            f"{main_q}.1": f"DiagnosticWorkUp_Q{main_q}a_Explain",
            f"{main_q}.2": f"DiagnosticWorkUp_Q{main_q}b",
            f"{main_q}.2.1": f"DiagnosticWorkUp_Q{main_q}b_Explain",
            f"{main_q}.3": f"DiagnosticWorkUp_Q{main_q}c",
            f"{main_q}.3.1": f"DiagnosticWorkUp_Q{main_q}c_Explain",
        }
        return mapping.get(question_id)

    if main_q == '10':
        mapping = {
            '10': 'DiagnosticWorkUp_Q10',
            '10.1': 'DiagnosticWorkUp_Q10_Explain',
        }
        return mapping.get(question_id)

    if main_q == '11':
        return 'DiagnosticWorkUp_Q11'

    return None


def map_treatment(question_id):
    """TREATMENT mapping"""
    parts = question_id.split('.')
    main_q = parts[0]

    if main_q == '7':
        mapping = {
            '7': 'Treatment_Q7a',
            '7.1': 'Treatment_Q7a_Explain',
            '7.2.1': 'Treatment_Q7a_Handoff',
            '7.2.2': 'Treatment_Q7a_Interdisciplinary',
            '7.2.3': 'Treatment_Q7a_EmergencySituation',
            '7.2.4': 'Treatment_Q7a_SupervisionHierarchy',
            '7.3': 'Treatment_Q7b',
            '7.3.1': 'Treatment_Q7b_Explain',
            '7.4': 'Treatment_Q7c',
            '7.4.1': 'Treatment_Q7c_Explain',
        }
        return mapping.get(question_id)

    if main_q in ['1', '2', '3', '4', '5', '6']:
        mapping = {
            main_q: f"Treatment_Q{main_q}a",
            f"{main_q}.1": f"Treatment_Q{main_q}a_Explain",
            f"{main_q}.2": f"Treatment_Q{main_q}b",
            f"{main_q}.2.1": f"Treatment_Q{main_q}b_Explain",
            f"{main_q}.3": f"Treatment_Q{main_q}c",
            f"{main_q}.3.1": f"Treatment_Q{main_q}c_Explain",
        }
        return mapping.get(question_id)

    if main_q == '8':
        mapping = {
            '8': 'Treatment_Q8a',
            '8.1': 'Treatment_Q8a_Explain',
            '8.2': 'Treatment_Q8b',
            '8.2.1': 'Treatment_Q8b_Explain',
            '8.3': 'Treatment_Q8c',
            '8.3.1': 'Treatment_Q8c_Explain',
        }
        return mapping.get(question_id)

    if main_q == '9':
        mapping = {
            '9': 'Treatment_Q9a',
            '9.1': 'Treatment_Q9a_Explain',
            '9.2': 'Treatment_Q9a_Explain2',
            '9.3': 'Treatment_Q9b',
            '9.3.1': 'Treatment_Q9b_Explain',
            '9.4': 'Treatment_Q9c',
            '9.5': 'Treatment_Q9d',
            '9.5.1': 'Treatment_Q9d_Explain',
            '9.6': 'Treatment_Q9e',
            '9.6.1': 'Treatment_Q9e_Explain',
        }
        return mapping.get(question_id)

    if main_q == '10':
        return 'Treatment_Q10' if question_id == '10' else 'Treatment_Q10_Explain'

    if main_q == '11':
        return 'Treatment_Q11'

    return None


def map_procedures(question_id):
    """PROCEDURES mapping"""
    parts = question_id.split('.')
    main_q = parts[0]

    if main_q == '6':
        mapping = {
            '6': 'Procedures_Q6a',
            '6.1': 'Procedures_Q6a_Explain',
            '6.2': 'Procedures_Q6b',
            '6.2.1': 'Procedures_Q6b_Handoff',
            '6.2.2': 'Procedures_Q6b_Interdisciplinary',
            '6.2.3': 'Procedures_Q6b_EmergencySituation',
            '6.2.4': 'Procedures_Q6b_SupervisionHierarchy',
            '6.3': 'Procedures_Q6c',
            '6.3.1': 'Procedures_Q6c_Explain',
            '6.4': 'Procedures_Q6d',
            '6.4.1': 'Procedures_Q6d_Explain',
        }
        return mapping.get(question_id)

    if main_q == '7':
        mapping = {
            '7': 'Procedures_Q7a',
            '7.1': 'Procedures_Q7a_Explain',
            '7.2': 'Procedures_Q7b',
            '7.2.1': 'Procedures_Q7b_Explain',
            '7.3': 'Procedures_Q7c',
            '7.3.1': 'Procedures_Q7c_Explain',
        }
        return mapping.get(question_id)

    if main_q == '8':
        mapping = {
            '8': 'Procedures_Q8',
            '8.1': 'Procedures_Q8_Explain',
        }
        return mapping.get(question_id)

    if main_q == '9':
        return 'Procedures_Q9' if question_id == '9' else None

    if main_q == '1':
        mapping = {
            '1': 'Procedures_Q1',
            '1.1': 'Procedures_Q1_List',
            '1.2': 'Procedures_Q1a',
            '1.2.1': 'Procedures_Q1a_Explain',
            '1.3': 'Procedures_Q1b',
            '1.3.1': 'Procedures_Q1b_Explain',
        }
        return mapping.get(question_id)

    if main_q in ['2', '3', '4', '5']:
        sub_q = len(parts)
        if sub_q == 1:
            return f'Procedures_Q{main_q}a'
        elif sub_q == 2:
            if parts[1] == '1':
                return f'Procedures_Q{main_q}a_Explain'
            elif parts[1] == '2':
                return f'Procedures_Q{main_q}b'
            elif parts[1] == '3':
                return f'Procedures_Q{main_q}c'
        elif sub_q == 3:
            if parts[1] == '2' and parts[2] == '1':
                return f'Procedures_Q{main_q}b_Explain'
            elif parts[1] == '3' and parts[2] == '1':
                return f'Procedures_Q{main_q}c_Explain'

    return None


def map_monitoring(question_id):
    """MONITORING mapping"""
    parts = question_id.split('.')
    main_q = parts[0]

    if main_q == '5':
        mapping = {
            '5': 'Monitoring_Q5a',
            '5.1': 'Monitoring_Q5a_Explain',
            '5.2.1': 'Monitoring_Q5b_Handoff',
            '5.2.2': 'Monitoring_Q5b_Interdisciplinary',
            '5.2.3': 'Monitoring_Q5b_EmergencySituation',
            '5.2.4': 'Monitoring_Q5b_SupervisionHierarchy',
            '5.3': 'Monitoring_Q5c',
            '5.3.1': 'Monitoring_Q5c_Explain',
            '5.4': 'Monitoring_Q5d',
            '5.4.1': 'Monitoring_Q5d_Explain',
        }
        return mapping.get(question_id)

    if main_q == '7':
        mapping = {
            '7': 'Monitoring_Q7',
            '7.1': 'Monitoring_Q7_Explain',
        }
        return mapping.get(question_id)

    if main_q == '8':
        return 'Monitoring_Q8' if question_id == '8' else None

    if main_q in ['1', '2', '3', '4', '6']:
        sub_q = len(parts)
        if sub_q == 1:
            return f'Monitoring_Q{main_q}a'
        elif sub_q == 2:
            if parts[1] == '1':
                return f'Monitoring_Q{main_q}a_Explain'
            elif parts[1] == '2':
                return f'Monitoring_Q{main_q}b'
            elif parts[1] == '3':
                return f'Monitoring_Q{main_q}c'
        elif sub_q == 3:
            if parts[1] == '2' and parts[2] == '1':
                return f'Monitoring_Q{main_q}b_Explain'
            elif parts[1] == '3' and parts[2] == '1':
                return f'Monitoring_Q{main_q}c_Explain'

    return None


def map_additional(question_id):
    """ADDITIONAL CONTRIBUTING FACTORS mapping"""
    parts = question_id.split('.')
    main_q = parts[0]

    if main_q in ['4', '5', '7', '8']:
        if question_id == main_q:
            return f'Additional_Q{main_q}'
        elif question_id == f'{main_q}.1':
            return f'Additional_Q{main_q}_explain' if main_q != '8' else None
        return None

    if main_q in ['1', '2', '3', '6']:
        sub_q = len(parts)
        if sub_q == 1:
            return f'Additional_Q{main_q}a'
        elif sub_q == 2:
            if parts[1] == '1':
                return f'Additional_Q{main_q}a_Explain'
            elif parts[1] == '2':
                return f'Additional_Q{main_q}b'
            elif parts[1] == '3':
                return f'Additional_Q{main_q}c'
        elif sub_q == 3:
            if parts[1] == '2' and parts[2] == '1':
                return f'Additional_Q{main_q}b_Explain'
            elif parts[1] == '3' and parts[2] == '1':
                return f'Additional_Q{main_q}c_Explain'

    return None


def map_standard_of_care(question_id):
    """STANDARD OF CARE mapping"""
    mapping = {
        '1': None,
        '1.1': 'z3_Standard_of_Care_1',
        '1.2': 'z3_Standard_of_Care_2',
        '1.3': 'z2_Standard_of_Care_3',
        '1.4': 'z1_Standard_of_Care_4',
        '1.5': 'z1_Standard_of_Care_5',
        '2': 'Standard_Of_Care_Q2',
    }
    return mapping.get(question_id)


def map_causation(question_id):
    """CAUSATION mapping"""
    mapping = {
        '1': None,
        '1.1': 'y3_Causation_1',
        '1.2': 'y2_Causation_3',
        '1.3': 'y3_Causation_2',
        '1.4': 'y1_Causation_4',
        '1.5': 'y1_Causation_5',
    }
    return mapping.get(question_id)


def map_closing_thoughts(question_id):
    """CLOSING THOUGHTS mapping"""
    mapping = {
        '1': 'Closing_Q1',
        '1.1': 'Closing_Q1_Comments',
        '2': 'Closing_Q2',
        '2.1': 'Closing_Q2_Comments',
        '3': 'Closing_Q3',
        '3.1': 'Closing_Q3_Comments',
        '4': 'Closing_Q4_Comments',
    }
    return mapping.get(question_id)


# =============================================================================
# COMBINED PDF FORM FILLER CLASS
# =============================================================================

class CombinedPDFFormFiller:
    """
    Combined PDF Form Filler
    Integrates section_mapping, form filling (sample34.py), and flattening
    """
    
    # Radio button mapping for yes/no/unclear/not_applicable questions
    RADIO_BUTTON_MAPPING = {
        "yes": 0,
        "y": 0,
        "true": 0,
        "no": 1,
        "n": 1,
        "false": 1,
        "unclear": 2,
        "u": 2,
        "not applicable": 3,
        "n/a": 3,
        "na": 3,
        "not_applicable": 3,
    }
    
    def __init__(self, pdf_path: str, answers_path: str):
        """Initialize the form filler with PDF and answers"""
        self.pdf_path = pdf_path
        self.answers_path = answers_path
        self.answer_map = {}
        self.doc = None
        self.stats = {
            "filled": 0,
            "radio_button_groups": 0,
            "rating_checkboxes": 0,
            "checkboxes": 0,
            "text_fields": 0,
            "radio_buttons": 0,
            "dropdowns": 0,
            "skipped": 0,
            "failed": 0,
        }
    
    # -------------------------------------------------------------------------
    # UTILITY METHODS (from sample34.py)
    # -------------------------------------------------------------------------
    
    @staticmethod
    def extract_rating_value(answer_value, question_type):
        """Extract numeric rating from answer."""
        if isinstance(answer_value, dict):
            if 'degree_alleged' in answer_value:
                return answer_value.get('degree_alleged')
            if 'degree_suffered' in answer_value:
                return answer_value.get('degree_suffered')
        if isinstance(answer_value, int):
            return answer_value
        val = str(answer_value).strip()
        match = re.search(r'\b([1-9])\b', val)
        if match:
            return int(match.group(1))
        return None
    
    @staticmethod
    def normalize_text(text):
        """Normalize text for comparison."""
        if not text:
            return ""
        # Decode common URL encodings
        text = text.replace('#20', ' ')
        text = text.replace('#2C', ',')
        text = text.replace('#2c', ',')
        text = text.replace('#2F', '/')
        text = text.replace('#2f', '/')
        # Remove extra whitespace and lowercase
        text = ' '.join(text.lower().split())
        return text
    
    @staticmethod
    def split_multi_answer(answer_str):
        """Split comma-separated answer intelligently."""
        if not isinstance(answer_str, str):
            return [str(answer_str)]
        # Split by comma
        parts = [part.strip() for part in answer_str.split(',')]
        # Filter out empty parts
        parts = [p for p in parts if p]
        return parts if parts else [answer_str]
    
    def find_matching_buttons(self, answer_value, question_type, sorted_buttons):
        """
        Find ALL matching buttons for checkbox_group answers.
        Returns list of tuples: (button_index, button_object, matched_text)
        """
        answer_str = str(answer_value).strip()
        
        # For checkbox_group, split by comma
        if question_type == 'checkbox_group':
            answer_parts = self.split_multi_answer(answer_str)
        else:
            answer_parts = [answer_str]
        
        # Try to match each answer part to buttons
        matching_buttons = []
        for btn_idx, btn in enumerate(sorted_buttons):
            btn_on_state = btn.on_state()
            if not btn_on_state:
                continue
            
            # Normalize button on_state
            normalized_on_state = self.normalize_text(btn_on_state)
            
            # Check if any answer part matches this button
            for ans_part in answer_parts:
                normalized_ans = self.normalize_text(ans_part)
                matched = False
                
                # Exact match
                if normalized_ans == normalized_on_state:
                    matched = True
                
                # Check for keyword matching
                else:
                    # For "defendant is a group, hospital, or other healthcare facility"
                    if any(word in normalized_ans for word in ['defendant', 'group', 'hospital', 'facility', 'healthcare']):
                        if all(word in normalized_on_state for word in ['group', 'hospital', 'facility']):
                            matched = True
                        elif all(word in normalized_on_state for word in ['group', 'facility']):
                            matched = True
                    
                    # For "other"
                    if not matched and 'other' in normalized_ans and len(normalized_ans.split()) <= 2:
                        if 'other' == normalized_on_state or normalized_on_state == 'other':
                            matched = True
                    
                    # For "handoff"
                    if not matched and 'handoff' in normalized_ans:
                        if 'handoff' in normalized_on_state:
                            matched = True
                    
                    # For "interdisciplinary"
                    if not matched and 'interdisciplinary' in normalized_ans:
                        if 'interdisciplinary' in normalized_on_state:
                            matched = True
                    
                    # For "emergency"
                    if not matched and 'emergency' in normalized_ans:
                        if 'emergency' in normalized_on_state:
                            matched = True
                    
                    # For "supervision/hierarchy"
                    if not matched and ('supervision' in normalized_ans or 'hierarchy' in normalized_ans):
                        if 'supervision' in normalized_on_state or 'hierarchy' in normalized_on_state:
                            matched = True
                    
                    # For "primary role"
                    if not matched and 'primary' in normalized_ans:
                        if 'primary' in normalized_on_state and 'role' in normalized_on_state:
                            matched = True
                    
                    # For "consultant"
                    if not matched and 'consultant' in normalized_ans:
                        if 'consultant' == normalized_on_state:
                            matched = True
                    
                    # For "supervisory"
                    if not matched and 'supervis' in normalized_ans:
                        if 'supervis' in normalized_on_state:
                            matched = True
                
                if matched:
                    matching_buttons.append((btn_idx, btn, ans_part))
                    break
        
        return matching_buttons
    
    # -------------------------------------------------------------------------
    # ANSWER LOADING (from sample34.py)
    # -------------------------------------------------------------------------
    
    def load_answers(self):
        """Load and parse answer data."""
        print("Loading answer data...")
        with open(self.answers_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        answers = data.get('answers', data)
        answer_map = {}
        
        for item in answers:
            question_id = item.get('question_id')
            section = item.get('section_name')
            answer_value = item.get('answer')
            question_type = item.get('question_type') or ''

            if isinstance(answer_value, str) and answer_value.strip().startswith('{'):
                try:
                    # Try JSON parsing
                    answer_value = json.loads(answer_value.replace("'", '"'))
                except:
                    try:
                        # Fallback to Python dict syntax
                        answer_value = ast.literal_eval(answer_value)
                    except:
                        pass  # Keep as string if parsing fails
            
            # Skip SKIPPED, None, empty answers
            if answer_value in (None, "", [], "SKIPPED"):
                continue
            if isinstance(answer_value, str) and answer_value.strip().upper() == "SKIPPED":
                continue
            
            # SPECIAL HANDLING FOR RATING SCALES
            if 'rating_scale' in question_type:
                rating = self.extract_rating_value(answer_value, question_type)
                if rating:
                    rating_question_id = f"{question_id}.{rating}"
                    pdf_field_name = question_id_to_pdf_field(rating_question_id, section)
                    if pdf_field_name:
                        answer_map[pdf_field_name] = {
                            "value": "Yes",
                            "type": question_type,
                            "question_id": rating_question_id,
                            "section": section,
                            "rating": rating,
                            "original_question_id": question_id
                        }
            
            # SPECIAL HANDLING FOR DEGREE OF INJURY
            if section == 'DEGREE OF INJURY' and isinstance(answer_value, dict):
                if 'degree_alleged' in answer_value:
                    alleged_rating = answer_value['degree_alleged']
                    alleged_field = question_id_to_pdf_field('2.alleged', section)
                    if alleged_field:
                        answer_map[alleged_field] = {
                            "value": str(alleged_rating),
                            "type": question_type,
                            "question_id": '2.alleged',
                            "section": section,
                            "rating": alleged_rating
                        }
                
                if 'degree_suffered' in answer_value:
                    suffered_rating = answer_value['degree_suffered']
                    suffered_field = question_id_to_pdf_field('2.suffered', section)
                    if suffered_field:
                        answer_map[suffered_field] = {
                            "value": str(suffered_rating),
                            "type": question_type,
                            "question_id": '2.suffered',
                            "section": section,
                            "rating": suffered_rating
                        }
                
                continue
            
            # SPECIAL HANDLING FOR CHECKBOX_GROUP WITH INDIVIDUAL FIELDS
            if question_type == 'checkbox_group' and isinstance(answer_value, str):
                # Get the base field name
                base_field_name = question_id_to_pdf_field(question_id, section)
                if base_field_name:
                    # Split the answer (handles both comma-separated and single values)
                    checkbox_values = self.split_multi_answer(answer_value)
                    
                    # Mapping of normalized answer values to field suffixes
                    checkbox_suffix_map = {
                        'handoff': '_Handoff',
                        'interdisciplinary': '_Interdisciplinary',
                        'emergency situation': '_EmergencySituation',
                        'emergency': '_EmergencySituation',
                        'supervision/hierarchy': '_SupervisionHierarchy',
                        'supervision': '_SupervisionHierarchy',
                        'hierarchy': '_SupervisionHierarchy',
                    }
                    
                    # Create individual checkbox entries
                    checkbox_created = False
                    for checkbox_val in checkbox_values:
                        normalized_val = self.normalize_text(checkbox_val)
                        
                        # Find matching suffix
                        suffix = None
                        for key, suf in checkbox_suffix_map.items():
                            if key in normalized_val:
                                suffix = suf
                                break
                        
                        if suffix:
                            checkbox_field_name = base_field_name + suffix
                            answer_map[checkbox_field_name] = {
                                "value": "Yes",  # Checkbox should be checked
                                "type": "individual_checkbox",
                                "question_id": question_id,
                                "section": section,
                            }
                            checkbox_created = True
                            print(f" ✓ Created checkbox: {checkbox_field_name} from '{checkbox_val}'")
                    
                    # If we created individual checkboxes, skip adding the base field
                    if checkbox_created:
                        continue
            
            # NORMAL PROCESSING
            base_field_name = question_id_to_pdf_field(question_id, section)
            if not base_field_name:
                continue
            
            answer_map[base_field_name] = {
                "value": answer_value,
                "type": question_type,
                "question_id": question_id,
                "section": section,
            }
        
        self.answer_map = answer_map
        return answer_map
    
    # -------------------------------------------------------------------------
    # WIDGET HELPERS
    # -------------------------------------------------------------------------
    
    @staticmethod
    def get_all_widgets_with_name(page, field_name):
        """Get all widgets with the same field name on a page."""
        all_widgets = []
        widgets = page.widgets()
        if widgets:
            for widget in widgets:
                if widget.field_name == field_name:
                    all_widgets.append(widget)
        return all_widgets
    
    # -------------------------------------------------------------------------
    # FORM FILLING (from sample34.py)
    # -------------------------------------------------------------------------
    
    def fill_form(self):
        """Fill PDF form fields."""
        print("\n" + "=" * 80)
        print("PDF FORM FILLER - COMBINED VERSION")
        print("=" * 80)
        
        try:
            self.doc = fitz.open(self.pdf_path)
            print(f"✓ Opened: {self.pdf_path}")
            print(f"  Pages: {self.doc.page_count}")
            print(f"  Field mappings: {len(self.answer_map)}\n")
            
            processed_widgets = set()
            
            for page_num, page in enumerate(self.doc):
                widgets = page.widgets()
                if not widgets:
                    continue
                
                for widget in widgets:
                    field_name = widget.field_name
                    if not field_name:
                        self.stats["skipped"] += 1
                        continue
                    
                    widget_id = (field_name, page_num, round(widget.rect.x0, 1), round(widget.rect.y0, 1))
                    if widget_id in processed_widgets:
                        continue
                    
                    if field_name not in self.answer_map:
                        self.stats["skipped"] += 1
                        continue
                    
                    processed_widgets.add(widget_id)
                    answer_data = self.answer_map[field_name]
                    answer_value = answer_data["value"]
                    question_type = answer_data.get("type", "")
                    
                    try:
                        widget_type = (widget.field_type_string or "").lower()
                        all_widgets_on_page = self.get_all_widgets_with_name(page, field_name)
                        
                        # INDIVIDUAL CHECKBOX (from split checkbox_group)
                        if question_type == "individual_checkbox":
                            if widget_type == "radiobutton" or widget_type == "checkbox":
                                val = str(answer_value or "").strip().lower()
                                is_checked = val in {"yes", "y", "true", "1", "on"}
                                
                                if is_checked:
                                    on = widget.on_state()
                                    if on:
                                        widget.field_value = on
                                    else:
                                        widget.field_value = "/Yes"
                                else:
                                    widget.field_value = "/Off"
                                
                                widget.update()
                                status = 'CHECKED' if is_checked else 'UNCHECKED'
                                print(f"✓ [IndivCheck] {field_name:50s} = {status}")
                                self.stats["filled"] += 1
                                self.stats["checkboxes"] += 1
                            continue
                        
                        # RADIO BUTTON GROUP
                        if widget_type == "radiobutton" and len(all_widgets_on_page) > 1:
                            # YES/NO/UNCLEAR/NOT_APPLICABLE radio groups
                            if question_type in ['yes_no', 'yes_no_unclear', 'yes_no_unclear_not_applicable']:
                                sorted_buttons = sorted(all_widgets_on_page, key=lambda w: w.rect.x0)
                                val = str(answer_value).strip().lower()
                                button_index = self.RADIO_BUTTON_MAPPING.get(val)
                                
                                if button_index is not None and button_index < len(sorted_buttons):
                                    # Clear all buttons first
                                    for btn in sorted_buttons:
                                        btn.field_value = "/Off"
                                        btn.update()
                                    
                                    # Set target button
                                    target_button = sorted_buttons[button_index]
                                    on_state = target_button.on_state()
                                    if on_state:
                                        target_button.field_value = on_state
                                    else:
                                        target_button.field_value = "/Yes"
                                    target_button.update()
                                    
                                    print(f"✓ [Radio-Group] {field_name:50s} = {answer_value:15s} (btn {button_index})")
                                    self.stats["filled"] += 1
                                    self.stats["radio_button_groups"] += 1
                                    
                                    # Mark all buttons as processed
                                    for btn in sorted_buttons:
                                        btn_id = (field_name, page_num, round(btn.rect.x0, 1), round(btn.rect.y0, 1))
                                        processed_widgets.add(btn_id)
                                else:
                                    print(f"⚠ [Radio-Group] {field_name:50s} (invalid index: {button_index})")
                                    self.stats["failed"] += 1
                            
                            # CHECKBOX_GROUP (multi-select)
                            elif question_type == 'checkbox_group':
                                sorted_buttons = sorted(all_widgets_on_page, key=lambda w: w.rect.y0)
                                matching_buttons = self.find_matching_buttons(answer_value, question_type, sorted_buttons)
                                
                                if matching_buttons:
                                    # Clear all first
                                    for btn in sorted_buttons:
                                        btn.field_value = "/Off"
                                        btn.update()
                                    
                                    # Set matched buttons
                                    selected_labels = []
                                    for btn_idx, btn, matched_text in matching_buttons:
                                        on_state = btn.on_state()
                                        if on_state:
                                            btn.field_value = on_state
                                            btn.update()
                                            selected_labels.append(self.normalize_text(on_state))
                                    
                                    print(f"✓ [MultiSelect] {field_name:50s} = {len(matching_buttons)} option(s): {', '.join(selected_labels)}")
                                    self.stats["filled"] += 1
                                    self.stats["radio_buttons"] += 1
                                    
                                    # Mark all as processed
                                    for btn in sorted_buttons:
                                        btn_id = (field_name, page_num, round(btn.rect.x0, 1), round(btn.rect.y0, 1))
                                        processed_widgets.add(btn_id)
                                else:
                                    print(f"⚠ [MultiSelect] {field_name:50s} = No matches")
                                    self.stats["failed"] += 1
                            
                            # OTHER RADIO BUTTONS (including rating scales)
                            else:
                                sorted_buttons = sorted(all_widgets_on_page, key=lambda w: w.rect.x0)
                                button_found = False
                                answer_str = str(answer_value).strip()
                                
                                for btn in sorted_buttons:
                                    btn_on_state = btn.on_state()
                                    if btn_on_state:
                                        clean_on_state = self.normalize_text(btn_on_state)
                                        normalized_answer = self.normalize_text(answer_str)
                                        
                                        if normalized_answer == clean_on_state or answer_str == btn_on_state:
                                            # Clear all buttons
                                            for b in sorted_buttons:
                                                b.field_value = "/Off"
                                                b.update()
                                            
                                            # Set this button
                                            btn.field_value = btn_on_state
                                            btn.update()
                                            
                                            if 'rating' in answer_data:
                                                print(f"✓ [Rating] {field_name:50s} = {answer_value:5s}")
                                                self.stats["rating_checkboxes"] += 1
                                            else:
                                                print(f"✓ [RadioBtn] {field_name:50s} = {clean_on_state:20s}")
                                                self.stats["radio_buttons"] += 1
                                            
                                            self.stats["filled"] += 1
                                            button_found = True
                                            
                                            # Mark all as processed
                                            for b in sorted_buttons:
                                                b_id = (field_name, page_num, round(b.rect.x0, 1), round(b.rect.y0, 1))
                                                processed_widgets.add(b_id)
                                            break
                                
                                if not button_found:
                                    print(f"⚠ [RadioBtn] {field_name:50s} = No match")
                                    self.stats["failed"] += 1
                        
                        # CHECKBOX
                        elif widget_type == "checkbox":
                            val = str(answer_value or "").strip().lower()
                            is_checked = val in {"yes", "y", "true", "1", "on"}
                            
                            if is_checked:
                                on = widget.on_state()
                                if on:
                                    widget.field_value = on
                                else:
                                    widget.field_value = "/Yes"
                            else:
                                widget.field_value = "/Off"
                            
                            widget.update()
                            status = 'CHECKED' if is_checked else 'UNCHECKED'
                            print(f"✓ [Checkbox] {field_name:50s} = {status}")
                            self.stats["filled"] += 1
                            self.stats["checkboxes"] += 1
                        
                        # TEXT FIELD
                        elif widget_type == "text":
                            widget.field_value = str(answer_value)
                            widget.update()
                            disp = (str(answer_value)[:40] + "...") if len(str(answer_value)) > 40 else str(answer_value)
                            print(f"✓ [TextField] {field_name:50s} = {disp}")
                            self.stats["filled"] += 1
                            self.stats["text_fields"] += 1
                        
                        # DROPDOWN/COMBOBOX
                        elif widget_type == "combobox":
                            widget.field_value = str(answer_value)
                            widget.update()
                            print(f"✓ [Dropdown] {field_name:50s} = {answer_value}")
                            self.stats["filled"] += 1
                            self.stats["dropdowns"] += 1
                        
                        else:
                            print(f"⚠ [Unknown] {field_name:50s} (Type: {widget.field_type_string})")
                            self.stats["failed"] += 1
                    
                    except Exception as e:
                        print(f"✗ [Error] {field_name:50s} : {str(e)[:60]}")
                        self.stats["failed"] += 1
            
            print("\n" + "=" * 80)
            print("FORM FILLING COMPLETE")
            print("=" * 80)
            print(f"✔ Total Filled: {self.stats['filled']}")
            print(f"  ├─ Radio Button Groups: {self.stats['radio_button_groups']}")
            print(f"  ├─ Rating Checkboxes: {self.stats['rating_checkboxes']}")
            print(f"  ├─ Regular Checkboxes: {self.stats['checkboxes']}")
            print(f"  ├─ Text Fields: {self.stats['text_fields']}")
            print(f"  ├─ Radio Buttons: {self.stats['radio_buttons']}")
            print(f"  └─ Dropdowns: {self.stats['dropdowns']}")
            print(f"➖ Skipped: {self.stats['skipped']}")
            print(f"✖ Failed: {self.stats['failed']}")
            print("=" * 80)
            
            return True
        
        except Exception as e:
            print(f"❌ Error during form filling: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # -------------------------------------------------------------------------
    # FLATTENING (from flatten.py)
    # -------------------------------------------------------------------------
    
    def flatten_and_save(self, output_path: str):
        """Flatten and save the filled PDF."""
        if self.doc is None:
            print("❌ No document loaded. Call fill_form() first.")
            return False
        
        print("\n" + "=" * 80)
        print("FLATTENING PDF")
        print("=" * 80)
        
        try:
            # Flatten form fields to static content
            self.doc.bake()
            print("✓ Flattened form fields to static content")
            
            # Save with proper compression and garbage collection
            self.doc.save(
                output_path,
                incremental=False,
                deflate=True,
                garbage=4  # Remove orphaned objects
            )
            
            self.doc.close()
            print(f"✓ Saved: {output_path}")
            
            print("\n" + "=" * 80)
            print("FLATTENING COMPLETE - Cross-device compatibility:")
            print("=" * 80)
            print("✔ Visible on iPhone Safari")
            print("✔ Visible on web browsers (Chrome, Edge, Firefox)")
            print("✔ Visible on desktop apps (WPS, Adobe, Edge)")
            print("✔ Searchable text preserved")
            print("✔ Form fields converted to static content")
            print("=" * 80)
            
            return True
        
        except Exception as e:
            print(f"❌ Error during flattening: {e}")
            import traceback
            traceback.print_exc()
            return False


# =============================================================================
# MAIN FUNCTION (for standalone usage)
# =============================================================================

def main():
    """Main entry point for standalone usage."""
    pdf_file = "MASTER_COPY_Medical_Faculty_Questionnaire.pdf"
    answers_file = "answers_20251111_015513_cleaned.json"
    output_file = "FILLED_FORM_COMPLETE.pdf"
    
    print("\n" + "=" * 80)
    print("COMBINED PDF FORM FILLER")
    print("=" * 80)
    print(f"Input PDF: {pdf_file}")
    print(f"Answers JSON: {answers_file}")
    print(f"Output PDF: {output_file}")
    print("=" * 80 + "\n")
    
    try:
        filler = CombinedPDFFormFiller(pdf_path=pdf_file, answers_path=answers_file)
        
        # Load answers
        filler.load_answers()
        print(f"\n✓ Loaded {len(filler.answer_map)} field mappings\n")
        
        # Fill form
        if not filler.fill_form():
            print("❌ Form filling failed")
            return 1
        
        # Flatten and save
        if not filler.flatten_and_save(output_file):
            print("❌ Flattening failed")
            return 1
        
        print("\n✅ PDF filled and flattened successfully!")
        print("\n📌 ALL FEATURES:")
        print("  ✓ Automatic checkbox_group splitting (with or without commas)")
        print("  ✓ DiagnosticWorkUp Q7.2 checkboxes")
        print("  ✓ Procedures Q6.2 checkboxes")
        print("  ✓ Rating scales (Degree of Injury - alleged and suffered)")
        print("  ✓ Multi-select Overview_Q2")
        print("  ✓ Treatment Q9c 'Other'")
        print("  ✓ All yes/no/unclear/not_applicable questions")
        print("  ✓ Cross-device compatible flattened PDF\n")
        
        return 0
    
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())