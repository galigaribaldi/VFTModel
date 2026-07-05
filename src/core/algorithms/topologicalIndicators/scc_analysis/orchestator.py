"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Orquestador del análisis SCC. Gestiona el estado del grafo y ensambla el reporte.
@route: src/core/algorithms/topologicalIndicators/scc_analysis/orchestator.py
@date: 2026-07-04
"""

import networkx as nx
from src.core.utils.logger import vft_logger
from src.core.algorithms.topologicalIndicators.scc_analysis.engine import (
    compute_sorted_components,
    extract_giant_component,
    compute_giant_metrics
)
from src.core.algorithms.topologicalIndicators.scc_analysis.diagnostics import (
    format_fragmentation_by_system,
    format_isolated_components
)


class SCCOrchestrator:
    """
    Orquestador del diagnóstico de Componentes Fuertemente Conexas.
    Determina si el grafo es apto para Fase 3 (T y B).

    Regla: componente gigante > 80% de nodos → apto.
    """

    PHASE_3_THRESHOLD = 80.0

    def __init__(self, G: nx.DiGraph):
        if not isinstance(G, nx.DiGraph):
            raise ValueError("SCCOrchestrator requiere un objeto networkx.DiGraph.")
        self.G = G
        self._components = None
        self._giant_nodes = None

    def _ensure_computed(self):
        """Calcula SCC una sola vez (cache interno)."""
        if self._components is not None:
            return
        self._components = compute_sorted_components(self.G)
        self._giant_nodes = self._components[0] if self._components else set()

    def analyze(self) -> dict:
        """
        Ejecuta el diagnóstico completo y retorna el reporte estructurado.
        """
        self._ensure_computed()

        total_nodes = self.G.number_of_nodes()
        total_edges = self.G.number_of_edges()
        total_sccs = len(self._components)

        giant_metrics = compute_giant_metrics(self.G, self._giant_nodes, total_nodes)
        phase_3_ready = giant_metrics["pct_of_total_nodes"] > self.PHASE_3_THRESHOLD

        fragmentation = format_fragmentation_by_system(self.G, self._giant_nodes)
        isolated = format_isolated_components(self.G, self._components)

        vft_logger.info(
            f"SCC: {total_sccs} componentes | "
            f"Gigante: {giant_metrics['nodes']:,} nodos ({giant_metrics['pct_of_total_nodes']:.1f}%) | "
            f"{'APTA' if phase_3_ready else 'NO APTA'} para Fase 3"
        )

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "total_sccs": total_sccs,
            "giant_component": giant_metrics,
            "phase_3_ready": phase_3_ready,
            "fragmentation_by_system": fragmentation,
            "isolated_components_sample": isolated
        }

    def get_giant_component(self) -> nx.DiGraph:
        """
        Retorna copia del subgrafo de la componente gigante.
        Para uso directo por indicadores de Fase 3 (T, B).
        """
        self._ensure_computed()
        return extract_giant_component(self.G, self._components)
