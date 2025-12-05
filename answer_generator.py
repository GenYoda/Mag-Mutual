"""
form_filler.py - Main orchestrator for batch form filling
"""

import json
import time
from pathlib import Path
from typing import List, Dict
import sys
import config
from form_engine import ChatbotAdapter, QuestionProcessor, ParallelProcessor, AnswerFormatter
from utils import FormFillerLogger, QuestionValidator, AnswerValidator


class FormFiller:
    """
    Main orchestrator for form filling pipeline
    Coordinates all modules: adapter, processor, formatter, parallelization
    """
    
    def __init__(self, questions_file: str, output_dir: str = None):
        """
        Initialize form filler
        
        Args:
            questions_file: Path to questions.json
            output_dir: Output directory for answers.json (default: forms/answers/)
        """
        self.questions_file = questions_file
        self.output_dir = output_dir or config.ANSWERS_DIR
        
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        self.logger = FormFillerLogger()
        self.chatbot_adapter = None
        self.question_processor = None
        self.parallel_processor = None
    
    def run(self) -> str:
        """
        Execute complete form filling pipeline
        
        Returns:
            Path to answers file if successful, raises exception otherwise
        """
        try:
            print(f"\n{'='*70}")
            print(f"🚀 MEDICAL RAG FORM FILLER")
            print(f"{'='*70}")
            
            # Step 1: Load questions
            print(f"\n📋 Step 1: Loading Questions")
            self.question_processor = QuestionProcessor(self.questions_file)
            total_questions = self.question_processor.get_total_questions()
            print(f"✓ Loaded {total_questions} questions from {self.questions_file}")
            
            # Step 2: Initialize chatbot
            print(f"\n🤖 Step 2: Initializing RAG Chatbot")
            self.chatbot_adapter = ChatbotAdapter(kb_path=config.KB_PATH)
            print(f"✓ Chatbot ready with {len(self.question_processor.get_page_numbers())} pages")
            
            # Step 3: Process all pages
            print(f"\n⚙️ Step 3: Processing Questions")
            self.parallel_processor = ParallelProcessor(self.chatbot_adapter)
            answers = self.parallel_processor.process_all_pages(self.question_processor)
            
            # Step 4: Save results
            print(f"\n💾 Step 4: Saving Results")
            output_file = self._save_answers(answers)
            print(f"✓ Answers saved to {output_file}")
            
            # ✅ Return the file path instead of True
            return output_file
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise the exception instead of returning False
    
    def _save_answers(self, answers: List[Dict]) -> str:
        """
        Save answers to JSON file with cleaning
        
        Args:
            answers: List of answered questions
        
        Returns:
            Path to output file
        """
        from datetime import datetime
        
        # Build output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(self.output_dir) / f"answers_{timestamp}.json"
        
        # Clean all answers using AnswerFormatter
        cleaned_answers = []
        
        for answer_item in answers:
            # Make a copy to avoid modifying original
            cleaned_item = {
                'section_name': answer_item.get('section_name'),
                'question_id': answer_item.get('question_id'),
                'main_question': answer_item.get('main_question'),
                'question_type': answer_item.get('question_type'),
                'answer': answer_item.get('answer'),
                'raw_answer': answer_item.get('raw_answer'),
                'confidence': answer_item.get('confidence'),
                'page_number': answer_item.get('page_number'),
                'sources': answer_item.get('sources', []),
                'used_context': answer_item.get('used_context', False)
            }
            
            # Clean the answer field if it exists (skip for rating types which return dict/int)
            if 'answer' in cleaned_item and cleaned_item['answer'] != 'SKIPPED':
                question_type = cleaned_item.get('question_type', '')
                
                # Skip cleaning for rating questions (they return dict or int, not string)
                if question_type not in ['rating_scale_1_to_9', 'rating_scale_1_to_5']:
                    main_question = cleaned_item.get('main_question', '')
                    cleaned_item['answer'] = AnswerFormatter.clean_answer(
                        cleaned_item['answer'],
                        main_question
                    )
                # For rating types, answer is already formatted correctly (dict or int)
            
            cleaned_answers.append(cleaned_item)
        
        # Calculate statistics
        total_questions = len(cleaned_answers)
        answered = [a for a in cleaned_answers if a.get('answer') not in ['SKIPPED', 'NOT_FOUND']]
        skipped = [a for a in cleaned_answers if a.get('answer') == 'SKIPPED']
        not_found = [a for a in cleaned_answers if a.get('answer') == 'NOT_FOUND']
        total_answered = len(answered)
        total_skipped = len(skipped) + len(not_found)
        
        # Prepare output
        output_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_questions': total_questions,
                'total_answered': total_answered,
                'total_skipped': total_skipped,
                'config': {
                    'enable_query_enhancement': config.ENABLE_QUERY_ENHANCEMENT,
                    'enable_distance_filter': config.ENABLE_DISTANCE_FILTER,
                    'enable_reranking': config.ENABLE_RERANKING,
                    'enable_context_injection': config.ENABLE_CONTEXT_INJECTION,
                    'enable_parallel': config.ENABLE_PARALLEL,
                    'max_workers': config.MAX_WORKERS
                }
            },
            'answers': cleaned_answers  # Use cleaned answers
        }
        
        # Save with UTF-8 encoding and ensure_ascii=False for proper unicode handling
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        return str(output_file)


def get_questions_file():
    """
    Get questions file from CLI or auto-detect from folder
    """
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    # Auto-detect latest file from forms/questions/
    questions_dir = Path(config.QUESTIONS_DIR)
    json_files = list(questions_dir.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {questions_dir}")
        sys.exit(1)
    
    # Sort by modification time (newest first)
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"📋 Auto-detected: {latest_file.name}")
    return str(latest_file)


if __name__ == "__main__":
    # Get questions file
    questions_file = get_questions_file()
    
    # Run form filler
    filler = FormFiller(questions_file)
    success = filler.run()
    
    sys.exit(0 if success else 1)
