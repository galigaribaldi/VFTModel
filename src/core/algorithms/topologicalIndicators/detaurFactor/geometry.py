"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Traductor espacial para generar coordenadas de rutas teóricas y topológicas.
@route: src/core/algorithms/topologicalIndicators/detaurFactor/geometry.py
"""

import networkx as nx

def format_network_geometry(G: nx.DiGraph, path: list) -> list:
    """Convierte el path de Dijkstra en una lista de puntos con coordenadas exactas."""
    puntos = []
    for i, n in enumerate(path):
        attr = G.nodes[n]
        lon, lat = attr['pos']
        puntos.append({
            "orden": i,
            "id": n,
            "nombre": attr.get('nombre', 'Trazo de red'),
            "sistema": attr.get('sistema', 'Transbordo'),
            "tipo": attr.get('tipo', 'N/A'),
            "lat": lat,
            "lon": lon
        })
    return puntos

def format_imaginary_geometry(coords_origen: tuple, coords_destino: tuple) -> list:
    """Genera la línea recta Haversine."""
    lon_o, lat_o = coords_origen
    lon_d, lat_d = coords_destino
    return [
        {"lat": lat_o, "lon": lon_o},
        {"lat": lat_d, "lon": lon_d}
    ]