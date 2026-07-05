"""
@author: Hernán Galileo Cabrera Garibaldi
@description:   Formateadores de diagnóstico para el análisis SCC.
                Traduce datos crudos de componentes en reportes legibles.
@phase: 3
@route: src/core/algorithms/topological/scc_analysis/diagnostics.py
@date: 2026-07-04
"""

import networkx as nx

def format_fragmentation_by_system(G: nx.DiGraph, giant_nodes: set) -> list:
    """
    Para cada sistema de transporte, cuenta nodos dentro vs fuera
    de la componente gigante. Solo considera estaciones (excluye trazos)
    """
    systems = {}
    for node, attr in G.nodes(data=True):
        if attr.get("tipo") == "trazo":
            continue
        sistema = attr.get("sistema", "desconocido")
        if sistema not in systems:
            systems[sistema] = {"in_giant": 0, "outside":0}
        if node in giant_nodes:
            systems[sistema]["in_giant"] += 1
        else:
            systems[sistema]["outside"] += 1
    result = []
    for sistema, counts in sorted(systems.items()):
        total = counts["in_giant"] + counts["outside"]
        result.append({
            "sistema": sistema,
            "nodes_in_giant": counts["in_giant"],
            "nodes_outside": counts["outside"],
            "pct_in_giant": round(counts["in_giant"] / total * 100, 2) if total > 0 else 0.0
        })
    return result

def format_isolated_components(G: nx.DiGraph, components: list, max_components: int = 10) -> list:
    """
    Retorna información resumida de las componentes no-gigantes más grandes.
    Útil para diagnosticar qué partes de la red están desconectadas.
    """
    # Saltar la primera (gigante)
    non_giant = components[1:max_components + 1]
    sample = []
    for component in non_giant:
        station_names = []
        systems_present = set()
        for node in component:
            attr = G.nodes[node]
            if attr.get("tipo") == "trazo":
                continue
            systems_present.add(attr.get("sistema", "desconocido"))
            if len(station_names) < 5:
                station_names.append(attr.get("nombre", "sin_nombre"))
        sample.append({
            "size": len(component),
            "sample_stations": station_names,
            "systems_present": sorted(systems_present)
            })
    return sample                                 