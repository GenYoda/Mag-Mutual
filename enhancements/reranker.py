"""
Reranking Module: Improve retrieval relevance
Uses LLM to score and rerank retrieved chunks for better quality
"""

from typing import List, Dict
import os


def rerank_chunks(query: str,
                  results: List[Dict],
                  openai_client,
                  top_k: int = 5,
                  method: str = 'simple',
                  debug: bool = False) -> List[Dict]:  # NEW: debug parameter
    """
    Rerank retrieved chunks using LLM-based relevance scoring
    
    Args:
        ...
        debug: If True, print detailed reranking information
    """
    
    if method == 'simple':
        reranked = _rerank_simple(query, results, openai_client, top_k)
    elif method == 'detailed':
        reranked = _rerank_detailed(query, results, openai_client, top_k)
    elif method == 'pairwise':
        reranked = _rerank_pairwise(query, results, openai_client, top_k)
    else:
        reranked = _rerank_simple(query, results, openai_client, top_k)
    
    # NEW: Debug output
    if debug:
        print("\n" + "="*70)
        print(f"RERANKING DEBUG ({method.upper()} method)")
        print("="*70)
        print(f"Query: {query}")
        print(f"Method: {method}")
        print(f"Input chunks: {len(results)}")
        print(f"Output chunks: {len(reranked)}")
        print("\nReranked Results:")
        
        for i, result in enumerate(reranked, 1):
            score = result.get('relevance_score', 0)
            doc = result['metadata']['source']
            distance = result.get('distance', 0)
            
            print(f"\n[{i}] Score: {score:.1f}/10, Distance: {distance:.3f}")
            print(f"    Document: {doc}")
            
            if method == 'detailed' and 'rerank_reason' in result:
                print(f"    Reason: {result['rerank_reason']}")
            
            if method == 'pairwise' and 'pairwise_wins' in result:
                print(f"    Wins: {result['pairwise_wins']}")
            
            print(f"    Text: {result['chunk'][:150]}...")
        
        print("="*70 + "\n")
    
    return reranked

    




    
    if not results or len(results) <= 1:
        return results
    
    print(f"  Reranking {len(results)} chunks using '{method}' method...")
    
    if method == 'simple':
        return _rerank_simple(query, results, openai_client, top_k)
    elif method == 'detailed':
        return _rerank_detailed(query, results, openai_client, top_k)
    elif method == 'pairwise':
        return _rerank_pairwise(query, results, openai_client, top_k)
    else:
        print(f"  ⚠ Unknown method '{method}', using 'simple'")
        return _rerank_simple(query, results, openai_client, top_k)


def _rerank_simple(query: str, results: List[Dict], client, top_k: int) -> List[Dict]:
    """
    Simple reranking: score each chunk individually (fast)
    """
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    
    scored_results = []
    
    for idx, result in enumerate(results):
        chunk_text = result['chunk'][:1000]  # Limit to 1000 chars for speed
        
        prompt = f"""Rate the relevance of this text chunk to the question on a scale of 0-10.
Only respond with a number.

Question: {query}

Text chunk:
{chunk_text}

Relevance score (0-10):"""
        
        try:
            response = client.chat.completions.create(
                model=chat_deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5
            )
            
            score_text = response.choices[0].message.content.strip()
            # Extract number from response
            score = float(''.join(c for c in score_text if c.isdigit() or c == '.'))
            score = max(0, min(10, score))  # Clamp to 0-10
            
        except Exception as e:
            # Fallback: use inverse of original distance
            original_distance = result.get('distance', 1.0)
            score = 10 / (1 + original_distance)
            print(f"    ⚠ Scoring failed for chunk {idx+1}, using distance-based score: {score:.2f}")
        
        result['relevance_score'] = score
        scored_results.append(result)
    
    # Sort by relevance score (highest first)
    scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    print(f"  ✓ Reranked: top score={scored_results[0]['relevance_score']:.1f}, "
          f"bottom score={scored_results[-1]['relevance_score']:.1f}")
    
    return scored_results[:top_k]


