"""
@author: Hernán Galileo Cabrera Garibaldi
@description:   Orquestador del indicador B (Centralidad de Intermediación).
                Opera exclusivamente sobre la componente gigante (SCC).
@phase: 3
@route: src/core/algorithms/topological/betweenness_centrality/orchestator.py
@date: 2026-07-05
"""

import networkx as nx
from src.core.utils.logger import vft_logger
from src.core.algorithms.topological.betweenness_centrality.engine import (
    compute_betweenness
)
from src.core.algorithms.topological.betweenness_centrality.diagnostics import (
    format_betweenness_ranking
)


class BetweennessOrchestrator:
    """
    Orquestador del indicador B (Centralidad de Intermediación).
    Calcula la importancia de cada nodo como intermediario en caminos mínimos.

    Prerequisito: subgrafo fuertemente conexo (componente gigante del SCC).
    """

    def __init__(self, G_scc: nx.DiGraph):
        if not isinstance(G_scc, nx.DiGraph):
            raise ValueError("BetweennessOrchestrator requiere un nx.DiGraph (componente gigante).")
        self.G_scc = G_scc

    def analyze(self) -> dict:
        """
        Ejecuta el cálculo de B y retorna reporte con ranking.
        """
        vft_logger.info(
            f"Calculando B (Betweenness Centrality) sobre {self.G_scc.number_of_nodes():,} nodos..."
        )

        bc_dict = compute_betweenness(self.G_scc)
        df_ranking = format_betweenness_ranking(self.G_scc, bc_dict)

        top_5 = df_ranking.head(5)
        if not top_5.empty:
            vft_logger.info(
                f"B (Betweenness): Top nodo = {top_5.iloc[0]['nombre']} "
                f"(B={top_5.iloc[0]['betweenness_centrality']:.4f})"
            )

        return {
            "summary": {
                "total_stations_ranked": len(df_ranking),
                "top_5": top_5.to_dict(orient="records"),
                "reference": {
                    "expected_top_cdmx": ["Pantitlán", "Pino Suárez"],
                    "expected_B_approx": 0.40
                }
            },
            "ranking": df_ranking
        }
