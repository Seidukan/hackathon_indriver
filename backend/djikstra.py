import heapq
from collections import namedtuple
import math
import logging

logger = logging.getLogger(__name__)

Edge = namedtuple('Edge', ['U', 'V', 'K', 'C'])

def get_shortest_path(from_node, to_node, edges_df):
    logger.debug(f"Finding shortest path from node {from_node} to {to_node}")
    # Convert DataFrame edges to Edge objects
    edges = []
    for (u, v, k), row in edges_df.iterrows():
        edges.append(Edge(U=u, V=v, K=k, C=row['edge_cost']))
    logger.debug(f"Converted {len(edges)} edges from DataFrame")
    
    # Build adjacency list
    graph = {}
    for e in edges:
        if e.U not in graph:
            graph[e.U] = []
        graph[e.U].append(e)
    
    # Initialize distances and previous edges
    dist = {}
    prev = {}
    for u in graph:
        dist[u] = math.inf
    dist[from_node] = 0
    
    # Priority queue (min-heap)
    pq = []
    heapq.heappush(pq, (0, from_node))
    
    while pq:
        priority, u = heapq.heappop(pq)
        if u == to_node:
            break
        if priority != dist[u]:
            continue  # Skip outdated entries
        for e in graph.get(u, []):
            v = e.V
            alt = dist[u] + e.C
            if alt < dist.get(v, math.inf):
                dist[v] = alt
                prev[v] = e
                heapq.heappush(pq, (alt, v))
    
    # Reconstruct path
    path = []
    at = to_node
    while at != from_node:
        if at not in prev:
            return None  # No path exists
        e = prev[at]
        path.insert(0, e)
        at = e.U
    return path