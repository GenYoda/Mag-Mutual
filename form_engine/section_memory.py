"""
section_memory.py - Section-level question-answer memory

Stores answered questions within a section for context injection.
Memory is cleared when section changes.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AnsweredQuestion:
    """Represents a single answered question"""
    question_id: str
    question_text: str
    answer: str
    question_type: str
    section_name: str


class SectionMemory:
    """
    Manages section-level memory of answered questions
    """
    
    def __init__(self):
        self.current_section: Optional[str] = None
        self.answers: Dict[str, AnsweredQuestion] = {}
    
    def set_section(self, section_name: str):
        """
        Switch to a new section (clears memory if section changed)
        
        Args:
            section_name: Name of the new section
        """
        if self.current_section != section_name:
            self.clear()
            self.current_section = section_name
    
    def add_answer(self, question: Dict, answer: str):
        """
        Add an answered question to memory
        
        Args:
            question: Question dict with metadata
            answer: The answer text
        """
        answered_q = AnsweredQuestion(
            question_id=question.get('question_id', ''),
            question_text=question.get('main_question', ''),
            answer=answer,
            question_type=question.get('question_type', ''),
            section_name=question.get('section_name', '')
        )
        
        self.answers[answered_q.question_id] = answered_q
    
    def get_answer(self, question_id: str) -> Optional[AnsweredQuestion]:
        """
        Get a specific answered question
        
        Args:
            question_id: ID of the question
            
        Returns:
            AnsweredQuestion or None if not found
        """
        return self.answers.get(question_id)
    
    def get_answers_by_ids(self, question_ids: List[str]) -> List[AnsweredQuestion]:
        """
        Get multiple answered questions by IDs
        
        Args:
            question_ids: List of question IDs
            
        Returns:
            List of AnsweredQuestion objects (skips missing IDs)
        """
        return [
            self.answers[qid] 
            for qid in question_ids 
            if qid in self.answers
        ]
    
    def get_answers_in_range(self, start_id: str, end_id: str) -> List[AnsweredQuestion]:
        """
        Get all answered questions in a range (e.g., Q1-Q7)
        
        Args:
            start_id: Starting question ID (e.g., "1")
            end_id: Ending question ID (e.g., "7")
            
        Returns:
            List of AnsweredQuestion objects in range
        """
        try:
            start_num = int(start_id)
            end_num = int(end_id)
        except ValueError:
            return []
        
        result = []
        for qid, answered in self.answers.items():
            # Extract base number from question_id (e.g., "7.2" → 7)
            try:
                base_num = int(qid.split('.')[0])
                if start_num <= base_num <= end_num:
                    result.append(answered)
            except (ValueError, IndexError):
                continue
        
        # Sort by question ID
        result.sort(key=lambda x: self._sort_key(x.question_id))
        return result
    
    def get_all_answers(self) -> List[AnsweredQuestion]:
        """
        Get all answered questions in current section
        
        Returns:
            List of all AnsweredQuestion objects, sorted by ID
        """
        result = list(self.answers.values())
        result.sort(key=lambda x: self._sort_key(x.question_id))
        return result
    
    def clear(self):
        """Clear all memory"""
        self.answers.clear()
        self.current_section = None
    
    @staticmethod
    def _sort_key(question_id: str) -> tuple:
        """
        Generate sort key for question IDs
        
        Examples:
            "1" → (1,)
            "7" → (7,)
            "7.2" → (7, 2)
            "7.2.1" → (7, 2, 1)
        
        Args:
            question_id: Question ID string
            
        Returns:
            Tuple of integers for sorting
        """
        try:
            return tuple(int(x) for x in question_id.split('.'))
        except ValueError:
            return (float('inf'),)  # Put unparseable IDs at end
