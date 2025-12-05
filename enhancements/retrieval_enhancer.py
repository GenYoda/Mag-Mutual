"""
Retrieval Enhancement: Distance-based filtering
Filters retrieved chunks based on similarity distance threshold
"""

from typing import List, Dict


def filter_by_distance(results: List[Dict], 
                       max_distance: float = 1.5, 
                       min_chunks: int = 3) -> List[Dict]:

    
    if not results:
        return []
    
    # Sort by distance (most similar first)
    sorted_results = sorted(results, key=lambda x: x.get('distance', float('inf')))
    
    # Filter by distance threshold
    filtered = [r for r in sorted_results if r.get('distance', float('inf')) <= max_distance]
    
    # Ensure minimum number of chunks
    if len(filtered) < min_chunks:
        # If we don't have enough within threshold, take the best min_chunks
        filtered = sorted_results[:min_chunks]
        print(f"  ⚠ Only {len([r for r in sorted_results if r.get('distance', float('inf')) <= max_distance])} chunks within distance {max_distance}")
        print(f"    Returning top {min_chunks} chunks anyway")
    else:
        print(f"  ✓ Filtered to {len(filtered)} chunks within distance {max_distance}")
    
    return filtered


def adaptive_distance_filter(results: List[Dict], 
                             min_chunks: int = 3,
                             max_chunks: int = 7) -> List[Dict]:

    
    if not results or len(results) <= min_chunks:
        return results
    
    # Sort by distance
    sorted_results = sorted(results, key=lambda x: x.get('distance', float('inf')))
    distances = [r.get('distance', float('inf')) for r in sorted_results]
    
    # Find the biggest jump in distance (elbow point)
    max_gap = 0
    best_cutoff = min_chunks
    
    for i in range(min_chunks - 1, min(len(distances) - 1, max_chunks)):
        gap = distances[i + 1] - distances[i]
        if gap > max_gap:
            max_gap = gap
            best_cutoff = i + 1
    
    # Take chunks up to the cutoff
    filtered = sorted_results[:best_cutoff]
    
    print(f"  ✓ Adaptive filter: selected {len(filtered)} chunks (distance cutoff: {distances[best_cutoff-1]:.3f})")
    
    return filtered


def get_distance_stats(results: List[Dict]) -> Dict:

    if not results:
        return {}
    
    distances = [r.get('distance', float('inf')) for r in results]
    
    return {
        'min': min(distances),
        'max': max(distances),
        'mean': sum(distances) / len(distances),
        'median': sorted(distances)[len(distances) // 2],
        'count': len(distances)
    }
