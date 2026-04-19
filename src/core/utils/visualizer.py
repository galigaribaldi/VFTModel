"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Visualizador descriptivo del grafo VFT — orientado a presentación, no a análisis técnico
@route: src/core/utils/visualizer.py
"""
import os
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from typing import Union
from src.core.utils.logger import vft_logger

# Viewport aproximado de la Zona Metropolitana del Valle de México.
# Evita que nodos outliers (ej. Interurbano Toluca) deformen la escala del grafo.
BBOX_ZMVM = {
    "lon_min": -99.45, "lon_max": -98.85,
    "lat_min": 19.10,  "lat_max": 19.68,
}

class VFTVisualizer:
    def __init__(self, G: nx.DiGraph):
        self.G = G
        self.posiciones = nx.get_node_attributes(G, 'pos')

        # Paleta de color por jerarquía — consistente en todos los paneles
        self.estilos_jerarquia = {
            "masivo_pesado": {
                "color": "#8B0000", "size": 30,
                "label": "Masivo Pesado  (Metro, Suburbano, Interurbano)",
            },
            "masivo_mediano": {
                "color": "#E87722", "size": 18,
                "label": "Masivo Mediano  (Metrobús, Tren Ligero, Cablebús)",
            },
            "superficie_convencional": {
                "color": "#1E7FCC", "size": 7,
                "label": "Superficie Convencional  (RTP, CC, Trolebús)",
            },
        }
        self._preparar_datos()

    # ------------------------------------------------------------------
    # Preparación de datos
    # ------------------------------------------------------------------

    def _preparar_datos(self):
        """Clasifica nodos y aristas, precalcula colores y estadísticas."""
        self.node_colors   = []
        self.node_sizes    = []
        self.nodes_to_plot = []
        self._color_por_nodo: dict = {}

        for n, data in self.G.nodes(data=True):
            jerarquia = data.get('jerarquia', 'superficie_convencional')
            # Los nodos de trazo no forman parte del análisis descriptivo
            if data.get('tipo') == 'trazo':
                continue
            estilo = self.estilos_jerarquia.get(
                jerarquia, self.estilos_jerarquia["superficie_convencional"]
            )
            self.nodes_to_plot.append(n)
            self.node_colors.append(estilo["color"])
            self.node_sizes.append(estilo["size"])
            self._color_por_nodo[n] = estilo["color"]

        # Clasificación de aristas
        self.transit_edges  = [
            (u, v) for u, v, d in self.G.edges(data=True) if d.get('tipo') == 'transit'
        ]
        self.transfer_edges = [
            (u, v) for u, v, d in self.G.edges(data=True) if d.get('tipo') == 'transfer'
        ]
        self.edges_ida = [
            (u, v) for u, v, d in self.G.edges(data=True)
            if d.get('tipo') == 'transit' and str(d.get('sentido')) == '0'
        ]
        self.edges_regreso = [
            (u, v) for u, v, d in self.G.edges(data=True)
            if d.get('tipo') == 'transit' and str(d.get('sentido')) == '1'
        ]

        # Color de cada arista según la jerarquía del nodo origen
        fallback = "#888888"
        self._color_transit  = [self._color_por_nodo.get(u, fallback) for u, v in self.transit_edges]
        self._color_ida      = [self._color_por_nodo.get(u, fallback) for u, v in self.edges_ida]
        self._color_regreso  = [self._color_por_nodo.get(u, fallback) for u, v in self.edges_regreso]

        # Texto de estadísticas para el pie de cada figura
        self.stats_texto = (
            f"{len(self.nodes_to_plot):,} estaciones  ·  "
            f"{len(self.transit_edges):,} segmentos de ruta  ·  "
            f"{len(self.transfer_edges):,} transbordos peatonales"
        )

    # ------------------------------------------------------------------
    # Helpers de presentación
    # ------------------------------------------------------------------

    def _configurar_ax(self, ax, titulo: str, subtitulo: str = ""):
        ax.set_title(titulo, fontsize=13, fontweight='bold', pad=10)
        if subtitulo:
            ax.set_xlabel(subtitulo, fontsize=8.5, color='#666666', labelpad=5)
        ax.axis('off')

    def _aplicar_viewport(self, ax):
        """Fija la vista a la ZMVM. Llamar DESPUÉS de todas las llamadas a nx.draw_*."""
        ax.set_xlim(BBOX_ZMVM["lon_min"], BBOX_ZMVM["lon_max"])
        ax.set_ylim(BBOX_ZMVM["lat_min"], BBOX_ZMVM["lat_max"])

    def _agregar_leyenda(self, ax, incluir_transbordo: bool = False):
        handles = [
            mpatches.Patch(facecolor=e["color"], label=e["label"], edgecolor='none')
            for e in self.estilos_jerarquia.values()
        ]
        if incluir_transbordo:
            handles.append(
                mlines.Line2D([], [], color='#999999', linestyle='--',
                              linewidth=1.2, label='Transbordo peatonal')
            )
        ax.legend(
            handles=handles, loc='lower left', fontsize=7.5,
            framealpha=0.9, edgecolor='#cccccc',
            handlelength=1.4, handleheight=1.0,
            borderpad=0.8, labelspacing=0.5,
        )

    def _agregar_stats(self, ax):
        ax.text(
            0.5, -0.02, self.stats_texto,
            transform=ax.transAxes, ha='center', va='top',
            fontsize=7.5, color='#999999', style='italic',
        )

    # ------------------------------------------------------------------
    # Paneles
    # ------------------------------------------------------------------

    def panel_1_nodos(self, ax):
        """Infraestructura: distribución espacial de estaciones por jerarquía."""
        self._configurar_ax(
            ax,
            "Infraestructura de Estaciones",
            subtitulo="Distribución espacial por jerarquía de servicio — ZMVM",
        )
        nx.draw_networkx_nodes(
            self.G, self.posiciones,
            nodelist=self.nodes_to_plot,
            node_size=self.node_sizes,
            node_color=self.node_colors,
            alpha=0.85, ax=ax,
        )
        self._aplicar_viewport(ax)
        self._agregar_leyenda(ax)
        self._agregar_stats(ax)

    def panel_2_aristas(self, ax):
        """Conectividad: red de segmentos de ruta coloreados por jerarquía."""
        self._configurar_ax(
            ax,
            "Red de Conectividad",
            subtitulo="Segmentos de ruta coloreados por jerarquía de servicio",
        )
        # Nodos como referencia geográfica muy tenue
        nx.draw_networkx_nodes(
            self.G, self.posiciones,
            node_color='#bbbbbb', node_size=1, alpha=0.12, ax=ax,
        )
        # Transbordos peatonales (solo modo REALISTIC_INTEGRATION)
        if self.transfer_edges:
            nx.draw_networkx_edges(
                self.G, self.posiciones,
                edgelist=self.transfer_edges,
                edge_color='#aaaaaa', alpha=0.18, width=0.4,
                style='dashed', arrows=False, ax=ax,
            )
        # Segmentos de ruta — coloreados por jerarquía, sin flechas para evitar saturación
        nx.draw_networkx_edges(
            self.G, self.posiciones,
            edgelist=self.transit_edges,
            edge_color=self._color_transit,
            alpha=0.4, width=0.55,
            arrows=False, ax=ax,
        )
        self._aplicar_viewport(ax)
        self._agregar_leyenda(ax, incluir_transbordo=bool(self.transfer_edges))
        self._agregar_stats(ax)

    def panel_3_ida(self, ax):
        """Sentido IDA: segmentos en dirección de operación habitual."""
        self._configurar_ax(
            ax,
            "Sentido de Servicio — IDA",
            subtitulo="Segmentos operando en dirección de ida, coloreados por jerarquía",
        )
        nx.draw_networkx_nodes(
            self.G, self.posiciones,
            node_size=1, node_color='#bbbbbb', alpha=0.15, ax=ax,
        )
        if self.edges_ida:
            nx.draw_networkx_edges(
                self.G, self.posiciones,
                edgelist=self.edges_ida,
                edge_color=self._color_ida,
                alpha=0.5, width=0.65,
                arrows=False, ax=ax,
            )
        else:
            ax.text(0.5, 0.5, "Sin segmentos con sentido IDA registrado",
                    transform=ax.transAxes, ha='center', va='center', color='#999999')
        self._aplicar_viewport(ax)
        self._agregar_leyenda(ax)
        self._agregar_stats(ax)

    def panel_4_regreso(self, ax):
        """Sentido REGRESO: segmentos en dirección de retorno."""
        self._configurar_ax(
            ax,
            "Sentido de Servicio — REGRESO",
            subtitulo="Segmentos operando en dirección de regreso, coloreados por jerarquía",
        )
        nx.draw_networkx_nodes(
            self.G, self.posiciones,
            node_size=1, node_color='#bbbbbb', alpha=0.15, ax=ax,
        )
        if self.edges_regreso:
            nx.draw_networkx_edges(
                self.G, self.posiciones,
                edgelist=self.edges_regreso,
                edge_color=self._color_regreso,
                alpha=0.5, width=0.65,
                arrows=False, ax=ax,
            )
        else:
            ax.text(0.5, 0.5, "Sin segmentos con sentido REGRESO registrado",
                    transform=ax.transAxes, ha='center', va='center', color='#999999')
        self._aplicar_viewport(ax)
        self._agregar_leyenda(ax)
        self._agregar_stats(ax)


# ----------------------------------------------------------------------
# Función de entrada pública
# ----------------------------------------------------------------------

def plot_vft_graph(G: nx.DiGraph, All: Union[bool, int] = True, save_name: str = "VFT_PLOT"):
    """
    Genera y guarda un panel del grafo VFT.

    Args:
        G:         Grafo dirigido NetworkX con atributos 'pos', 'jerarquia', 'tipo', 'sentido'.
        All:       Número de panel a renderizar (1-4).
        save_name: Nombre del archivo PNG de salida (sin extensión).
    """
    viz = VFTVisualizer(G)
    fig, ax = plt.subplots(figsize=(10, 9), facecolor='#f8f8f8')

    panel_map = {
        1: viz.panel_1_nodos,
        2: viz.panel_2_aristas,
        3: viz.panel_3_ida,
        4: viz.panel_4_regreso,
    }

    fn = panel_map.get(int(All))
    if fn:
        fn(ax)
    else:
        vft_logger.warning(f"Panel {All} no existe. Opciones válidas: 1-4.")

    plt.tight_layout()
    os.makedirs("ASSETS", exist_ok=True)
    out_path = f"ASSETS/{save_name}.png"
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    vft_logger.info(f"Panel guardado: {out_path}")
    plt.show()
    plt.close(fig)
