"""
parallel_processor.py - Process questions in parallel with context awareness
"""

import time
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .chatbot_adapter import ChatbotAdapter
from .chunk_cache import ChunkCache
from .question_processor import QuestionProcessor
from .answer_formatter import AnswerFormatter
from .context_manager import ContextManager
import config


class ParallelProcessor:
    """
    Process questions in parallel with page-level caching and context awareness
    """

    def __init__(self, chatbot_adapter: ChatbotAdapter):
        self.chatbot = chatbot_adapter
        self.cache = ChunkCache()
        self.context_manager = ContextManager()
        self.max_workers = config.MAX_WORKERS
        self.stats = {
            'total_time': 0,
            'questions_with_context': 0,
            'questions_skipped': 0
        }

    def process_page(self, page_questions: List[Dict], page_index: int, total_pages: int) -> List[Dict]:
        """
        Process all questions on a page with context awareness
        
        Args:
            page_questions: List of questions on this page
            page_index: Current page index
            total_pages: Total number of pages
        
        Returns:
            List of answered questions with results
        """
        if not page_questions:
            return []

        answered = []
        page_num = page_questions[0].get('page_number')

        # Update section context
        section_name = page_questions[0].get('section_name', '')
        if section_name:
            self.context_manager.update_section(section_name)

        # Process each question
        for question in page_questions:
            result = self._answer_question(question)
            answered.append(result)

            # Add to context memory if answered (not SKIPPED and not NOT_FOUND)
            if result.get('answer') not in ['NOT_FOUND', 'SKIPPED']:
                self.context_manager.add_answer(question, result['answer'])

        return answered

    def _answer_question(self, question: Dict) -> Dict:
        """
        Answer a single question with context awareness
        
        Args:
            question: Question dict with metadata
        
        Returns:
            Answer dict with result
        """
        q_id = question.get('question_id', 'UNKNOWN')
        q_text = question.get('main_question', '')
        q_type = question.get('question_type', 'text')
        page_num = question.get('page_number', 0)
        response_options = question.get('response_options', [])
        requires_explanation = question.get('requires_explanation', False)

        # Check if question should be skipped
        should_skip, skip_reason = self.context_manager.should_skip_question(question)
        if should_skip:
            self.stats['questions_skipped'] += 1
            return {
                'section_name': question.get('section_name', ''),
                'question_id': q_id,
                'main_question': q_text,
                'answer': 'SKIPPED',
                'status': 'skipped',
                'skip_reason': skip_reason,
                'page_number': page_num,
                'confidence': 0.0,
                'sources': []
            }

        # Get context if needed
        context = None
        if config.ENABLE_CONTEXT_INJECTION:
            context = self.context_manager.get_context(question)
            if context:
                self.stats['questions_with_context'] += 1

        # # Include response options in query for checkbox_group questions
        # if q_type == 'checkbox_group' and response_options:
        #     from enhancements.query_enhancer import enhance_checkbox_query
        #     enhanced_query = enhance_checkbox_query(q_text, response_options)
        # else:
        #     enhanced_query = q_text

        # # Ask question with context
        # result = self.chatbot.ask(query=enhanced_query, context=context)
                # Include response options in query for checkbox_group questions
        if q_type == 'checkbox_group' and response_options:
            from enhancements.query_enhancer import enhance_checkbox_query
            enhanced_query = enhance_checkbox_query(q_text, response_options)
            # Ask question with context
            result = self.chatbot.ask(query=enhanced_query, context=context)
            answer_text = result.get('answer', 'NOT_FOUND')
            sources = result.get('sources', [])
            
        # ========== NEW: Handle rating_scale_1_to_9 (dual rating) ==========
        elif q_type == 'rating_scale_1_to_9' and response_options:
            from enhancements.query_enhancer import enhance_rating_1_to_9_query
            
            # Call 1: Get rating for "alleged"
            query_alleged = enhance_rating_1_to_9_query(q_text, response_options, aspect="alleged")
            result_alleged = self.chatbot.ask(query=query_alleged, context=context)
            
            # Call 2: Get rating for "suffered"
            query_suffered = enhance_rating_1_to_9_query(q_text, response_options, aspect="suffered")
            result_suffered = self.chatbot.ask(query=query_suffered, context=context)
            
            # Combine results
            answer_text = {
                'alleged': result_alleged.get('answer', 'NOT_FOUND'),
                'suffered': result_suffered.get('answer', 'NOT_FOUND')
            }
            
            # Combine sources from both calls
            sources_alleged = result_alleged.get('sources', [])
            sources_suffered = result_suffered.get('sources', [])
            sources = sources_alleged + sources_suffered
            
        # ========== NEW: Handle rating_scale_1_to_5 (single rating) ==========
        elif q_type == 'rating_scale_1_to_5' and response_options:
            from enhancements.query_enhancer import enhance_rating_1_to_5_query
            enhanced_query = enhance_rating_1_to_5_query(q_text, response_options)
            # Ask question with context
            result = self.chatbot.ask(query=enhanced_query, context=context)
            answer_text = result.get('answer', 'NOT_FOUND')
            sources = result.get('sources', [])
            
        else:
            # Default: no enhancement
            enhanced_query = q_text
            # Ask question with context
            result = self.chatbot.ask(query=enhanced_query, context=context)
            answer_text = result.get('answer', 'NOT_FOUND')
            sources = result.get('sources', [])



        # # Extract answer and sources
        # answer_text = result.get('answer', 'NOT_FOUND')
        # sources = result.get('sources', [])

        # Calculate confidence from sources
        if sources:
            avg_similarity = sum(s.get('similarity', 0.0) for s in sources) / len(sources)
            confidence = min(1.0, avg_similarity / 100.0)
        else:
            confidence = 0.0

        # Format answer based on question type and requires_explanation
        # Format answer based on question type and requires_explanation
        formatted = AnswerFormatter.format_answer(
            answer_text,
            q_type,
            response_options,
            confidence,
            requires_explanation
        )


        
        # Build result with raw answer
        answer_result = {
            'section_name': question.get('section_name', ''),
            'question_id': q_id,
            'main_question': q_text,
            'question_type': q_type,
            'answer': formatted['answer'],
            'raw_answer': answer_text,  # ← NEW: Store raw LLM answer
            'confidence': formatted['confidence'],
            'page_number': page_num,
            'sources': [
                {
                    'file': s.get('metadata', {}).get('source', 'Unknown'),
                    'pages': s.get('metadata', {}).get('page_numbers', []),
                    'similarity': s.get('similarity', 0.0),
                    'chunk_preview': s.get('chunk', '')[:200],
                    'chunk_full': s.get('chunk', '')  # ← Full chunk text
                }
                for s in sources
            ],
            'used_context': context is not None
        }

        # Add explanation if present and required
        if 'explanation' in formatted:
            answer_result['explanation'] = formatted['explanation']

        return answer_result
        
        # Add explanation if present and required
        if 'explanation' in formatted:
            answer_result['explanation'] = formatted['explanation']

        return answer_result

    def process_all_pages(self, question_processor: QuestionProcessor) -> List[Dict]:
        """
        Process all pages in sequence with context awareness
        
        Args:
            question_processor: QuestionProcessor instance
        
        Returns:
            List of all answered questions
        """
        all_results = []
        page_numbers = question_processor.get_page_numbers()
        total_pages = len(page_numbers)

        print(f"\n{'='*70}")
        print(f"🚀 Starting Parallel Processing (Context-Aware)")
        print(f"   Pages: {total_pages} | Questions: {question_processor.get_total_questions()}")
        print(f"   Workers: {self.max_workers}")
        print(f"   Context Injection: {'Enabled' if config.ENABLE_CONTEXT_INJECTION else 'Disabled'}")
        print(f"{'='*70}\n")

        global_start = time.time()
        page_counter = 0
        current_section = None  # Track current section

        # Process pages sequentially to maintain context order
        for page_num in page_numbers:
            page_counter += 1
            page_questions = question_processor.get_questions_by_page(page_num)

            if not page_questions:
                continue

            # Get section for this page
            page_section = page_questions[0].get('section_name', '')

            # Only update section if it changed
            if page_section != current_section:
                print(f"   📂 Section changed: {current_section or 'None'} → {page_section}")
                self.context_manager.update_section(page_section)
                current_section = page_section

            print(f"   [{page_counter}/{total_pages}] Page {page_num}: {len(page_questions)} Q's ({page_section})", end=" ")
            page_start = time.time()

            # Process page
            page_results = self.process_page(page_questions, page_counter, total_pages)
            all_results.extend(page_results)

            elapsed = time.time() - page_start
            print(f"✓ {elapsed:.1f}s")

        total_time = time.time() - global_start
        self.stats['total_time'] = total_time

        # Print final summary
        self._print_summary(all_results, total_time)

        return all_results

    def _print_summary(self, answers: List[Dict], total_time: float):
        """Print execution summary"""
        answered = [a for a in answers if a.get('answer') not in ['NOT_FOUND', 'SKIPPED']]
        not_found = len([a for a in answers if a.get('answer') == 'NOT_FOUND'])
        skipped = len([a for a in answers if a.get('answer') == 'SKIPPED'])

        print(f"\n{'='*70}")
        print(f"✅ Processing Complete")
        print(f"{'='*70}")
        print(f"Total Questions:    {len(answers)}")
        print(f"Answered:          {len(answered)} ({len(answered)/len(answers)*100:.1f}%)")
        print(f"Not Found:         {not_found} ({not_found/len(answers)*100:.1f}%)")
        print(f"Skipped:           {skipped} ({skipped/len(answers)*100:.1f}%)")
        print(f"With Context:      {self.stats['questions_with_context']}")
        print(f"Time Taken:        {total_time:.2f}s")
        print(f"Avg per Q:         {total_time/len(answers):.2f}s")
        print(f"{'='*70}\n")
