"""
answer_formatter.py - Format answers based on question type and requirements (OPTIMIZED)
"""

import re
from typing import Dict


class AnswerFormatter:
    """
    Formats answers based on question type and structure
    Optimized for speed
    """
    @staticmethod
    def detect_field_type(question_text: str) -> str:
        """
        Detect field type based on question text
        """
        q_lower = question_text.lower()
        
        if any(word in q_lower for word in ['phone', 'contact', 'number']):
            return 'phone'
        elif any(word in q_lower for word in ['date', 'when', 'time']):
            return 'date'
        elif any(word in q_lower for word in ['email', 'mail']):
            return 'email'
        elif any(word in q_lower for word in ['name', 'defendant', 'plaintiff', 'attorney', 'reviewer']):  # ✅ Added 'reviewer'
            return 'name'
        elif any(word in q_lower for word in ['address', 'location', 'city', 'state', 'zip']):
            return 'address'
        else:
            return 'text'

    @staticmethod
    def clean_answer(answer_text: str, question_text: str = "") -> str:
        """
        Smart cleaning based on detected field type
        """
        if not answer_text or answer_text == "NOT_FOUND":
            return answer_text
        
        cleaned = answer_text.strip()
        
        # Detect field type from question text
        field_type = AnswerFormatter.detect_field_type(question_text)
        
        # FIELD-TYPE SPECIFIC EXTRACTION
        if field_type == 'phone':
            # Extract ONLY phone number
            phone_pattern = r'(?:\+?1?\s*)?(?:\()?(\d{3})(?:\))?[-.\s]?(\d{3})[-.\s]?(\d{4}|\d+)|\b\d{7,10}\b'
            match = re.search(phone_pattern, cleaned)
            if match:
                return match.group(0).strip().replace(' ', '')
        
        elif field_type == 'date':
            # Extract date patterns
            date_pattern = r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b'
            match = re.search(date_pattern, cleaned, re.IGNORECASE)
            if match:
                return match.group(0)
        
        elif field_type == 'email':
            # Extract email
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            match = re.search(email_pattern, cleaned)
            if match:
                return match.group(0)
        
        elif field_type == 'name':
            # Remove various prefixes that might precede names
            cleaned = re.sub(r'^(?:defendant|plaintiff|attorney|reviewer)\s+name\s*:\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'^The\s+defendants?\s+are\s*:\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'^Defendant\s+names?\s*:\s*', '', cleaned, flags=re.IGNORECASE)  # ✅ NEW
            cleaned = re.sub(r'^[A-Z]:\s*', '', cleaned)  # ✅ NEW - removes "A: " prefixes
            cleaned = re.sub(r'^\d+\.\s+', '', cleaned)  # Remove "1. " prefixes in lists
            
            # Keep multiline names but clean each line
            lines = cleaned.split('\n')
            lines = [re.sub(r'^[-•*]\s*', '', line.strip()) for line in lines if line.strip()]
            cleaned = '\n'.join(lines)

        
        elif field_type == 'address':
            # Remove address label prefixes
            cleaned = re.sub(r'^(?:address|location)\s*:\s*', '', cleaned, flags=re.IGNORECASE)
        
        # GENERIC CLEANUP (all field types)
        # Remove conversational prefixes
        cleaned = re.sub(r'^The\s+\w+\s+(?:is|are)\s+', '', cleaned, flags=re.IGNORECASE)
        
        # Remove source citations
        cleaned = re.sub(r'\s*\[\s*(?:Source|Sources)\s*:.*?\]\s*', ' ', cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Remove trailing period only for very short answers (phone, email, dates)
        if field_type in ['phone', 'email', 'date'] and len(cleaned) < 100:
            cleaned = cleaned.rstrip('.')
        
        # Final validation
        if not cleaned or cleaned.lower() in ['unknown', 'n/a', 'not available', 'not provided', '']:
            return "NOT_FOUND"
        
        return cleaned
    
    
    @staticmethod
    def format_answer(answer_text: str, question_type: str, response_options: list, 
                    confidence: float, requires_explanation: bool = False) -> Dict:
        """
        Format answer - FAST PATH
        
        Args:
            answer_text: Raw LLM answer
            question_type: Type of question
            response_options: Available response options
            confidence: Confidence score
            requires_explanation: Whether explanation is required (ONLY determinant)
            
        Returns:
            Dict with formatted answer and optional explanation
        """
        
        # Fast path: No options = open-ended question
        if not response_options:
            return {
                'answer': answer_text if answer_text != 'NOT_FOUND' else 'Not Found',
                'confidence': confidence
            }
        
        # Initialize selected_answer for explanation check
        selected_answer = None
        
        # Option-based question: Handle single-select, multi-select, and ratings
        if question_type == 'checkbox_group':
            # Multi-select: Get ALL matching options
            selected_options = AnswerFormatter._extract_multiple_options(answer_text, response_options)
            selected_answer = ', '.join(selected_options) if selected_options else 'Not Found'
            result = {
                'answer': selected_answer,
                'confidence': confidence
            }
        
        # ========== NEW: Handle rating_scale_1_to_9 (dual rating) ==========
        elif question_type == 'rating_scale_1_to_9':
            # Extract ratings and build raw_answer
            rating_result = AnswerFormatter._extract_rating_1_to_9(answer_text, response_options)
            
            result = {
                'answer': rating_result['answer'],  # {"degree_alleged": 7, "degree_suffered": 6}
                'raw_answer': rating_result['raw_answer'],  # Formatted text with full options and explanations
                'confidence': confidence
            }
            selected_answer = None  # Skip explanation logic below
        
        # ========== NEW: Handle rating_scale_1_to_5 (single rating) ==========
        elif question_type == 'rating_scale_1_to_5':
            # Extract rating and build raw_answer
            rating_result = AnswerFormatter._extract_rating_1_to_5(answer_text, response_options)
            
            result = {
                'answer': rating_result['answer'],  # Just the number (e.g., 3)
                'raw_answer': rating_result['raw_answer'],  # Formatted text with full option and explanation
                'confidence': confidence
            }
            selected_answer = None  # Skip explanation logic below
        
        else:
            # Single-select: Get FIRST matching option
            selected_answer = AnswerFormatter._extract_option_fast(answer_text, response_options)
            result = {
                'answer': selected_answer,
                'confidence': confidence
            }
        
        # Add explanation ONLY if requires_explanation is True and answer was found
        if requires_explanation and selected_answer and selected_answer != 'Not Found':
            explanation = AnswerFormatter._extract_explanation_fast(answer_text)
            if explanation:
                result['explanation'] = explanation
        
        return result
            
    
    @staticmethod
    def _extract_option_fast(answer_text: str, response_options: list) -> str:
        """
        FAST option extraction - Single pass
        
        Args:
            answer_text: Full LLM answer
            response_options: Available options
            
        Returns:
            Selected option or 'Not Found'
        """
        if not answer_text or not response_options:
            return 'Not Found'
        
        answer_lower = answer_text.lower()
        
        # Single pass: Check first 100 chars only (where option usually is)
        first_part = answer_lower[:100]
        
        for option in response_options:
            if option.lower() in first_part:
                return option
        
        return 'Not Found'
    
    @staticmethod
    def _extract_explanation_fast(answer_text: str) -> str:
        """
        FAST explanation extraction
        
        Splits on first period only, no regex
        
        Args:
            answer_text: Full LLM answer
            
        Returns:
            Explanation text
        """
        if not answer_text or '.' not in answer_text:
            return ""
        
        # Find first period
        idx = answer_text.find('. ')
        if idx < 0:
            return ""
        
        # Get everything after first period
        explanation = answer_text[idx + 2:].strip()
        
        # Remove source citations if present
        if '[Source:' in explanation:
            explanation = explanation[:explanation.index('[Source:')].strip()
        
        return explanation
    @staticmethod
    def _extract_multiple_options(answer_text: str, response_options: list) -> list:
        """
        Extract MULTIPLE matching options for checkbox_group
        
        Args:
            answer_text: Full LLM answer
            response_options: Available options
            
        Returns:
            List of selected options
        """
        if not answer_text or not response_options:
            return []
        
        answer_lower = answer_text.lower()
        selected = []
        
        # Search full text for all matching options
        for option in response_options:
            option_lower = option.lower()
            if option_lower in answer_lower:
                selected.append(option)
        
        return selected
    @staticmethod
    def _extract_rating_1_to_9(answer_text_dict: dict, response_options: list) -> dict:
        """
        Extract dual ratings (alleged and suffered) from rating_scale_1_to_9 questions
        
        Args:
            answer_text_dict: Dict with 'alleged' and 'suffered' keys containing LLM responses
            response_options: List of 9 rating options
        
        Returns:
            Dict with 'answer' (rating numbers) and 'raw_answer' (formatted text)
        """
        if not isinstance(answer_text_dict, dict):
            return {
                'answer': {'degree_alleged': 'Not Found', 'degree_suffered': 'Not Found'},
                'raw_answer': 'Error: Invalid answer format'
            }
        
        alleged_text = answer_text_dict.get('alleged', 'NOT_FOUND')
        suffered_text = answer_text_dict.get('suffered', 'NOT_FOUND')
        
        # Extract rating numbers and option text for both
        alleged_rating, alleged_option, alleged_explanation = AnswerFormatter._parse_rating_response(
            alleged_text, response_options
        )
        suffered_rating, suffered_option, suffered_explanation = AnswerFormatter._parse_rating_response(
            suffered_text, response_options
        )
        
        # Build answer dict (just numbers)
        answer = {
            'degree_alleged': alleged_rating,
            'degree_suffered': suffered_rating
        }
        
        # Build raw_answer (full text with options and explanations)
        raw_answer_parts = []
        
        raw_answer_parts.append("=== DEGREE OF INJURY ALLEGED ===")
        if alleged_rating != 'Not Found':
            raw_answer_parts.append(f"RATING: {alleged_rating}. {alleged_option}")
            raw_answer_parts.append(f"\nEXPLANATION: {alleged_explanation}\n")
        else:
            raw_answer_parts.append("RATING: Not Found\n")
        
        raw_answer_parts.append("\n=== DEGREE OF INJURY SUFFERED ===")
        if suffered_rating != 'Not Found':
            raw_answer_parts.append(f"RATING: {suffered_rating}. {suffered_option}")
            raw_answer_parts.append(f"\nEXPLANATION: {suffered_explanation}")
        else:
            raw_answer_parts.append("RATING: Not Found")
        
        return {
            'answer': answer,
            'raw_answer': '\n'.join(raw_answer_parts)
        }

    @staticmethod
    def _extract_rating_1_to_5(answer_text: str, response_options: list) -> dict:
        """
        Extract single rating from rating_scale_1_to_5 questions
        
        Args:
            answer_text: LLM response text
            response_options: List of 5 rating options
        
        Returns:
            Dict with 'answer' (rating number) and 'raw_answer' (formatted text)
        """
        # Extract rating number and option text
        rating_number, rating_option, explanation = AnswerFormatter._parse_rating_response(
            answer_text, response_options
        )
        
        # Build raw_answer (full text with option and explanation)
        if rating_number != 'Not Found':
            raw_answer = f"RATING: {rating_number}. {rating_option}\n\nEXPLANATION: {explanation}"
        else:
            raw_answer = "RATING: Not Found"
        
        return {
            'answer': rating_number,  # Just the number
            'raw_answer': raw_answer
        }

    @staticmethod
    def _parse_rating_response(llm_response: str, response_options: list) -> tuple:
        """
        Parse rating number, option text, and explanation from LLM response
        
        Args:
            llm_response: Full LLM response text
            response_options: List of rating options (e.g., ["1. No physical injury...", "2. Very slight..."])
        
        Returns:
            Tuple of (rating_number, rating_option_text, explanation)
        """
        if not llm_response or llm_response == 'NOT_FOUND':
            return ('Not Found', '', '')
        
        # Extract rating number using regex
        # Look for patterns like "RATING: 7" or "RATING: 7." or just "7."
        rating_match = re.search(r'RATING:\s*(\d+)', llm_response, re.IGNORECASE)
        
        if not rating_match:
            # Fallback: Look for first number in response
            fallback_match = re.search(r'\b([1-9])\b', llm_response)
            if fallback_match:
                rating_number = int(fallback_match.group(1))
            else:
                return ('Not Found', '', '')
        else:
            rating_number = int(rating_match.group(1))
        
        # Validate rating is in valid range
        max_rating = len(response_options)
        if rating_number < 1 or rating_number > max_rating:
            return ('Not Found', '', f'Invalid rating: {rating_number}')
        
        # Get the full option text from response_options
        rating_option = response_options[rating_number - 1]  # Convert 1-indexed to 0-indexed
        
        # Extract explanation (text after "EXPLANATION:")
        explanation = ''
        explanation_match = re.search(r'EXPLANATION:\s*(.+)', llm_response, re.IGNORECASE | re.DOTALL)
        if explanation_match:
            explanation = explanation_match.group(1).strip()
        else:
            # Fallback: Use everything after the rating line
            lines = llm_response.split('\n')
            if len(lines) > 1:
                explanation = '\n'.join(lines[1:]).strip()
        
        return (rating_number, rating_option, explanation)
