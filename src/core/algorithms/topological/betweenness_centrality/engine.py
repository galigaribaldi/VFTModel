"""
@author: Hernán Galileo Cabrera Garibaldi
@description:   Motor de cálculo para Centralidad de Intermediación (B).
                Funciones puras sin estado - reciben el subgrafo, retornan datos.
@phase: 3
@route: src/core/algorithms/topological/betweenness_centrality/engine.py
@date: 2026-07-05
"""
import networkx as nx


def compute_betweenness(G_scc: nx.DiGraph, normalized: bool = True) -> dict:
    """
    Calcula B(v) = Σ σ_st(v) / σ_st para todos los nodos.
    Usa el atributo 'weight' (impedancia en minutos).
    Retorna dict {node_id: float} con valores normalizados.
    """
    return nx.betweenness_centrality(G_scc, weight='weight', normalized=normalized)
