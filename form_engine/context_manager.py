"""
context_manager.py - Manages context injection for questions

Determines what context (prior answers) should be injected
into the prompt for each question based on question structure
and text analysis.
"""

from typing import Optional, List, Tuple  # Added Tuple here
from .section_memory import SectionMemory, AnsweredQuestion
from .question_analyzer import QuestionAnalyzer


class ContextManager:
    """
    Manages context retrieval and formatting for questions
    """
    
    def __init__(self):
        self.memory = SectionMemory()
        self.analyzer = QuestionAnalyzer()
    
    def update_section(self, section_name: str):
        """
        Update current section (clears memory if changed)
        
        Args:
            section_name: Name of the new section
        """
        self.memory.set_section(section_name)
    
    def add_answer(self, question: dict, answer: str):
        """
        Add an answered question to memory
        
        Args:
            question: Question dict with metadata
            answer: The answer text
        """
        self.memory.add_answer(question, answer)
    
    def get_context(self, question: dict) -> Optional[str]:
        """
        Get context string for a question (if needed)
        
        Args:
            question: Question dict with metadata
            
        Returns:
            Formatted context string or None if no context needed
        """
        question_id = question.get('question_id', '')
        question_text = question.get('main_question', '')
        
        # Rule 1: Sub-questions need parent chain
        if self.analyzer.is_sub_question(question_id):
            parent_ids = self.analyzer.extract_parent_chain(question_id)
            return self._format_parent_context(parent_ids)
        
        # Rule 2: Explicit range references (Q1-7)
        range_match = self.analyzer.parse_question_range(question_text)
        if range_match:
            start_id, end_id = range_match
            return self._format_range_context(start_id, end_id)
        
        # Rule 3: Synthesis questions need full section
        if self.analyzer.is_synthesis_question(question_text):
            return self._format_section_context()
        
        # No context needed
        return None
    
    def should_skip_question(self, question: dict, parent_answer: Optional[str] = None) -> Tuple[bool, str]:
        """
        Determine if question should be skipped based on conditional logic
        
        Args:
            question: Question dict with metadata
            parent_answer: Optional parent answer (for compatibility)
            
        Returns:
            Tuple of (should_skip: bool, reason: str)
        """
        # Check conditional_display field
        conditional = question.get('conditional_display')
        if not conditional:
            return (False, "")
        
        parent_id = conditional.get('parent_question_id')
        required_values = conditional.get('parent_response_values', [])
        
        if not parent_id or not required_values:
            return (False, "")
        
        # Get parent answer from memory
        parent_answered = self.memory.get_answer(parent_id)
        
        if not parent_answered:
            # Parent not answered yet - DON'T SKIP (parent might not have context yet)
            # Only skip if we're SURE parent is answered and doesn't match
            return (False, "")
        
        # Check if parent answer matches required values
        parent_ans_lower = parent_answered.answer.lower()
        
        # More flexible matching
        skip = True
        for req_val in required_values:
            if req_val.lower() in parent_ans_lower:
                skip = False
                break
        
        if skip:
            reason = f"Parent Q{parent_id} = '{parent_answered.answer}', needed: {required_values}"
            return (True, reason)
        
        return (False, "")

    def _format_parent_context(self, parent_ids: List[str]) -> Optional[str]:
        """
        Format parent question context
        
        Args:
            parent_ids: List of parent question IDs
            
        Returns:
            Formatted context string or None if no parents found
        """
        parents = self.memory.get_answers_by_ids(parent_ids)
        
        if not parents:
            return None
        
        context_parts = ["Previous questions in this chain:"]
        for p in parents:
            context_parts.append(f"- Q{p.question_id}: \"{p.question_text}\" → Answer: \"{p.answer}\"")
        
        return "\n".join(context_parts)
    
    def _format_range_context(self, start_id: str, end_id: str) -> Optional[str]:
        """
        Format range context (Q1-7)
        
        Args:
            start_id: Starting question ID
            end_id: Ending question ID
            
        Returns:
            Formatted context string or None if no answers in range
        """
        answers = self.memory.get_answers_in_range(start_id, end_id)
        
        if not answers:
            return None
        
        context_parts = [f"Previous answers from Q{start_id} to Q{end_id}:"]
        for a in answers:
            context_parts.append(f"- Q{a.question_id}: \"{a.question_text}\" → Answer: \"{a.answer}\"")
        
        return "\n".join(context_parts)
    
    def _format_section_context(self) -> Optional[str]:
        """
        Format full section context
        
        Returns:
            Formatted context string or None if no answers in section
        """
        answers = self.memory.get_all_answers()
        
        if not answers:
            return None
        
        context_parts = ["Previous answers in this section:"]
        for a in answers:
            context_parts.append(f"- Q{a.question_id}: \"{a.question_text}\" → Answer: \"{a.answer}\"")
        
        return "\n".join(context_parts)
    
    def clear(self):
        """Clear all memory"""
        self.memory.clear()
