"""
Query Enhancement Module
Expands user queries with synonyms and related terms for better retrieval
"""

from typing import List, Optional
import os


def enhance_query(query: str, 
                  openai_client,
                  method: str = 'keywords') -> str:
    """
    Enhance user query by adding relevant keywords and synonyms
    
    This improves retrieval by expanding the semantic search space.
    Particularly useful for medical/technical queries.
    
    Args:
        query: Original user query
        openai_client: Azure OpenAI client instance
        method: Enhancement method
               - 'keywords': Add relevant keywords (fast, recommended)
               - 'rephrase': Generate alternative phrasings (slower)
               - 'expand': Both keywords and rephrase (slowest, most thorough)
    
    Returns:
        Enhanced query string
    
    Example:
        >>> original = "What medication was prescribed?"
        >>> enhanced = enhance_query(original, client)
        >>> print(enhanced)
        "What medication was prescribed? drug treatment prescription medicine therapy pharmaceutical"
    """
    
    if not query or len(query.strip()) < 3:
        return query
    
    print(f"  Enhancing query with method '{method}'...")
    
    if method == 'keywords':
        return _enhance_with_keywords(query, openai_client)
    elif method == 'rephrase':
        return _enhance_with_rephrase(query, openai_client)
    elif method == 'expand':
        keywords_enhanced = _enhance_with_keywords(query, openai_client)
        return _enhance_with_rephrase(keywords_enhanced, openai_client)
    else:
        return query


def _enhance_with_keywords(query: str, client) -> str:
    """
    Add relevant keywords and synonyms to query
    """
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    
    prompt = f"""Given this medical/technical question, generate 5-7 relevant keywords, synonyms, or related terms that would help find the answer in documents.

Question: {query}

Instructions:
- Focus on medical/technical terminology
- Include synonyms and related concepts
- Keep it concise (single words or short phrases)
- Separate with spaces

Keywords:"""
    
    try:
        response = client.chat.completions.create(
            model=chat_deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100
        )
        
        keywords = response.choices[0].message.content.strip()
        # Clean up keywords (remove commas, newlines, etc.)
        keywords = keywords.replace(',', ' ').replace('\n', ' ')
        
        enhanced = f"{query} {keywords}"
        print(f"    Added keywords: {keywords[:60]}...")
        
        return enhanced
        
    except Exception as e:
        print(f"    ⚠ Query enhancement failed: {str(e)}")
        return query


def _enhance_with_rephrase(query: str, client) -> str:
    """
    Generate alternative phrasings of the query
    """
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    
    prompt = f"""Rephrase this question in 2-3 different ways that capture the same meaning but use different words.

Original question: {query}

Instructions:
- Keep the same intent
- Use different terminology
- Be concise
- Separate rephrases with | symbol

Rephrased versions:"""
    
    try:
        response = client.chat.completions.create(
            model=chat_deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=150
        )
        
        rephrases = response.choices[0].message.content.strip()
        # Combine original with rephrases
        enhanced = f"{query} {rephrases.replace('|', ' ')}"
        print(f"    Generated rephrases")
        
        return enhanced
        
    except Exception as e:
        print(f"    ⚠ Query rephrasing failed: {str(e)}")
        return query


def enhance_query_simple(query: str, domain: str = 'medical') -> str:
    """
    Simple query enhancement without LLM (fast, rule-based)
    
    Adds common synonyms and related terms based on domain.
    
    Args:
        query: Original query
        domain: Domain for synonym expansion ('medical', 'technical', 'general')
    
    Returns:
        Enhanced query
    """
    
    if domain == 'medical':
        # Medical synonyms
        replacements = {
            'medication': 'medication drug medicine prescription pharmaceutical',
            'drug': 'drug medication medicine pharmaceutical',
            'treatment': 'treatment therapy intervention protocol',
            'diagnosis': 'diagnosis condition disease disorder',
            'test': 'test exam examination lab study',
            'doctor': 'doctor physician provider clinician',
            'patient': 'patient subject case individual',
            'symptoms': 'symptoms signs presentation manifestation',
            'prescribed': 'prescribed given administered ordered',
        }
    else:
        replacements = {}
    
    enhanced = query
    for term, expansion in replacements.items():
        if term.lower() in query.lower():
            enhanced += f" {expansion}"
    
    if enhanced != query:
        print(f"    Added domain-specific terms")
    
    return enhanced


