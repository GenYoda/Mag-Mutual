"""
Validators - Input and output validation
"""

import json
from typing import Dict, List, Optional

class QuestionValidator:
    """Validate questions.json format"""
    
    @staticmethod
    def validate(questions_data: List[Dict]) -> tuple[bool, str]:
        """
        Validate questions structure
        
        Args:
            questions_data: List of question dicts
        
        Returns:
            (is_valid, error_message)
        """
        required_fields = ['question_id', 'main_question', 'question_type', 'page_number']
        
        for i, q in enumerate(questions_data):
            for field in required_fields:
                if field not in q:
                    return False, f"Question {i}: Missing '{field}'"
        
        return True, "Valid"

class AnswerValidator:
    """Validate answers.json format"""
    
    @staticmethod
    def validate(answers_data: List[Dict]) -> tuple[bool, str]:
        """
        Validate answers structure
        
        Args:
            answers_data: List of answer dicts
        
        Returns:
            (is_valid, error_message)
        """
        required_fields = ['question_id', 'answer', 'confidence']
        
        for i, a in enumerate(answers_data):
            for field in required_fields:
                if field not in a:
                    return False, f"Answer {i}: Missing '{field}'"
        
        return True, "Valid"
