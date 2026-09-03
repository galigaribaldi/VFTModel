"""
@author: Hernán Galileo Cabrera Garibaldi
@description:   Orquestador del indicador T (Tiempo Promedio de Viaje).
                Opera exclusivamente sobre la componente gigante (SCC).
@phase: 3
@route: src/core/algorithms/topological/average_travel_time/orchestator.py
@date: 2026-07-05
"""

import networkx as nx
from src.core.utils.logger import vft_logger
from src.core.algorithms.topological.average_travel_time.engine import (
    compute_average_travel_time
)


class AverageTravelTimeOrchestrator:
    """
    Orquestador del indicador T (Tiempo Promedio de Viaje).
    Calcula el promedio de caminos más cortos ponderados sobre la componente gigante.

    Prerequisito: subgrafo fuertemente conexo (componente gigante del SCC).
    """

    def __init__(self, G_scc: nx.DiGraph):
        if not isinstance(G_scc, nx.DiGraph):
            raise ValueError("AverageTravelTimeOrchestrator requiere un nx.DiGraph (componente gigante).")
        self.G_scc = G_scc

    def analyze(self) -> dict:
        """
        Ejecuta el cálculo de T y retorna el reporte estructurado.
        """
        # Verificar conectividad fuerte
        if not nx.is_strongly_connected(self.G_scc):
            raise ValueError("El subgrafo no es fuertemente conexo. Usar get_giant_component().")

        vft_logger.info(
            f"Calculando T (Tiempo Promedio) sobre {self.G_scc.number_of_nodes():,} nodos... "
            f"Esto puede tardar varios minutos."
        )

        t_minutes = compute_average_travel_time(self.G_scc)

        vft_logger.info(f"T (Tiempo Promedio de Viaje): {t_minutes:.2f} minutos")

        return {
            "T_average_travel_time_minutes": round(t_minutes, 4),
            "graph_info": {
                "nodes": self.G_scc.number_of_nodes(),
                "edges": self.G_scc.number_of_edges(),
                "is_strongly_connected": True
            },
            "reference": {
                "expected_cdmx_approx": 85.0,
                "unit": "minutes"
            }
        }
