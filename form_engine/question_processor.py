"""
QuestionProcessor - Parse and organize questions
Groups questions by page number, handles parent-subquestion relationships
"""

import json
from typing import Dict, List, Optional
from collections import defaultdict

class QuestionProcessor:
    """
    Process questions.json and organize for batch answering
    - Group by page_number
    - Handle parent-subquestion dependencies
    - Maintain question order
    """
    
    def __init__(self, questions_file: str):
        """
        Initialize with questions JSON file
        
        Args:
            questions_file: Path to questions.json
        """
        self.questions_file = questions_file
        self.all_questions = []
        self.questions_by_page = defaultdict(list)
        self.questions_by_id = {}
        self.parent_subquestion_map = defaultdict(list)
        
        self._load_questions()
    
    def _load_questions(self):  
        """Load and parse questions.json"""  
        try:  
            # Open the file with UTF-8 encoding  
            with open(self.questions_file, 'r', encoding='utf-8') as f:  
                data = json.load(f)  # Load JSON data  
    
            # Handle different JSON formats  
            if isinstance(data, list):  
                # Check if it's a nested list [[{...}]] format  
                if len(data) > 0 and isinstance(data[0], list):  
                    raw_questions = data[0]  # Unwrap nested list  
                else:  
                    raw_questions = data  
            elif isinstance(data, dict):  
                raw_questions = data.get('questions', [])  
            else:  
                raise ValueError(f"Unexpected JSON format: {type(data)}")  
    
            # ✅ Filter out non-dict items (like embedded images)  
            self.all_questions = []  
            skipped_count = 0  
    
            for item in raw_questions:  
                if isinstance(item, dict):  
                    self.all_questions.append(item)  
                else:  
                    skipped_count += 1  
                    # Preview what's being skipped (for debugging)  
                    if isinstance(item, str):  
                        preview = item[:50] + "..." if len(item) > 50 else item  
                    else:  
                        preview = str(type(item))  
                    print(f"  ⚠ Skipped non-question item: {preview}")  
    
            print(f"✓ Loaded {len(self.all_questions)} questions")  
            if skipped_count > 0:  
                print(f"⚠ Skipped {skipped_count} non-question items")  
    
            # Organize by page and ID  
            for q in self.all_questions:  
                page = q.get('page_number')  
                q_id = q.get('question_id')  
                parent_id = q.get('parent_question_id', '')  
    
                if page:  
                    self.questions_by_page[page].append(q)  
                if q_id:  
                    self.questions_by_id[q_id] = q  
                if parent_id:  
                    self.parent_subquestion_map[parent_id].append(q)  
    
        except UnicodeDecodeError as e:  
            # Handle encoding errors gracefully  
            raise RuntimeError(f"Failed to load questions due to encoding error: {str(e)}")  
        except json.JSONDecodeError as e:  
            # Handle JSON parsing errors  
            raise RuntimeError(f"Failed to load questions due to invalid JSON structure: {str(e)}")  
        except Exception as e:  
            # Catch-all for other exceptions  
            raise RuntimeError(f"Failed to load questions: {str(e)}")  


    def get_questions_by_page(self, page_number: int) -> List[Dict]:
        """
        Get all questions for a specific page
        
        Args:
            page_number: Page to retrieve
        
        Returns:
            List of questions on that page
        """
        return self.questions_by_page.get(page_number, [])
    
    def get_page_numbers(self) -> List[int]:
        """Get list of all page numbers with questions"""
        return sorted(self.questions_by_page.keys())
    
    def get_subquestions(self, parent_id: str) -> List[Dict]:
        """
        Get subquestions for a parent question
        
        Args:
            parent_id: Parent question ID
        
        Returns:
            List of subquestions
        """
        return self.parent_subquestion_map.get(parent_id, [])
    
    def get_question(self, question_id: str) -> Optional[Dict]:
        """Get a single question by ID"""
        return self.questions_by_id.get(question_id)
    
    def get_total_questions(self) -> int:
        """Get total number of questions"""
        return len(self.all_questions)
