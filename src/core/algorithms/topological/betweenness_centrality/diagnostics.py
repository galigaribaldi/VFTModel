"""
@author: Hernán Galileo Cabrera Garibaldi
@description:   Formateadores de diagnóstico para Centralidad de Intermediación (B).
                Enriquece el diccionario crudo de betweenness en un DataFrame rankeado
                con metadatos de estación.
@phase: 3
@route: src/core/algorithms/topological/betweenness_centrality/diagnostics.py
@date: 2026-07-05
"""

import networkx as nx
import pandas as pd


def format_betweenness_ranking(G_scc: nx.DiGraph, bc_dict: dict) -> pd.DataFrame:
    """
    Transforma el diccionario crudo de betweenness en un DataFrame rankeado
    con metadatos de estación (nombre, sistema, alcaldía, coordenadas).
    Filtra nodos tipo 'trazo' y solo incluye estaciones con nombre.
    """
    rows = []
    for node, bc_value in bc_dict.items():
        attr = G_scc.nodes[node]
        if attr.get('tipo') == 'trazo':
            continue
        if 'nombre' not in attr:
            continue
        pos = attr.get('pos', (0, 0))
        rows.append({
            "node_id": str(node),
            "nombre": attr.get("nombre", "Desconocido"),
            "sistema": attr.get("sistema", "Desconocido"),
            "alcaldia_municipio": attr.get("alcaldia_municipio", "Desconocida"),
            "es_cetram": attr.get("es_cetram", False),
            "lon": pos[0],
            "lat": pos[1],
            "betweenness_centrality": round(bc_value, 6)
        })

    df = pd.DataFrame(rows)
    df.sort_values("betweenness_centrality", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df
