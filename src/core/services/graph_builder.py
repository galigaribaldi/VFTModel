"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Constructor del Grafo Topológico para el Modelo VFT.
@route: src/core/services/builder/graph_builder.py
@date: 2026-04-09
@notes: Se migró a una arquitectura de Clase para soportar diferentes modos de 
        construcción topológica (Estricta vs. Integración Realista) usando
        umbrales estadísticos de "snapping" peatonal.
"""

import numpy as np
from scipy.spatial import KDTree
from collections import defaultdict
import networkx as nx
from src.api.schemas.schemas import GeoJSONTransportSchema, TipoEntidad
from src.core.utils.logger import vft_logger
from src.core.models.impedance import VFTImpedanceModel

class VFTGraphBuilder:
    """
    Clase orquestadora para la construcción del Grafo VFT.
    Permite generar redes puramente matemáticas o redes integradas con transbordos peatonales.
    """
    
    # Diccionario de umbrales estadísticos de transbordo (en metros)
    STATISTICAL_THRESHOLDS = {
        "MIN": 15.0,        # Intersección estricta / Mismo polígono arquitectónico
        "Q1": 85.0,         # Transbordo rápido y directo (Realista Conservador)
        "Q2_MEDIAN": 180.0, # Transbordo promedio real (Integración Total de CETRAMs)
        "MEAN": 245.0,      # Promedio matemático (Sesgado por outliers)
        "Q3": 420.0,        # Límite máximo de caminata forzada
        "MAX": 880.0        # Outlier / Falso transbordo
    }
    # Frecuencias promedio para el cálculo de abordaje en transbordos
    ## definidos desde la concepción del grafo en archvios GTFS
    FALLBACK_FRECUENCIA = {
        "METRO": 3.0, "MB": 5.0, "TL": 10.0, "TROLE": 8.0,
        "RTP": 15.0, "SUB": 12.0, "CBB": 10.0, "CC": 15.0, "MEXIBÚS": 6.0
    }
    # Umbral de snapping espacial: ~50 m convertidos a grados decimales en CDMX (lat ~19°N)
    # 1° lat ≈ 111,000 m — tolerancia uniforme para el KDTree de Fase 2
    SNAP_TOLERANCE_DEG: float = 50.0 / 111_000.0   # ≈ 0.000450 °

    def __init__(self, validated_data: GeoJSONTransportSchema):
        """Inicializa el constructor con los datos validados de Go."""
        self.validated_data = validated_data
        self.G = nx.DiGraph()

    def _build_base_network(self):
        """
        Fase 1: Registra estaciones como nodos del grafo (coordenadas GPS originales).
        Fase 2: Para cada ruta, concatena todas las sublíneas del MultiLineString en
        una secuencia continua y la recorre buscando estaciones registradas dentro de
        SNAP_TOLERANCE_DEG (~50 m). Crea UNA arista por cada par de estaciones
        consecutivas detectadas, con la distancia haversine acumulada a lo largo del
        trazo real (no en línea recta).

        Resuelve dos problemas estructurales del GeoJSON de Apimetro:
          Trampa 1 — float mismatch: la proyección ST_LineLocatePoint desplaza el
            endpoint del segmento al eje del carril (~5-15 m de la parada real).
            El KDTree tolera hasta 50 m, absorbiendo este desfase.
          Trampa 2 — sublíneas no interestación: MB, CC, RTP y TROLE tienen
            sublíneas a nivel de cuadra (2-6 vértices, ~50-200 m). La caminata
            acumula distancia entre waypoints sin importar la granularidad del GeoJSON.
        """
        vft_logger.info("Fase 1 y 2: Extrayendo nodos y trazos base...")

        # ── Fase 1: Registrar estaciones ──────────────────────────────────────
        for feature in self.validated_data.features:
            if feature.properties.tipo_entidad == TipoEntidad.estacion:
                lon, lat = feature.geometry.coordinates
                node_id = (lon, lat)

                jerarquia_val = (
                    feature.properties.jerarquia_transporte.value
                    if feature.properties.jerarquia_transporte
                    else "superficie_convencional"
                )

                self.G.add_node(
                    node_id,
                    pos=(lon, lat),
                    nombre=feature.properties.nombre,
                    sistema=feature.properties.sistema.value,
                    jerarquia=jerarquia_val,
                    es_cetram=feature.properties.es_cetram,
                    nombre_cetram=feature.properties.nombre_cetram,
                    alcaldia_municipio=feature.properties.alcaldia_municipio,
                    tipo_estacion=feature.properties.tipo_estacion,
                    tipo="estacion"
                )

        # ── Fase 2: KDTree por sistema (evita contaminación cruzada) ─────────
        # Cada sistema tiene su propio árbol espacial. Al caminar una ruta,
        # solo se consulta el árbol del sistema al que pertenece esa ruta.
        station_nodes = list(self.G.nodes())
        if not station_nodes:
            vft_logger.warning("Fase 1 no registró estaciones. Abortando Fase 2.")
            return

        sys_nodes_map = defaultdict(list)
        for n in station_nodes:
            s = self.G.nodes[n].get('sistema', '')
            sys_nodes_map[s].append(n)

        sys_kdtrees = {
            s: (KDTree(np.array([[n[0], n[1]] for n in nlist])), nlist)
            for s, nlist in sys_nodes_map.items() if nlist
        }
        aristas_creadas = 0

        for feature in self.validated_data.features:
            if feature.properties.tipo_entidad != TipoEntidad.ruta:
                continue

            geom_type = feature.geometry.type
            if geom_type == "LineString":
                raw_sublineas = [feature.geometry.coordinates]
            elif geom_type == "MultiLineString":
                raw_sublineas = feature.geometry.coordinates
            else:
                continue

            # Concatenar sublíneas en una secuencia continua,
            # deduplicando el punto de unión entre sublíneas adyacentes
            all_coords = []
            for sublinea in raw_sublineas:
                if len(sublinea) < 2:
                    continue
                if all_coords and tuple(all_coords[-1]) == tuple(sublinea[0]):
                    all_coords.extend(sublinea[1:])
                else:
                    all_coords.extend(sublinea)

            if len(all_coords) < 2:
                continue

            props   = feature.properties
            sentido = props.sentido
            color   = 'gray'
            if sentido == 0:   color = 'green'
            elif sentido == 1: color = 'orange'

            # Seleccionar el KDTree del sistema de esta ruta (Fix 1)
            route_sistema = props.sistema.value
            if route_sistema not in sys_kdtrees:
                vft_logger.debug(f"Sin estaciones para sistema '{route_sistema}'. Ruta omitida.")
                continue
            kdtree_s, station_subset = sys_kdtrees[route_sistema]

            edge_attr_base = {
                "sistema":                route_sistema,           # Fix 3: .value string
                "sentido":                sentido,                 # Fix 2: dirección IDA(1)/REGRESO(0)
                "derecho_de_via":         props.derecho_de_via.value if props.derecho_de_via else "mixto",
                "velocidad_promedio_kmh": props.velocidad_promedio_kmh,
                "frecuencia_minutos":     props.frecuencia_minutos,
                "tipo":                   "transit",
            }

            # Caminata de detección de waypoints de estación
            ultimo_waypoint = None   # node_id de la última estación encontrada
            dist_acumulada  = 0.0

            for i, coord in enumerate(all_coords):
                lon, lat = coord[0], coord[1]

                # Acumular haversine desde el punto anterior del trazo
                if i > 0:
                    lon_p, lat_p = all_coords[i - 1][0], all_coords[i - 1][1]
                    dist_acumulada += VFTImpedanceModel.haversine(lon_p, lat_p, lon, lat)

                # ¿Hay una estación del mismo sistema a ≤ SNAP_TOLERANCE_DEG? (Fix 1)
                dist_deg, idx = kdtree_s.query([lon, lat])

                if dist_deg <= self.SNAP_TOLERANCE_DEG:
                    estacion_node = station_subset[idx]

                    if estacion_node != ultimo_waypoint:
                        # Estación nueva → crear arista desde el último waypoint
                        if ultimo_waypoint is not None:
                            self.G.add_edge(
                                ultimo_waypoint, estacion_node,
                                color=color,
                                distancia_segmento_m=round(dist_acumulada, 2),
                                **edge_attr_base,
                            )
                            aristas_creadas += 1
                        ultimo_waypoint = estacion_node

                    # Resetear siempre al estar dentro del radio de tolerancia
                    # (evita acumular distancia de "rebote" cerca de la estación)
                    dist_acumulada = 0.0

        vft_logger.info(f"Fase 2 completada: {aristas_creadas} aristas interestación creadas.")

    def _apply_pedestrian_snapping(self, tolerance_m: float):
        """
        Fase 3: Busca estaciones cercanas y las une con aristas peatonales
        para crear integración intermodal, cobrando el Costo de Abordaje.
        """
        vft_logger.info(f"Fase 3: Integrando sistemas (Tolerancia peatonal: {tolerance_m}m)...")
        
        nodos_estacion = [
            (n, attr) for n, attr in self.G.nodes(data=True) 
            if attr.get('tipo') != 'trazo' and 'nombre' in attr
        ]
        
        transbordos_creados = 0
        
        for i in range(len(nodos_estacion)):
            u_id, u_attr = nodos_estacion[i]
            lon_u, lat_u = u_attr['pos']
            sistema_u = u_attr.get("sistema", "GENERICO")
            
            for j in range(i + 1, len(nodos_estacion)):
                v_id, v_attr = nodos_estacion[j]
                lon_v, lat_v = v_attr['pos']
                sistema_v = v_attr.get("sistema", "GENERICO")
                
                # Calcular distancia real geodésica
                distancia_m = VFTImpedanceModel.haversine(lon_u, lat_u, lon_v, lat_v)
                
                # Validar la conexión
                if 0 < distancia_m <= tolerance_m:
                    # 1. Calcular tiempo de caminata a 5 km/h (5000m / 60min = 83.33 m/min)
                    tiempo_caminata_min = distancia_m / (5000.0 / 60.0) 
                    
                    # 2. Calcular Boarding Cost de cada destino (Frecuencia / 2)
                    wait_v = self.FALLBACK_FRECUENCIA.get(sistema_v, 10.0) / 2.0
                    wait_u = self.FALLBACK_FRECUENCIA.get(sistema_u, 10.0) / 2.0
                    
                    # 3. Arista de Ida (El usuario camina hacia V, y espera el transporte V)
                    self.G.add_edge(u_id, v_id, 
                               sistema="Transbordo Peatonal", 
                               tipo="transfer",
                               color="blue",
                               distancia_segmento_m=round(distancia_m, 2),
                               travel_time_min=round(tiempo_caminata_min, 2),
                               boarding_cost_min=round(wait_v, 2),
                               weight=round(tiempo_caminata_min + wait_v, 4))
                               
                    # 4. Arista de Vuelta (El usuario camina hacia U, y espera el transporte U)
                    self.G.add_edge(v_id, u_id, 
                               sistema="Transbordo Peatonal",
                               tipo="transfer", 
                               color="blue",
                               distancia_segmento_m=round(distancia_m, 2),
                               travel_time_min=round(tiempo_caminata_min, 2),
                               boarding_cost_min=round(wait_u, 2),
                               weight=round(tiempo_caminata_min + wait_u, 4))
                               
                    transbordos_creados += 2

        vft_logger.info(f"Se crearon {transbordos_creados} aristas de Transbordo Peatonal.")

    def build_graph(self, mode: str = "REALISTIC_INTEGRATION", tolerance_m: float = None) -> nx.DiGraph:
        """
        Método orquestador principal.
        Modos soportados:
        - 'STRICT_TOPOLOGY': Grafo matemático puro, sin intersecciones peatonales.
        - 'REALISTIC_INTEGRATION': Aplica el snapping peatonal según el umbral dado.
        """
        vft_logger.info(f"Iniciando VFTGraphBuilder en modo: {mode}")
        
        # 1. Construir red base
        self._build_base_network()
        vft_logger.info(f"Grafo Base construido: {self.G.number_of_nodes()} Nodos y {self.G.number_of_edges()} Segmentos.")

        # 2. Filtrar aristas phantom (segmentos interestación irrealmente largos).
        # Causa raíz: rutas con MultiLineString fragmentado en el backend Go (ST_LineMerge
        # fallido). Al concatenar sublíneas no contiguas, la caminata acumula distancia
        # entre fragmentos geográficamente distantes y genera un edge largo dentro del
        # mismo sistema. Umbral conservador: ninguna parada de CC/RTP debería estar a
        # más de 5 km en línea recta de la siguiente estación registrada.
        # Impacto en algoritmos: B (betweenness) y T (tiempo promedio) son sensibles
        # a estos edges si son el único puente entre fragmentos desconectados.
        PHANTOM_THRESHOLD_M = 5_000.0
        phantom_edges = [
            (u, v) for u, v, d in self.G.edges(data=True)
            if d.get('tipo') == 'transit'
            and d.get('distancia_segmento_m', 0.0) > PHANTOM_THRESHOLD_M
        ]
        if phantom_edges:
            self.G.remove_edges_from(phantom_edges)
            vft_logger.warning(
                f"Eliminadas {len(phantom_edges)} aristas phantom (distancia > {PHANTOM_THRESHOLD_M/1000:.0f} km). "
                f"Causa probable: geometría MultiLineString fragmentada en el backend."
            )

        # 3. Aplicar Snapping (Solo si el modo es realista)
        if mode == "REALISTIC_INTEGRATION":
            # Si no se provee tolerancia, usar la Mediana (Q2) por defecto
            if tolerance_m is None:
                tolerance_m = self.STATISTICAL_THRESHOLDS["Q1"]
            
            self._apply_pedestrian_snapping(tolerance_m)

        # 4. Aplicar Impedancia
        vft_logger.info("Aplicando Motor de Impedancia...")
        motor_impedancia = VFTImpedanceModel(self.G)
        motor_impedancia.apply_impedance()

        vft_logger.info(
            f"Grafo final: {self.G.number_of_nodes()} nodos, "
            f"{self.G.number_of_edges()} aristas."
        )
        return self.G