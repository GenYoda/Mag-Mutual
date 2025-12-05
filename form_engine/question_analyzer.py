"""
question_analyzer.py - Analyzes questions to determine context needs

Parses question text and structure to identify:
- Sub-questions needing parent context
- Questions with explicit range references (Q1-7)
- Synthesis questions needing full section context
"""

import re
from typing import Optional, Tuple, List


class QuestionAnalyzer:
    """
    Analyzes questions to determine what context they need
    """
    
    # Regex patterns for detecting question ranges
    RANGE_PATTERNS = [
        r'Q(\d+)-(\d+)',                          # Q1-7
        r'Q(\d+)\s+to\s+Q?(\d+)',                 # Q1 to 7, Q1 to Q7
        r'questions?\s+(\d+)\s+through\s+(\d+)',  # question 1 through 7
        r'Question\s+(\d+)\s+to\s+Question\s+(\d+)',  # Question 1 to Question 7
    ]
    
    # Keywords indicating synthesis questions
    SYNTHESIS_KEYWORDS = [
        'additional insights',
        'provide any',
        'summarize',
        'overall',
        'in summary',
        'additional information',
        'additional context',
        'any other',
        'further details'
    ]
    
    @staticmethod
    def extract_parent_chain(question_id: str) -> List[str]:
        """
        Extract parent question chain from question ID
        
        Examples:
            "7" → []
            "7.1" → ["7"]
            "7.2" → ["7", "7.1"]
            "7.3" → ["7", "7.1", "7.2"]
            "7.2.1" → ["7", "7.1", "7.2"]
        
        Args:
            question_id: Question ID (e.g., "7.2")
            
        Returns:
            List of parent question IDs
        """
        parts = question_id.split('.')
        
        if len(parts) == 1:
            # No parents (top-level question)
            return []
        
        # Build parent chain
        parents = []
        for i in range(len(parts) - 1):
            parent_id = '.'.join(parts[:i+1])
            parents.append(parent_id)
        
        return parents
    
    @classmethod
    def parse_question_range(cls, question_text: str) -> Optional[Tuple[str, str]]:
        """
        Parse question text for explicit range references
        
        Examples:
            "...in Q1-7..." → ("1", "7")
            "...questions 1 through 10..." → ("1", "10")
            "...no range..." → None
        
        Args:
            question_text: The question text to analyze
            
        Returns:
            Tuple of (start_id, end_id) or None if no range found
        """
        for pattern in cls.RANGE_PATTERNS:
            match = re.search(pattern, question_text, re.IGNORECASE)
            if match:
                start_id, end_id = match.groups()
                return (start_id, end_id)
        
        return None
    
    @classmethod
    def is_synthesis_question(cls, question_text: str) -> bool:
        """
        Check if question is a synthesis question needing full context
        
        Args:
            question_text: The question text to analyze
            
        Returns:
            True if synthesis question, False otherwise
        """
        question_lower = question_text.lower()
        
        for keyword in cls.SYNTHESIS_KEYWORDS:
            if keyword in question_lower:
                return True
        
        return False
    
    @staticmethod
    def is_sub_question(question_id: str) -> bool:
        """
        Check if question is a sub-question (has a parent)
        
        Args:
            question_id: Question ID (e.g., "7.2")
            
        Returns:
            True if sub-question, False otherwise
        """
        return '.' in question_id
