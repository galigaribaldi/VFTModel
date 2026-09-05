"""
@author: Hernán Galileo Cabrera Garibaldi
@description:   Motor de cálculo para Tiempo Promedio de Viaje (T).
                Funciones puras sin estado - reciben el subgrafo, retornan datos.
@phase: 3
@route: src/core/algorithms/topological/average_travel_time/engine.py
@date: 2026-07-05
"""
import networkx as nx


def compute_average_travel_time(G_scc: nx.DiGraph) -> float:
    """
    Calcula T = 1/(N*(N-1)) * Σ t(i,j) para todos los pares de nodos.
    Usa el atributo 'weight' (impedancia en minutos).
    Retorna T en minutos.
    """
    return nx.average_shortest_path_length(G_scc, weight='weight')
