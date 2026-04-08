"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Constructor del Grafo Topológico y Visualizador para el Modelo VFT.
@route: src/core/services/builder/graph_builder.py
@date: 2026-04-02
@notes: Este módulo toma los datos validados por Pydantic, construye un grafo topológico con NetworkX
        y despliega una visualización básica usando Matplotlib.
"""

import networkx as nx
import matplotlib.pyplot as plt
from src.api.schemas.schemas import GeoJSONTransportSchema, TipoEntidad
from src.core.utils.logger import vft_logger
from src.core.utils.visualizer import plot_vft_graph
from src.core.models.impedance import VFTImpedanceModel

def build_and_plot_network(validated_data: GeoJSONTransportSchema):
    """
    Toma los datos validados por Pydantic, construye un grafo topológico con NetworkX
    y despliega una visualización básica usando Matplotlib.
    """
    vft_logger.info("Iniciando la construcción del Grafo VFT...")

    G = nx.DiGraph()

    # 2. Separar y procesar Nodos (Estaciones)
    for feature in validated_data.features:
        if feature.properties.tipo_entidad == TipoEntidad.estacion:
            lon, lat = feature.geometry.coordinates
            node_id = (lon, lat)
            
            G.add_node(
                node_id, 
                pos=(lon, lat),
                nombre=feature.properties.nombre,
                sistema=feature.properties.sistema,
                jerarquia=feature.properties.jerarquia_transporte.value if feature.properties.jerarquia_transporte else "superficie_convencional",
                tipo="estacion"
            )

    # 3. Procesar Aristas Dirigidas (Rutas)
    for feature in validated_data.features:
        if feature.properties.tipo_entidad == TipoEntidad.ruta:
            sentido = feature.properties.sentido
            
            coords_list = []
            if feature.geometry.type == "LineString":
                coords_list = [feature.geometry.coordinates]
            elif feature.geometry.type == "MultiLineString":
                coords_list = feature.geometry.coordinates
            else:
                continue
            for linea in coords_list:
                for i in range(len(linea)-1):
                    u = tuple(linea[i])
                    v = tuple(linea[i+1])
                    if u not in G:
                        G.add_node(u, pos=u, tipo="trazo")
                    if v not in G:
                        G.add_node(v, pos=v, tipo="trazo")
                    
                    props = feature.properties
                    edge_attr = {
                        "sistema": props.sistema,
                        "derecho_de_via": props.derecho_de_via.value if props.derecho_de_via else "mixto",
                        "velocidad_promedio_kmh": props.velocidad_promedio_kmh,
                        "frecuencia_minutos": props.frecuencia_minutos
                    }
                    
                    if sentido == 0:
                        G.add_edge(u, v, color='green', **edge_attr)
                    elif sentido == 1:
                        G.add_edge(u, v, color='orange', **edge_attr)
                    else:
                        G.add_edge(u, v, color='gray', **edge_attr)
    vft_logger.info(f"Grafo Dirigido construido: {G.number_of_nodes()} Nodos topológicos y {G.number_of_edges()} Segmentos de flujo.")
    
    ## Apicacion de la impedancia matemática
    vft_logger.info("Llamando al Motor de Impedancia VFT...")
    motor = VFTImpedanceModel(G)
    G = motor.apply_impedance()  
      
    #plot_vft_graph(G)
    ## SOLO el panel 1 (Nodos) y 2 (Calles)
    #plot_vft_graph(G, All=[1, 2])
    
    ## SOLO la dirección de IDA (Panel 3)
    #plot_vft_graph(G, All=3)
    return G
