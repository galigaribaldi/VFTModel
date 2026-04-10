"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Motor analítico para evaluar el Factor de Desviación (Detour Factor).
@route: src/core/algorithms/detour_factor.py
"""

import networkx as nx
import pandas as pd
import random
from src.core.models.impedance import VFTImpedanceModel
from src.core.utils.logger import vft_logger

class DetourFactorAnalyzer:
    """
    Clase encargada de calcular métricas de eficiencia espacial (Detour Factor)
    sobre el Grafo Dirigido del sistema de Transporte.
    """
    def __init__(self, G: nx.DiGraph):
        if not isinstance(G, nx.DiGraph):
            raise ValueError("El motor requiere un objeto networkx.DiGraph.")
        self.G = G

    def calculate_detaur_factor(self, sample_size: int = 500, seed: int = None) -> pd.DataFrame:
        """
        Calcula el Factor de Desviación (Detour Factor) de la red.
        Matemáticamente: DF = Distancia de Red / Distancia en Línea Recta.
        """
        if seed is not None:
            random.seed(seed)
        
        nodos_validos = [
            (nodo_id, atributos) 
            for nodo_id, atributos in self.G.nodes(data=True) 
            if atributos.get('tipo') != 'trazo' and 'nombre' in atributos
        ]
        
        if len(nodos_validos) < 2:
            return pd.DataFrame()
        
        ids_validos = {nodo_id for nodo_id, _ in nodos_validos}
        diccionario_nodos_validos = {nodo_id: atributos for nodo_id, atributos in nodos_validos}
        
        resultados = []
        intentos = 0
        max_intentos = sample_size * 10 
        
        while len(resultados) < sample_size and intentos < max_intentos:
            intentos += 1
            
            u_id = random.choice(list(ids_validos))
            destinos_alcanzables = list(nx.descendants(self.G, u_id).intersection(ids_validos))
            
            if not destinos_alcanzables:
                continue
                
            v_id = random.choice(destinos_alcanzables)
            
            u_attr = diccionario_nodos_validos[u_id]
            v_attr = diccionario_nodos_validos[v_id]
            
            lon_u, lat_u = u_attr['pos']
            lon_v, lat_v = v_attr['pos']
            
            dist_recta_m = VFTImpedanceModel.haversine(lon_u, lat_u, lon_v, lat_v)
            
            if dist_recta_m < 100:
                continue
                
            try:
                path = nx.shortest_path(self.G, source=u_id, target=v_id, weight='distancia_segmento_m')
                
                dist_red_m = 0
                sistemas_involucrados = set()
                
                # --- NUEVO: Extraemos la ruta ignorando los "trazos" o nodos sin nombre ---
                ruta_estaciones = [
                    self.G.nodes[n]['nombre'] 
                    for n in path 
                    if 'nombre' in self.G.nodes[n] and self.G.nodes[n].get('tipo') != 'trazo'
                ]
                
                for i in range(len(path) - 1):
                    n_actual = path[i]
                    n_siguiente = path[i+1]
                    
                    # 1. Extraemos el sistema de transporte usado en esta arista
                    edge_data = self.G.get_edge_data(n_actual, n_siguiente)
                    if edge_data and 'sistema' in edge_data:
                        sistemas_involucrados.add(edge_data['sistema'])
                    
                    # 2. Sumamos la distancia de red
                    n_actual_pos = self.G.nodes[n_actual]['pos']
                    n_siguiente_pos = self.G.nodes[n_siguiente]['pos']
                    
                    dist_red_m += VFTImpedanceModel.haversine(
                        n_actual_pos[0], n_actual_pos[1], 
                        n_siguiente_pos[0], n_siguiente_pos[1]
                    )
                
                factor_desviacion = dist_red_m / dist_recta_m
                
                # 3. Construimos el resultado limpio
                resultados.append({
                    "Origen": u_attr['nombre'],
                    "Sistema_Origen": u_attr.get('sistema', 'No definido'),
                    "Destino": v_attr['nombre'],
                    "Sistema_Destino": v_attr.get('sistema', 'No definido'),
                    "Sistemas_Involucrados": list(sistemas_involucrados),
                    "Ruta_Estaciones": ruta_estaciones,
                    "Saltos_Topologicos": len(path) - 1,
                    "Distancia_Recta_km": round(dist_recta_m / 1000, 2),
                    "Distancia_Red_km": round(dist_red_m / 1000, 2),
                    "Factor_Desviacion": round(factor_desviacion, 2)
                })
                
            except nx.NetworkXNoPath:
                pass
            except Exception as e:
                print(f"Error en intento {intentos}: {e}")
                
        df_resultados = pd.DataFrame(resultados)
        
        if not df_resultados.empty:
            df_resultados = df_resultados.sort_values(by="Factor_Desviacion", ascending=False)
            
        return df_resultados

    def calculate_any_node_detaur_factor(self, origen, destino) -> pd.DataFrame:
        """
        Calcula el Factor de Desviación incluyendo lógica de Primera y Última Milla.
        
        Parámetros:
        - origen: str (ID del nodo) o tuple (longitud, latitud)
        - destino: str (ID del nodo) o tuple (longitud, latitud)
        
        Retorna: pd.DataFrame con los resultados y las Consideraciones Reales.
        """
        
        def _obtener_nodo_y_caminata(punto):
            # Escenario A: El punto ya es un nodo de la red (String)
            """
            Encuentra el nodo más cercano a una coordenada geográfica arbitraria y devuelve la distancia a pie.
        
            Parámetros:
            - punto: str (ID del nodo) o tuple (longitud, latitud)
        
            Retorna: nodo_mas_cercano, attr_mas_cercano, distancia_minima_m, punto_original
            """
            if isinstance(punto, str):
                if punto in self.G.nodes:
                    attr = self.G.nodes[punto]
                    # No hay caminata, ya estamos en la estación
                    return punto, attr, 0.0, attr['pos']
                else:
                    raise ValueError(f"El nodo {punto} no existe en el grafo.")
            
            # Escenario B: El punto es una coordenada geográfica arbitraria (Tupla)
            if isinstance(punto, tuple) and len(punto) == 2:
                lon_punto, lat_punto = punto
                nodo_mas_cercano = None
                attr_mas_cercano = None
                distancia_minima_m = float('inf')

                for n, attr in self.G.nodes(data=True):
                    if attr.get('tipo') == 'trazo' or 'nombre' not in attr:
                        continue
                        
                    lon_nodo, lat_nodo = attr['pos']
                    distancia = VFTImpedanceModel.haversine(lon_punto, lat_punto, lon_nodo, lat_nodo)
                    
                    if distancia < distancia_minima_m:
                        distancia_minima_m = distancia
                        nodo_mas_cercano = n
                        attr_mas_cercano = attr
                        
                return nodo_mas_cercano, attr_mas_cercano, distancia_minima_m, punto
                
            raise ValueError("La entrada debe ser un String (ID Nodo) o una Tupla (lon, lat).")

        u_red, u_attr, dist_caminata_origen, coords_origen_real = _obtener_nodo_y_caminata(origen)
        v_red, v_attr, dist_caminata_destino, coords_destino_real = _obtener_nodo_y_caminata(destino)

        lon_o, lat_o = coords_origen_real
        lon_d, lat_d = coords_destino_real
        dist_recta_total_m = VFTImpedanceModel.haversine(lon_o, lat_o, lon_d, lat_d)
        
        # Evitar división por cero si escogieron exactamente el mismo punto
        if dist_recta_total_m == 0:
            return pd.DataFrame()

        try:
            path = nx.shortest_path(self.G, source=u_red, target=v_red)
        except nx.NetworkXNoPath:
            # Si los nodos de abordaje no están conectados, no hay ruta posible
            return pd.DataFrame()
            
        dist_red_topologica_m = 0.0
        for i in range(len(path) - 1):
            n_actual_pos = self.G.nodes[path[i]]['pos']
            n_siguiente_pos = self.G.nodes[path[i+1]]['pos']
            dist_red_topologica_m += VFTImpedanceModel.haversine(
                n_actual_pos[0], n_actual_pos[1], 
                n_siguiente_pos[0], n_siguiente_pos[1]
            )
        ## Factor de Desviación
        dist_total_recorrida_m = dist_caminata_origen + dist_red_topologica_m + dist_caminata_destino
        factor_desviacion = dist_total_recorrida_m / dist_recta_total_m
        
        ## Formateo de nombres para la tabla
        nombre_origen = "Coordenada Arbitraria" if isinstance(origen, tuple) else u_attr['nombre']
        nombre_destino = "Coordenada Arbitraria" if isinstance(destino, tuple) else v_attr['nombre']
        
        ## Crea un DataFrame con los resultados
        resultados = []
        resultados.append({
            "Origen": nombre_origen,
            "Destino": nombre_destino,
            "Saltos_Topologicos": len(path) - 1,
            "Distancia_Recta_km": round(dist_recta_total_m / 1000, 2),
            "Distancia_Red_km": round(dist_total_recorrida_m / 1000, 2),
            "Factor_Desviacion": round(factor_desviacion, 2),
            
            ## Colección de Consideraciones Reales
            "Consideraciones_Reales": {
                "Origen_Pertenece_A_Red": isinstance(origen, str),
                "Destino_Pertenece_A_Red": isinstance(destino, str),
                "Caminata_1ra_Milla_Metros": round(dist_caminata_origen, 2),
                "Caminata_Ultima_Milla_Metros": round(dist_caminata_destino, 2),
                "Estacion_Abordaje": u_attr['nombre'],
                "Estacion_Descenso": v_attr['nombre'],
                "Distancia_Pura_Transporte_km": round(dist_red_topologica_m / 1000, 2)
            }
        })
        
        return pd.DataFrame(resultados)