def get_query_variations(query: str, client, max_variations: int = 3) -> List[str]:
    """
    Generate multiple query variations for parallel retrieval
    
    Returns list of query variations that can be used for multiple
    retrievals, then combined.
    
    Args:
        query: Original query
        client: OpenAI client
        max_variations: Maximum number of variations to generate
    
    Returns:
        List of query variations including original
    """
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    
    prompt = f"""Generate {max_variations} alternative ways to ask this question, using different terminology.

Original: {query}

Alternatives (one per line):"""
    
    try:
        response = client.chat.completions.create(
            model=chat_deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=200
        )
        
        variations_text = response.choices[0].message.content.strip()
        variations = [v.strip() for v in variations_text.split('\n') if v.strip()]
        
        # Add original at the start
        all_variations = [query] + variations[:max_variations]
        
        print(f"    Generated {len(all_variations)-1} query variations")
        
        return all_variations
        
    except Exception as e:
        print(f"    ⚠ Variation generation failed: {str(e)}")
        return [query]
def enhance_checkbox_query(question: str, response_options: list) -> str:
    if not response_options:
        return question
    
    options_str = '\n'.join([f"  - {opt}" for opt in response_options])
    enhanced = f"{question}\n\nOptions to select from:\n{options_str}"
    
    return enhanced

def enhance_rating_1_to_9_query(question_text: str, response_options: list, aspect: str) -> str:
    """
    Enhance query for rating_scale_1_to_9 questions (dual rating)
    
    Args:
        question_text: The original question text
        response_options: List of 9 rating options (e.g., ["1. No physical injury...", "2. Very slight..."])
        aspect: Either "alleged" or "suffered"
    
    Returns:
        Enhanced query with structured rating scale and focused instructions
    """
    
    # Format the rating scale clearly
    rating_scale = "\n".join([f"{option}" for option in response_options])
    
    # Determine focus based on aspect
    if aspect.lower() == "alleged":
        focus_instruction = """
YOUR TASK:
Based on the medical records and evidence provided, determine which rating level (1-9) best describes the DEGREE OF INJURY ALLEGED by the plaintiff/claimant.

Focus SPECIFICALLY on what injury was CLAIMED or ALLEGED, not what actually occurred.
This is what the plaintiff states they suffered according to their complaint or claim.
"""
    else:  # "suffered"
        focus_instruction = """
YOUR TASK:
Based on the medical records and evidence provided, determine which rating level (1-9) best describes the DEGREE OF INJURY ACTUALLY SUFFERED by the patient.

Focus SPECIFICALLY on what injury ACTUALLY OCCURRED based on medical documentation and evidence.
This is the objective medical outcome, not the claim.
"""
    
    enhanced_query = f"""
ORIGINAL QUESTION:
{question_text}

RATING SCALE REFERENCE (1-9):
{rating_scale}

{focus_instruction}

REQUIRED RESPONSE FORMAT:
RATING: [number 1-9]. [Full text of the selected rating option]

EXPLANATION: [Detailed reasoning based on medical evidence, including specific references to documents, findings, and clinical outcomes. Cite specific sources.]

IMPORTANT:
- You MUST select exactly ONE rating from 1-9
- Include the COMPLETE text of the rating option you select
- Provide comprehensive medical reasoning with document references
- Be objective and base your assessment only on documented medical evidence
"""
    
    return enhanced_query.strip()

def enhance_rating_1_to_5_query(question_text: str, response_options: list) -> str:
    """
    Enhance query for rating_scale_1_to_5 questions (single rating)
    
    Args:
        question_text: The original question text
        response_options: List of 5 rating options (e.g., ["1. No departure...", "2. Minimal departure..."])
    
    Returns:
        Enhanced query with structured rating scale and clear instructions
    """
    
    # Format the rating scale clearly
    rating_scale = "\n".join([f"{option}" for option in response_options])
    
    enhanced_query = f"""
ORIGINAL QUESTION:
{question_text}

RATING SCALE REFERENCE (1-5):
{rating_scale}

YOUR TASK:
Based on the medical records and evidence provided, carefully evaluate and select the most appropriate rating level (1-5) that accurately answers the question above.

REQUIRED RESPONSE FORMAT:
RATING: [number 1-5]. [Full text of the selected rating option]

EXPLANATION: [Detailed reasoning based on medical evidence, including specific references to documents, clinical findings, and applicable standards. Cite specific sources.]

IMPORTANT:
- You MUST select exactly ONE rating from 1-5
- Include the COMPLETE text of the rating option you select
- Provide comprehensive reasoning with document references
- Base your assessment only on documented evidence and established medical/legal standards
- Be objective and avoid hindsight bias
"""
    
    return enhanced_query.strip()

