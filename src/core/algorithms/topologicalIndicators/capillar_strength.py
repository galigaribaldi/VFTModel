"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Motor analítico para evaluar indicadores topológicos del grafo VFT.
@date: 7/04/2026
@route: src/core/algorithms/topologicalIndicators/capillar_strength.py
@nothes: Se agrupan dos tipos indicadores "Fuerza Capilar (Grado Nodal)" y 
        "Factor de Desviación (Detour Factor)". Es importante hacer la división
        De Fuerza Capilar, ya que existe la función puramente matemática
        Y la función que combina las distancias geográficas reales
@warning: Este código puede pesar más en memoria al usar la función de "Fuerza Capilar"
            Por distancias geográficas. Tener cuidado al ejecutar
"""

import networkx as nx
import pandas as pd
from src.core.utils.logger import vft_logger
from src.core.models.impedance import VFTImpedanceModel 
class CapillaryStrengthAnalyzer:
    """
    Clase encargada de calcular métricas de centralidad sobre el Grafo Dirigido.
    """
    
    def __init__(self, G: nx.DiGraph):
        """
        Inicializa el motor ingiriendo el Grafo Topológico ya construido.
        """
        if not isinstance(G, nx.DiGraph):
            raise ValueError("El motor topológico requiere un objeto networkx.DiGraph.")
        self.G = G
        
    def calculate_capillary_strength(self, snap_tolerance_m: float = 25.0) -> pd.DataFrame:
        """
        Calcula la Fuerza Capilar (Grado Nodal) estricta implementando 'Snapping'.
        Corrige la inflación geométrica ignorando las aristas internas de los trazos atrapados.
        """
        resultados = []
        
        # =====================================================================
        # 1. CREACIÓN DEL ÍNDICE ESPACIAL (Grid Hashing)
        # =====================================================================
        cell_size = 0.001 
        trazos_grid = {}
        
        for node, attr in self.G.nodes(data=True):
            if attr.get('tipo') == 'trazo':
                lon, lat = attr['pos']
                cx = int(lon / cell_size)
                cy = int(lat / cell_size)
                
                if (cx, cy) not in trazos_grid:
                    trazos_grid[(cx, cy)] = []
                trazos_grid[(cx, cy)].append(node)

        degree_tol = snap_tolerance_m / 111000.0

        # =====================================================================
        # 2. EVALUACIÓN Y SNAPPING
        # =====================================================================
        for node, attr in self.G.nodes(data=True):
            if attr.get('tipo') == 'trazo' or 'nombre' not in attr:
                continue
                
            in_degree = self.G.in_degree(node)
            out_degree = self.G.out_degree(node)
            
            nombre_estacion = attr['nombre']
            sistema_str = str(attr.get('sistema', 'Desconocido'))
            sistema_str = sistema_str.split('.')[-1].upper() if '.' in sistema_str else sistema_str

            # --- RUTINA DE SNAPPING (Imantación con Filtro de Frontera) ---
            if in_degree == 0 and out_degree == 0:
                lon_est, lat_est = attr['pos']
                cx = int(lon_est / cell_size)
                cy = int(lat_est / cell_size)
                
                candidatos = []
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        candidatos.extend(trazos_grid.get((cx + dx, cy + dy), []))
                
                # PASO A: Recolectar estrictamente quiénes están DENTRO de la burbuja
                nodos_en_burbuja = set()
                for t_node in candidatos:
                    lon_t, lat_t = self.G.nodes[t_node]['pos']
                    
                    if abs(lat_est - lat_t) > degree_tol or abs(lon_est - lon_t) > degree_tol:
                        continue
                        
                    dist = VFTImpedanceModel.haversine(lon_est, lat_est, lon_t, lat_t)
                    
                    if dist <= snap_tolerance_m:
                        nodos_en_burbuja.add(t_node)
                
                aristas_entrada_unicas = set()
                aristas_salida_unicas = set()
                
                # PASO B: Contar solo lo que cruza la frontera (Entra de afuera o sale hacia afuera)
                for t_node in nodos_en_burbuja:
                    for u, v in self.G.in_edges(t_node):
                        if u not in nodos_en_burbuja:  # ¡El filtro mágico!
                            aristas_entrada_unicas.add((u, v))
                            
                    for u, v in self.G.out_edges(t_node):
                        if v not in nodos_en_burbuja:  # ¡El filtro mágico!
                            aristas_salida_unicas.add((u, v))
                
                in_degree = len(aristas_entrada_unicas)
                out_degree = len(aristas_salida_unicas)

            total_degree = in_degree + out_degree
            
            # =================================================================
            # 3. CONSOLIDACIÓN DE RESULTADOS
            # =================================================================
            resultados.append({
                "Nodo_ID": str(node) if isinstance(node, tuple) else str(node),
                "Estacion": nombre_estacion, 
                "Sistemas_Integrados": [sistema_str],
                "Detalle_Estaciones": {
                    sistema_str: [nombre_estacion]
                },
                "Estaciones_Agrupadas": 1,
                "Conexiones_Entrada": in_degree,
                "Conexiones_Salida": out_degree,
                "Fuerza_Capilar_Total": total_degree
            })
            
        df_resultados = pd.DataFrame(resultados)
        
        if not df_resultados.empty:
            df_resultados = df_resultados.sort_values(by="Fuerza_Capilar_Total", ascending=False)
            
        return df_resultados

    def calculate_geo_capillary_strength(self, tolerance_m: float = 100.0, snap_tolerance_m: float = 25.0) -> pd.DataFrame:
        """
        Calcula la Fuerza Capilar agrupando estaciones físicamente cercanas (Macro-Hubs).
        Incorpora 'Snapping' con Grid Espacial y devuelve una estructura de datos
        detallada por sistema (Listas y Diccionarios) para facilitar su consumo en JSON.
        """
        G_prox = nx.Graph()
        
        # =====================================================================
        # 1. ÍNDICE ESPACIAL (Grid Hashing) PARA LAS LÍNEAS (Trazos)
        # =====================================================================
        cell_size = 0.001
        trazos_grid = {}
        
        for node, attr in self.G.nodes(data=True):
            if attr.get('tipo') == 'trazo':
                lon, lat = attr['pos']
                cx = int(lon / cell_size)
                cy = int(lat / cell_size)
                
                if (cx, cy) not in trazos_grid:
                    trazos_grid[(cx, cy)] = []
                trazos_grid[(cx, cy)].append(node)

        degree_tol_geo = tolerance_m / 111000.0
        degree_tol_snap = snap_tolerance_m / 111000.0
        
        # =====================================================================
        # 2. FILTRO DE ESTACIONES REALES
        # =====================================================================
        estaciones_validas = []
        for u_id, u_attr in self.G.nodes(data=True):
            if u_attr.get('tipo') == 'trazo' or 'nombre' not in u_attr:
                continue
            estaciones_validas.append((u_id, u_attr))
            G_prox.add_node(u_id)
            
        # =====================================================================
        # 3. CONSTRUCCIÓN DE MACRO-HUBS (Agrupación por proximidad)
        # =====================================================================
        for i in range(len(estaciones_validas)):
            u_id, u_attr = estaciones_validas[i]
            lon_u, lat_u = u_attr['pos']
            
            for j in range(i + 1, len(estaciones_validas)):
                v_id, v_attr = estaciones_validas[j]
                lon_v, lat_v = v_attr['pos']
                
                if abs(lat_u - lat_v) > degree_tol_geo or abs(lon_u - lon_v) > degree_tol_geo:
                    continue
                
                dist = VFTImpedanceModel.haversine(lon_u, lat_u, lon_v, lat_v)
                if dist <= tolerance_m:
                    G_prox.add_edge(u_id, v_id)
                    
        # =====================================================================
        # 4. CONSOLIDACIÓN Y CÁLCULO DE GRADO (Formato JSON Estandarizado)
        # =====================================================================
        resultados = []
        for component in nx.connected_components(G_prox):
            nombres = set()
            sistemas = set()
            
            # Diccionario para mapear qué estaciones pertenecen a qué sistema
            detalle_estaciones = {}
            
            aristas_entrada_unicas = set()
            aristas_salida_unicas = set()
            
            for node in component:
                attr = self.G.nodes[node]
                nombre_estacion = attr['nombre']
                nombres.add(nombre_estacion)
                
                # Limpieza del sistema
                sistema_str = str(attr.get('sistema', 'Desconocido'))
                sistema_str = sistema_str.split('.')[-1].upper() if '.' in sistema_str else sistema_str
                sistemas.add(sistema_str)
                
                # Poblar el diccionario Detalle_Estaciones
                if sistema_str not in detalle_estaciones:
                    detalle_estaciones[sistema_str] = set()
                detalle_estaciones[sistema_str].add(nombre_estacion)
                
                lon_est, lat_est = attr['pos']
                
                # A. Conexiones Topológicas Directas
                for u, v in self.G.in_edges(node):
                    if u not in component:
                        aristas_entrada_unicas.add((u, v))
                for u, v in self.G.out_edges(node):
                    if v not in component:
                        aristas_salida_unicas.add((u, v))
                        
                # B. Conexiones por Snapping (Imantación de Trazos)
                cx = int(lon_est / cell_size)
                cy = int(lat_est / cell_size)
                
                candidatos = []
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        candidatos.extend(trazos_grid.get((cx + dx, cy + dy), []))
                        
                for t_node in candidatos:
                    lon_t, lat_t = self.G.nodes[t_node]['pos']
                    
                    if abs(lat_est - lat_t) > degree_tol_snap or abs(lon_est - lon_t) > degree_tol_snap:
                        continue
                        
                    dist = VFTImpedanceModel.haversine(lon_est, lat_est, lon_t, lat_t)
                    
                    if dist <= snap_tolerance_m:
                        for u, v in self.G.in_edges(t_node):
                            aristas_entrada_unicas.add((u, v))
                        for u, v in self.G.out_edges(t_node):
                            aristas_salida_unicas.add((u, v))
            
            total_degree = len(aristas_entrada_unicas) + len(aristas_salida_unicas)
            
            if total_degree > 0:
                # Ordenamiento alfabético para una visualización consistente
                nombres_limpios = " - ".join(sorted(list(nombres)))
                sistemas_lista = sorted(list(sistemas))
                detalle_limpio = {k: sorted(list(v)) for k, v in detalle_estaciones.items()}
                
                resultados.append({
                    "Macro_Hub": nombres_limpios,
                    "Sistemas_Integrados": sistemas_lista,           # <-- Array
                    "Detalle_Estaciones": detalle_limpio,            # <-- Objeto JSON anidado
                    "Estaciones_Agrupadas": len(component),
                    "Conexiones_Entrada": len(aristas_entrada_unicas),
                    "Conexiones_Salida": len(aristas_salida_unicas),
                    "Fuerza_Capilar_Total": total_degree
                })
                
        df_resultados = pd.DataFrame(resultados)
        
        if not df_resultados.empty:
            df_resultados = df_resultados.sort_values(by="Fuerza_Capilar_Total", ascending=False)
            
        return df_resultados