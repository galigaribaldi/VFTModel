"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Motor matemático puro para cálculos topológicos y trigonométricos del Factor de Desviación.
@route: src/core/algorithms/topologicalIndicators/detaurFactor/engine.py
"""

import networkx as nx
from src.core.models.impedance import VFTImpedanceModel

def get_closest_node_and_walking_distance(G: nx.DiGraph, punto):
    """
    Encuentra el nodo más cercano a una coordenada y devuelve la distancia a pie.
    Retorna: nodo_mas_cercano, attr_mas_cercano, distancia_minima_m, coordenadas_reales
    """
    # Escenario A: El punto ya es un nodo de la red (String)
    if isinstance(punto, str):
        if punto in G.nodes:
            attr = G.nodes[punto]
            return punto, attr, 0.0, attr['pos']
        raise ValueError(f"El nodo {punto} no existe en el grafo.")
    
    # Escenario B: El punto es una coordenada geográfica arbitraria (Tupla)
    if isinstance(punto, tuple) and len(punto) == 2:
        lon_punto, lat_punto = punto
        nodo_mas_cercano = None
        attr_mas_cercano = None
        distancia_minima_m = float('inf')

        for n, attr in G.nodes(data=True):
            if attr.get('tipo') == 'trazo' or 'nombre' not in attr:
                continue
                
            lon_nodo, lat_nodo = attr['pos']
            distancia = VFTImpedanceModel.haversine(lon_punto, lat_punto, lon_nodo, lat_nodo)
            
            if distancia < distancia_minima_m:
                distancia_minima_m = distancia
                nodo_mas_cercano = n
                attr_mas_cercano = attr
                
        return nodo_mas_cercano, attr_mas_cercano, distancia_minima_m, punto
        
    raise ValueError("La entrada debe ser un String (ID Nodo) o una Tupla (lon, lat).")

def calculate_network_distance(G: nx.DiGraph, path: list) -> float:
    """Suma las distancias reales de red iterando sobre los segmentos."""
    dist_red_topologica_m = 0.0
    for i in range(len(path) - 1):
        n_actual_pos = G.nodes[path[i]]['pos']
        n_siguiente_pos = G.nodes[path[i+1]]['pos']
        dist_red_topologica_m += VFTImpedanceModel.haversine(
            n_actual_pos[0], n_actual_pos[1], 
            n_siguiente_pos[0], n_siguiente_pos[1]
        )
    return dist_red_topologica_m