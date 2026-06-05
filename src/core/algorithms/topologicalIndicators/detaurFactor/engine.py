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
    """
    Suma la distancia real del trazo entre estaciones consecutivas del path.

    Usa distancia_segmento_m de la arista, que el graph_builder acumuló
    vértice a vértice siguiendo el MultiLineString completo (curvas, esquinas,
    diagonales). Para CC y RTP, que siguen vialidades urbanas sinuosas, este
    valor puede ser hasta un 40% mayor que la cuerda directa entre paradas.

    Fallback a haversine solo si la arista no tiene el atributo (caso defensivo).
    """
    dist_red_topologica_m = 0.0
    for i in range(len(path) - 1):
        edge_data = G[path[i]][path[i + 1]]
        segmento = edge_data.get('distancia_segmento_m')
        if segmento is None:
            n_pos  = G.nodes[path[i]]['pos']
            n1_pos = G.nodes[path[i + 1]]['pos']
            segmento = VFTImpedanceModel.haversine(
                n_pos[0], n_pos[1], n1_pos[0], n1_pos[1]
            )
        dist_red_topologica_m += segmento
    return dist_red_topologica_m