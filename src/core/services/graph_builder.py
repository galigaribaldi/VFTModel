"""
@author: Galileo Garibaldi
@date: 2026-03-25
@description: Servicio principal del Modelo VFT para transformar geometrías espaciales en grafos topológicos.
@route: src/core/services/graph_builder.py
@notes: Utiliza momepy y geopandas. Explota geometrías complejas a líneas simples antes de la conversión a grafo.
"""

import geopandas as gpd
import momepy
import networkx as nx
import matplotlib.pyplot as plt
from src.core.utils.logger import vft_logger

def build_graph_from_geojson(geojson_dict: dict) -> nx.MultiGraph:
    """Convierte un diccionario GeoJSON en un grafo matemático ruteable."""
    vft_logger.info("Iniciando construcción del Grafo (VFT Model)")
    
    try:
        gdf = gpd.GeoDataFrame.from_features(geojson_dict["features"])
        vft_logger.info(f"GeoDataFrame inicial creado con {len(gdf)} geometrías complejas.")
    
        ##Convertir multistring a linestring para convertirlo a NetworkX
        gdf = gdf.explode(index_parts=False, ignore_index=True)
        gdf = gdf[gdf.geometry.type == 'LineString']
        
        # Proyección a UTM Zona 14N (CDMX) para mediciones precisas en metros
        if gdf.crs is None:
            gdf.set_crs(epsg=4326, inplace=True)
        gdf = gdf.to_crs(epsg=32614)
        
        vft_logger.info("Proyección espacial UTM Zona 14N aplicada correctamente.")         
        
        # Creación del grafo usando el enfoque primal (Nodos = Intersecciones)
        graph = momepy.gdf_to_nx(gdf, approach='primal')
        
        ## Opcional: Pintando el grafo
        vft_logger.info(f"¡Higuera construida! {graph}")
        nodos_muestra = list(graph.nodes)[:2]
        aristas_muestra = list(graph.edges(data=True))[:1] # Incluimos data=True para ver los atributos
        
        vft_logger.info(f"Muestra de Nodos (Coordenadas UTM): {nodos_muestra}")
        vft_logger.info(f"Muestra de Arista (Conectividad y Atributos): {aristas_muestra}")
        
        # --- EXPORTACIÓN VISUAL ---
        # Pintamos el grafo en una imagen PNG para validar visualmente la red
        vft_logger.info("Generando renderizado visual del grafo (VFT_Render.png)...")
        fig, ax = plt.subplots(figsize=(10, 10))
        nx.draw(graph, pos={n: n for n in graph.nodes()}, node_size=10, node_color='red', edge_color='gray', ax=ax)
        plt.savefig("VFT_Render.png", dpi=300, bbox_inches='tight')
        plt.close(fig) # Cerramos la figura para no consumir RAM
        vft_logger.info("Renderizado visual guardado exitosamente.")
        
        return graph
    
    except Exception as e:
        vft_logger.error(f"Error matemático o topológico al construir el grafo: {e}")
        raise e    