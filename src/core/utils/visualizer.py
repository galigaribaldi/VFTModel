"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Clase de visualización espacial modular para el Modelo VFT.
@route: src/core/utils/visualizer.py
@date: 2026-04-03
@notes: Refactorizado a POO. Permite generar un dashboard 2x2 o paneles individuales.
"""
import os
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from typing import Union, List
from src.core.utils.logger import vft_logger

class VFTVisualizer:
    """Clase encargada de procesar y renderizar el análisis espacial del Modelo VFT."""
    
    def __init__(self, G: nx.DiGraph):
        self.G = G
        self.posiciones = nx.get_node_attributes(G, 'pos')
        self._preparar_datos()

    def _preparar_datos(self):
        """Procesa y clasifica colores, tamaños y flujos una sola vez en memoria."""
        vft_logger.info("Visualizador inicializado. Pre-procesando geometrías...")
        
        # Diccionario de estilos para la taxonomía de 4 niveles
        estilos_jerarquia = {
            "masivo_pesado": {"color": "darkred", "size": 25},            # Metro, Suburbano
            "masivo_mediano": {"color": "darkorange", "size": 15},        # Metrobús, Tren Ligero
            "superficie_convencional": {"color": "royalblue", "size": 8}, # RTP, Corredores
            "superficie_baja": {"color": "lightblue", "size": 3}          # Alimentadoras, Pumabús
        }
        
        # 1. Preparar Nodos con 4 jerarquías
        self.color_map = []
        self.node_sizes = []
        for node, data in self.G.nodes(data=True):
            if data.get("tipo") == "trazo":
                self.color_map.append('none')
                self.node_sizes.append(0)
            else:
                # Obtenemos la jerarquía, si no existe o viene mal, cae en convencional
                jerarquia = data.get("jerarquia", "superficie_convencional")
                estilo = estilos_jerarquia.get(jerarquia, estilos_jerarquia["superficie_convencional"])
                
                self.color_map.append(estilo["color"])
                self.node_sizes.append(estilo["size"])

        # 2. Preparar Aristas (Igual que antes)
        self.edges_all = list(self.G.edges(data=True))
        self.edge_colors_all = [d.get('color', 'gray') for u, v, d in self.edges_all]
        self.edges_ida = [(u, v) for u, v, d in self.edges_all if d.get('color') == 'green']
        self.edges_vuelta = [(u, v) for u, v, d in self.edges_all if d.get('color') == 'orange']
        self.edges_no_ida = [(u, v) for u, v, d in self.edges_all if d.get('color') != 'green']
        self.edges_no_vuelta = [(u, v) for u, v, d in self.edges_all if d.get('color') != 'orange']
        
    def _configurar_ejes(self, ax):
        """Aplica estilos consistentes al mapa base de cada panel."""
        ax.axis('equal')
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")

    def panel_1_nodos(self, ax):
        """Dibuja exclusivamente los nodos (Estaciones vs Capilaridad)."""
        ax.set_title("1. Distribución de Estaciones (Nodos)", fontsize=16)
        nx.draw_networkx_nodes(
            self.G, self.posiciones, node_size=self.node_sizes, 
            node_color=self.color_map, alpha=0.8, ax=ax
        )
        
        # Nueva leyenda con los 4 niveles
        legend_elements = [
            mlines.Line2D([], [], color='none', marker='o', markerfacecolor='darkred', markersize=12, label='Masivo Pesado'),
            mlines.Line2D([], [], color='none', marker='o', markerfacecolor='darkorange', markersize=9, label='Masivo Mediano'),
            mlines.Line2D([], [], color='none', marker='o', markerfacecolor='royalblue', markersize=6, label='Superficie Convencional'),
            mlines.Line2D([], [], color='none', marker='o', markerfacecolor='lightblue', markersize=4, label='Superficie Baja'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        self._configurar_ejes(ax)

    def panel_2_aristas(self, ax):
        """Dibuja exclusivamente las calles/trazos sin dirección."""
        ax.set_title("2. Densidad de Trazos Físicos (Calles)", fontsize=16)
        if self.edges_all:
            nx.draw_networkx_edges(
                self.G, self.posiciones, alpha=0.4, edge_color=self.edge_colors_all, arrows=False, ax=ax
            )
        self._configurar_ejes(ax)

    def panel_3_ida(self, ax):
        """Resalta flujos de Ida sobre un mapa base fantasmal."""
        ax.set_title("3. Flujos de IDA (Sentido 0)", fontsize=16)
        if self.edges_no_ida:
            nx.draw_networkx_edges(
                self.G, self.posiciones, edgelist=self.edges_no_ida, alpha=0.1, edge_color='gray', arrows=False, ax=ax
            )
        if self.edges_ida:
            nx.draw_networkx_edges(
                self.G, self.posiciones, edgelist=self.edges_ida, alpha=0.9, edge_color='green', 
                width=1.5, arrows=True, arrowsize=8, connectionstyle='arc3,rad=0.03', ax=ax
            )
        self._configurar_ejes(ax)

    def panel_4_regreso(self, ax):
        """Resalta flujos de Vuelta sobre un mapa base fantasmal."""
        ax.set_title("4. Flujos de REGRESO (Sentido 1)", fontsize=16)
        if self.edges_no_vuelta:
            nx.draw_networkx_edges(
                self.G, self.posiciones, edgelist=self.edges_no_vuelta, alpha=0.1, edge_color='gray', arrows=False, ax=ax
            )
        if self.edges_vuelta:
            nx.draw_networkx_edges(
                self.G, self.posiciones, edgelist=self.edges_vuelta, alpha=0.9, edge_color='orange', 
                width=1.5, arrows=True, arrowsize=8, connectionstyle='arc3,rad=0.03', ax=ax
            )
        self._configurar_ejes(ax)

    def render(self, All: Union[bool, int, List[int]] = True, save_name: str = "VFT_MODEL_IMAGE"):
        """
        Orquesta la generación de gráficos y los guarda en la carpeta ASSETS.
        """
        vft_logger.info(f"Renderizando paneles solicitados: All={All}")
        
        # Caso 1: Dashboard Completo (2x2)
        if All is True:
            fig, axs = plt.subplots(2, 2, figsize=(20, 20), facecolor='whitesmoke')
            fig.suptitle("Análisis Topológico del Modelo VFT - CDMX", fontsize=24, fontweight='bold')
            
            self.panel_1_nodos(axs[0, 0])
            self.panel_2_aristas(axs[0, 1])
            self.panel_3_ida(axs[1, 0])
            self.panel_4_regreso(axs[1, 1])
            
        # Caso 2: Paneles Específicos
        else:
            paneles_a_dibujar = [All] if isinstance(All, int) else All
            num_paneles = len(paneles_a_dibujar)
            
            fig, axs = plt.subplots(1, num_paneles, figsize=(10 * num_paneles, 10), facecolor='whitesmoke')
            fig.suptitle("Análisis Topológico VFT (Vista Parcial)", fontsize=20, fontweight='bold')
            
            if num_paneles == 1:
                axs = [axs]
                
            for ax, num_panel in zip(axs, paneles_a_dibujar):
                if num_panel == 1:
                    self.panel_1_nodos(ax)
                elif num_panel == 2:
                    self.panel_2_aristas(ax)
                elif num_panel == 3:
                    self.panel_3_ida(ax)
                elif num_panel == 4:
                    self.panel_4_regreso(ax)
                else:
                    ax.set_title(f"Panel {num_panel} no existe")
                    
        # --- LÓGICA DE GUARDADO AUTOMÁTICO ---
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # Crear carpeta ASSETS si no existe (en la raíz de donde ejecutes el script)
        os.makedirs("ASSETS", exist_ok=True)
        filepath = os.path.join("ASSETS", f"{save_name}.png")
        
        # Guardar en alta resolución (dpi=300) ideal para la tesis
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='whitesmoke')
        vft_logger.info(f"Visualización guardada exitosamente en: {filepath}")
        
        # Mostrar en pantalla
        plt.show()

# =========================================================
# Wrapper para mantener retrocompatibilidad con el builder
# =========================================================
def plot_vft_graph(G: nx.DiGraph, All: Union[bool, int, List[int]] = True, save_name: str = "VFT_MODEL_IMAGE"):
    """
    Función puente para instanciar la clase desde fuera y exportar la gráfica.
    """
    visualizador = VFTVisualizer(G)
    visualizador.render(All=All, save_name=save_name)