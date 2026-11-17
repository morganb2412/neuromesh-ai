"""Deterministic measurements over the current source-backed graph."""
import networkx as nx

from .store import graph as current_graph


def analyze_graph():
    snapshot = current_graph()
    nodes = sorted(snapshot['nodes'], key=lambda row: row['id'])
    edges = sorted(snapshot['edges'], key=lambda row: row['id'])
    graph = nx.Graph()
    graph.add_nodes_from(n['id'] for n in nodes)
    graph.add_edges_from((e['source_id'],e['target_id']) for e in edges)
    # Small bounded power iteration keeps local analysis free of SciPy and stable.
    rank = {n: 1 / len(nodes) for n in graph} if nodes else {}
    if nodes:
        neighbors = {n: list(graph.neighbors(n)) for n in graph}
        for _ in range(100):
            dangling = sum(rank[n] for n in graph if not neighbors[n]) / len(nodes)
            updated = {n: .15 / len(nodes) + .85 * dangling for n in graph}
            for n in graph:
                if neighbors[n]:
                    share = .85 * rank[n] / len(neighbors[n])
                    for target in neighbors[n]:
                        updated[target] += share
            error = sum(abs(updated[n] - rank[n]) for n in graph)
            rank = updated
            if error < 1e-10:
                break
    ordered = sorted(nodes, key=lambda n:(-rank.get(n['id'],0),n['id']))[:10]
    return {'mode':'live','node_count':graph.number_of_nodes(),
            'edge_count':graph.number_of_edges(),'density':nx.density(graph),
            'connected_components':nx.number_connected_components(graph),
            'top_entities':[{'id':n['id'],'label':n['label'],'pagerank':round(rank[n['id']],8)} for n in ordered],
            'method':'PageRank power iteration (damping 0.85), undirected; disconnected nodes retained; sorted IDs ensure deterministic tie order'}