def _rerank_detailed(query: str, results: List[Dict], client, top_k: int) -> List[Dict]:
    """
    Detailed reranking: more thorough analysis (slower, more accurate)
    """
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    
    scored_results = []
    
    for idx, result in enumerate(results):
        chunk_text = result['chunk'][:1500]
        
        prompt = f"""Analyze how well this text chunk answers the question.
Consider:
1. Does it contain the information needed?
2. Is the information directly relevant?
3. Is it complete or partial?

Question: {query}

Text chunk:
{chunk_text}

Provide:
1. Relevance score (0-10)
2. Brief reason

Format: score|reason
Example: 8|Contains diagnosis and treatment details"""
        
        try:
            response = client.chat.completions.create(
                model=chat_deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=100
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse response
            if '|' in response_text:
                score_part, reason = response_text.split('|', 1)
                score = float(''.join(c for c in score_part if c.isdigit() or c == '.'))
                score = max(0, min(10, score))
                result['rerank_reason'] = reason.strip()
            else:
                score = float(''.join(c for c in response_text if c.isdigit() or c == '.'))
                score = max(0, min(10, score))
                result['rerank_reason'] = "No reason provided"
            
        except Exception as e:
            original_distance = result.get('distance', 1.0)
            score = 10 / (1 + original_distance)
            result['rerank_reason'] = f"Scoring failed: {str(e)}"
        
        result['relevance_score'] = score
        scored_results.append(result)
    
    scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    print(f"  ✓ Detailed rerank complete")
    print(f"    Top chunk ({scored_results[0]['relevance_score']:.1f}): {scored_results[0].get('rerank_reason', 'N/A')[:60]}...")
    
    return scored_results[:top_k]


def _rerank_pairwise(query: str, results: List[Dict], client, top_k: int) -> List[Dict]:
    """
    Pairwise reranking: compare chunks against each other (slowest, most accurate)
    Uses tournament-style comparison
    """
    if len(results) <= 2:
        return results[:top_k]
    
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    
    # Create win matrix
    n = len(results)
    wins = [0] * n
    
    # Compare pairs
    comparisons = 0
    max_comparisons = min(n * (n - 1) // 4, 50)  # Limit comparisons
    
    import random
    pairs = [(i, j) for i in range(n) for j in range(i+1, n)]
    random.shuffle(pairs)
    
    for i, j in pairs[:max_comparisons]:
        chunk_a = results[i]['chunk'][:500]
        chunk_b = results[j]['chunk'][:500]
        
        prompt = f"""Which text chunk better answers the question? Respond with A or B.

Question: {query}

Chunk A:
{chunk_a}

Chunk B:
{chunk_b}

Better chunk (A or B):"""
        
        try:
            response = client.chat.completions.create(
                model=chat_deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=3
            )
            
            winner = response.choices[0].message.content.strip().upper()
            
            if 'A' in winner:
                wins[i] += 1
            elif 'B' in winner:
                wins[j] += 1
            
            comparisons += 1
            
        except Exception as e:
            continue
    
    # Assign scores based on wins
    for idx, result in enumerate(results):
        result['relevance_score'] = wins[idx]
    
    results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    print(f"  ✓ Pairwise rerank: {comparisons} comparisons made")
    
    return results[:top_k]


def get_rerank_stats(results: List[Dict]) -> Dict:
    """
    Get statistics about reranking results
    
    Args:
        results: Reranked results with relevance_score
    
    Returns:
        Dictionary with statistics
    """
    if not results or 'relevance_score' not in results[0]:
        return {}
    
    scores = [r['relevance_score'] for r in results]
    
    return {
        'min_score': min(scores),
        'max_score': max(scores),
        'mean_score': sum(scores) / len(scores),
        'score_range': max(scores) - min(scores),
        'count': len(scores)
    }
