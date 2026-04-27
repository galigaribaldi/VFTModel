"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Orquestador principal del Detour Factor, gestiona el estado del grafo y ensambla respuestas.
@route: src/core/algorithms/topologicalIndicators/detaurFactor/orchestrator.py
"""

import networkx as nx
import pandas as pd
import random
from src.core.models.impedance import VFTImpedanceModel
from src.core.utils.logger import vft_logger
from src.core.algorithms.topologicalIndicators.detaurFactor.engine import get_closest_node_and_walking_distance, calculate_network_distance
from src.core.algorithms.topologicalIndicators.detaurFactor.geometry import format_network_geometry, format_imaginary_geometry

class DetourFactorOrchestrator:
    def __init__(self, G: nx.DiGraph):
        self.G = G

    def calculate_custom_route(self, origen, destino, return_json=False):
        # 1. Obtener nodos y distancias de caminata
        u_red, u_attr, dist_cam_o, coords_o = get_closest_node_and_walking_distance(self.G, origen)
        v_red, v_attr, dist_cam_d, coords_d = get_closest_node_and_walking_distance(self.G, destino)

        # 2. Cálculo de distancias base
        lon_o, lat_o = coords_o
        lon_d, lat_d = coords_d
        from src.core.models.impedance import VFTImpedanceModel
        dist_recta_total_m = VFTImpedanceModel.haversine(lon_o, lat_o, lon_d, lat_d)
        
        if dist_recta_total_m == 0: return {} if return_json else pd.DataFrame()

        try:
            path = nx.shortest_path(self.G, source=u_red, target=v_red, weight='length')
        except nx.NetworkXNoPath:
            return {} if return_json else pd.DataFrame()

        # 3. EXTRACCIÓN DE TRAZABILIDAD (Lo que faltaba)
        ruta_estaciones = [self.G.nodes[n].get('nombre', 'Trazo') for n in path]
        sistemas_raw = [self.G.nodes[n].get('sistema') for n in path if self.G.nodes[n].get('sistema')]
        
        # Sistemas involucrados únicos manteniendo el orden
        sistemas_involucrados = list(dict.fromkeys(sistemas_raw))
        if dist_cam_o > 0 or dist_cam_d > 0:
            sistemas_involucrados.insert(0, "Transbordo Peatonal")

        # 4. Lógica de Nombres Descriptivos
        nombre_origen = u_attr['nombre'] if isinstance(origen, str) else f"Punto cerca de {u_attr['nombre']}"
        nombre_destino = v_attr['nombre'] if isinstance(destino, str) else f"Punto cerca de {v_attr['nombre']}"

        dist_red_topologica_m = calculate_network_distance(self.G, path)
        dist_total_recorrida_m = dist_cam_o + dist_red_topologica_m + dist_cam_d
        
        # 5. Construcción del Resumen Enriquecido
        resumen = {
            "Origen": nombre_origen,
            "Sistema_Origen": u_attr.get('sistema', 'N/A'),
            "Destino": nombre_destino,
            "Sistema_Destino": v_attr.get('sistema', 'N/A'),
            "Sistemas_Involucrados": sistemas_involucrados,
            "Ruta_Estaciones": ruta_estaciones,
            "Saltos_Topologicos": len(path) - 1,
            "Distancia_Recta_km": round(dist_recta_total_m / 1000, 2),
            "Distancia_Red_km": round(dist_total_recorrida_m / 1000, 2),
            "Factor_Desviacion": round(dist_total_recorrida_m / dist_recta_total_m, 2),
            "Consideraciones_Reales": {
                "Caminata_1ra_Milla_m": round(dist_cam_o, 2),
                "Caminata_Ultima_Milla_m": round(dist_cam_d, 2),
                "Estacion_Abordaje": u_attr['nombre'],
                "Estacion_Descenso": v_attr['nombre']
            }
        }

        if return_json:
            return {
                "metrics": resumen,
                "map_data": {
                    "network_route": format_network_geometry(self.G, path),
                    "haversine_line": format_imaginary_geometry(coords_o, coords_d)
                }
            }
        return pd.DataFrame([resumen])

    def calculate_sample_routes(self, sample_size: int = 500, seed: int = None, return_json=False):
        """Muestreo masivo que ahora incluye toda la trazabilidad."""
        if seed is not None: random.seed(seed)
        
        nodos_validos = [n for n, attr in self.G.nodes(data=True) if attr.get('tipo') != 'trazo' and 'nombre' in attr]
        resultados = []
        
        while len(resultados) < sample_size:
            u_id = random.choice(nodos_validos)
            reachable = list(nx.descendants(self.G, u_id).intersection(set(nodos_validos)))
            if not reachable: continue
            
            v_id = random.choice(reachable)
            res = self.calculate_custom_route(u_id, v_id, return_json=True)
            
            if res and (res["metrics"]["Distancia_Recta_km"] * 1000) >= 100:
                resultados.append(res if return_json else res["metrics"])
                    
        return resultados if return_json else pd.DataFrame(resultados)