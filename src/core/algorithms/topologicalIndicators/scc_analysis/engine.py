"""
@author: Hernán Galileo Cabrera Garibaldi
@description:   Motor de Cálculo para componentes fuertemente conexas (SCC).
                Funciones puras sin estado - reciben el grafo, retornan datos
@route: src/core/algorithms/topologicalIndicators/scc_analysis/engine.py
@date: 2026-07-04
"""
import networkx as nx

def compute_sorted_components(G: nx.DiGraph) -> list:
    """
    Calcula todos los SCC del grafo usando Tarjan (O(V+E)).
    Retorna lista de sets de nodos, ordenado de mayor a menor.
    """
    return sorted(
        nx.strongly_connected_components(G),
        key=len,
        reverse=True
    )
    
def extract_giant_component(G: nx.DiGraph, components: list) -> nx.DiGraph:
    """
    Retorna una copia independiente del subgrado inducido por el componente gigante.
    La copia permite que Fase 3 modifique el subgrafo sin afectar el grafo principal.
    """
    if not components:
        return nx.DiGraph()
    giant_nodes = components[0]
    return G.subgraph(giant_nodes).copy()

def compute_giant_metrics(G: nx.DiGraph, giant_nodes: set, total_nodes: int) -> dict:
    """
    Calcula las métricas básicas de la componente gigante.
    """
    giant_subgraph = G.subgraph(giant_nodes)
    pct = (len(giant_nodes)/total_nodes*100) if total_nodes > 0 else 0.0
    return {
        "nodes": len(giant_nodes),
        "edges":giant_subgraph.number_of_edges(),
        "pct_of_total_nodes":round(pct, 2)
    }
    