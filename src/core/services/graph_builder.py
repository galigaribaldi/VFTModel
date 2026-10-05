"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Constructor del Grafo Topológico para el Modelo VFT.
@route: src/core/services/builder/graph_builder.py
@date: 2026-04-09
@notes: Se migró a una arquitectura de Clase para soportar diferentes modos de 
        construcción topológica (Estricta vs. Integración Realista) usando
        umbrales estadísticos de "snapping" peatonal.
"""

import math
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

    # Filtro phantom (Fix #23): una arista larga solo es phantom si su trazo cruza una
    # discontinuidad real entre sublíneas (salto > PHANTOM_GAP_M). Los tramos largos con
    # trazo continuo (SUB, INTERURBANO, MB/MEXIBÚS exprés) son legítimos.
    PHANTOM_THRESHOLD_M: float = 5_000.0
    PHANTOM_GAP_M: float = 50.0

    # Excepción metodológica EXCLUSIVA del Tren Suburbano (Fix #23).
    # Con la tolerancia Q1 (85 m) el SUB queda sin ningún transbordo intermodal: sus puntos
    # de estación son centroides de andén de tren pesado (150-200 m) y los accesos a los
    # sistemas vecinos quedan a 300-450 m. Para el resto de sistemas rige únicamente el
    # snapping Q1. Formato: estación SUB → (sistema destino, nombre de estación destino).
    # Se conectan todos los nodos homónimos del destino a ≤ SUB_TRANSFER_MAX_M.
    SUB_OFFICIAL_TRANSFERS = [
        ("Buenavista",   ("METRO",   "Buenavista")),
        ("Buenavista",   ("MB",      "Buenavista")),
        ("Lechería",     ("MEXIBÚS", "Lechería")),
        ("Tlalnepantla", ("CC",      "Suburbano")),
    ]
    SUB_TRANSFER_MAX_M: float = 500.0

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
            saltos_union = {}   # índice del primer vértice de la sublínea → salto (m) desde la anterior
            for sublinea in raw_sublineas:
                if len(sublinea) < 2:
                    continue
                if all_coords and tuple(all_coords[-1]) == tuple(sublinea[0]):
                    all_coords.extend(sublinea[1:])
                else:
                    if all_coords:
                        saltos_union[len(all_coords)] = VFTImpedanceModel.haversine(
                            all_coords[-1][0], all_coords[-1][1], sublinea[0][0], sublinea[0][1]
                        )
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

            # Caminata de detección de waypoints de estación (Fix #22)
            # La distancia se mide a lo largo del trazo SIN reinicios. Cada estación se
            # ancla en su proyección sobre el trazo (punto de máxima aproximación) y se
            # suma su offset perpendicular. Por desigualdad triangular:
            #   d_seg = off_a + trazo(ancla_a → ancla_b) + off_b  ≥  haversine(a, b)
            # lo que garantiza DI ≥ 1.0 a nivel arista y, por tanto, de ruta.
            coords = [(c[0], c[1]) for c in all_coords]
            dist_acumulada = [0.0]
            for k in range(1, len(coords)):
                dist_acumulada.append(
                    dist_acumulada[-1] + VFTImpedanceModel.haversine(*coords[k - 1], *coords[k])
                )

            # Visita = racha de vértices consecutivos dentro del radio de la misma estación.
            # Se conserva la proyección más cercana de la racha: [estacion, d_ancla, offset, ultimo_i, primer_i]
            visitas = []
            for i, (lon, lat) in enumerate(coords):
                # ¿Hay una estación del mismo sistema a ≤ SNAP_TOLERANCE_DEG? (Fix 1)
                dist_deg, idx = kdtree_s.query([lon, lat])
                if dist_deg > self.SNAP_TOLERANCE_DEG:
                    continue

                estacion_node = station_subset[idx]
                offset_m, d_ancla = self._project_station_on_trace(
                    estacion_node, i, coords, dist_acumulada
                )
                if visitas and visitas[-1][0] == estacion_node and visitas[-1][3] == i - 1:
                    if offset_m < visitas[-1][2]:
                        visitas[-1][1], visitas[-1][2] = d_ancla, offset_m
                    visitas[-1][3] = i
                else:
                    visitas.append([estacion_node, d_ancla, offset_m, i, i])

            # Una arista por cada cambio de estación (mismo criterio topológico previo:
            # re-visitar la misma estación no crea arista; la salida se mide desde la última visita)
            ultimo_waypoint = None   # (estacion, d_ancla, offset, ultimo_i)
            for estacion_node, d_ancla, offset_m, ultimo_i, primer_i in visitas:
                if ultimo_waypoint is not None and estacion_node != ultimo_waypoint[0]:
                    distancia_m = ultimo_waypoint[2] + (d_ancla - ultimo_waypoint[1]) + offset_m
                    # Mayor discontinuidad entre sublíneas recorrida por esta arista (Fix #23)
                    salto_max_m = max(
                        (sl for k, sl in saltos_union.items() if ultimo_waypoint[3] < k <= primer_i),
                        default=0.0,
                    )
                    self.G.add_edge(
                        ultimo_waypoint[0], estacion_node,
                        color=color,
                        distancia_segmento_m=round(distancia_m, 2),
                        salto_union_max_m=round(salto_max_m, 2),
                        **edge_attr_base,
                    )
                    aristas_creadas += 1
                ultimo_waypoint = (estacion_node, d_ancla, offset_m, ultimo_i)

        vft_logger.info(f"Fase 2 completada: {aristas_creadas} aristas interestación creadas.")

    @staticmethod
    def _project_station_on_trace(station, i, coords, dist_acumulada):
        """
        Proyecta la estación sobre los segmentos del trazo adyacentes al vértice i.
        Retorna (offset_m, d_ancla): distancia perpendicular estación→trazo y
        distancia acumulada a lo largo del trazo hasta el punto proyectado.
        Proyección local equirectangular (error despreciable a escala < 100 m).
        """
        lon_s, lat_s = station
        best = (VFTImpedanceModel.haversine(lon_s, lat_s, *coords[i]), dist_acumulada[i])
        kx = math.cos(math.radians(lat_s))
        for a, b in ((i - 1, i), (i, i + 1)):
            if a < 0 or b >= len(coords):
                continue
            (ax, ay), (bx, by) = coords[a], coords[b]
            dx, dy = (bx - ax) * kx, (by - ay)
            l2 = dx * dx + dy * dy
            if l2 == 0:
                continue
            t = max(0.0, min(1.0, ((lon_s - ax) * kx * dx + (lat_s - ay) * dy) / l2))
            px, py = ax + t * (bx - ax), ay + t * (by - ay)
            offset_m = VFTImpedanceModel.haversine(lon_s, lat_s, px, py)
            if offset_m < best[0]:
                best = (offset_m, dist_acumulada[a] + t * (dist_acumulada[b] - dist_acumulada[a]))
        return best

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
                    self._add_transfer_pair(u_id, v_id, sistema_u, sistema_v, distancia_m)
                    transbordos_creados += 2

        vft_logger.info(f"Se crearon {transbordos_creados} aristas de Transbordo Peatonal.")

    def _add_transfer_pair(self, u_id, v_id, sistema_u: str, sistema_v: str, distancia_m: float):
        """
        Crea el par de aristas de Transbordo Peatonal u↔v cobrando caminata a 5 km/h
        más el Costo de Abordaje (frecuencia / 2) del sistema destino.
        """
        # 1. Tiempo de caminata a 5 km/h (5000m / 60min = 83.33 m/min)
        tiempo_caminata_min = distancia_m / (5000.0 / 60.0)

        # 2. Boarding Cost de cada destino (Frecuencia / 2)
        wait_v = self.FALLBACK_FRECUENCIA.get(sistema_v, 10.0) / 2.0
        wait_u = self.FALLBACK_FRECUENCIA.get(sistema_u, 10.0) / 2.0

        # 3. Arista de Ida (el usuario camina hacia V y espera el transporte V)
        # 4. Arista de Vuelta (el usuario camina hacia U y espera el transporte U)
        for a, b, wait in ((u_id, v_id, wait_v), (v_id, u_id, wait_u)):
            self.G.add_edge(a, b,
                       sistema="Transbordo Peatonal",
                       tipo="transfer",
                       color="blue",
                       distancia_segmento_m=round(distancia_m, 2),
                       travel_time_min=round(tiempo_caminata_min, 2),
                       boarding_cost_min=round(wait, 2),
                       weight=round(tiempo_caminata_min + wait, 4))

    def _apply_sub_transfers(self):
        """
        Fase 3b (Fix #23): conecta los transbordos oficiales del Tren Suburbano
        (SUB_OFFICIAL_TRANSFERS) cuya distancia supera la tolerancia peatonal.
        Solo aplica a nodos SUB; ningún otro sistema recibe transbordos fuera de Q1.
        """
        by_key = defaultdict(list)
        for n, attr in self.G.nodes(data=True):
            if attr.get('tipo') == 'estacion':
                by_key[(attr.get('sistema'), attr.get('nombre'))].append(n)

        creados = 0
        for nombre_sub, key_b in self.SUB_OFFICIAL_TRANSFERS:
            key_a = ("SUB", nombre_sub)
            nodos_a, nodos_b = by_key.get(key_a, []), by_key.get(key_b, [])
            if not nodos_a or not nodos_b:
                vft_logger.warning(f"Transbordo SUB sin match: {key_a} ↔ {key_b}")
                continue
            for u in nodos_a:
                for v in nodos_b:
                    distancia_m = VFTImpedanceModel.haversine(u[0], u[1], v[0], v[1])
                    if 0 < distancia_m <= self.SUB_TRANSFER_MAX_M:
                        self._add_transfer_pair(u, v, key_a[0], key_b[0], distancia_m)
                        creados += 2
        vft_logger.info(f"Fase 3b: {creados} aristas de transbordo oficial del Tren Suburbano.")

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
        # Fix #23: además de la longitud, se exige que el trazo cruce una discontinuidad
        # real entre sublíneas; los tramos largos con trazo continuo se conservan.
        phantom_edges = [
            (u, v) for u, v, d in self.G.edges(data=True)
            if d.get('tipo') == 'transit'
            and d.get('distancia_segmento_m', 0.0) > self.PHANTOM_THRESHOLD_M
            and d.get('salto_union_max_m', float('inf')) > self.PHANTOM_GAP_M
        ]
        if phantom_edges:
            self.G.remove_edges_from(phantom_edges)
            vft_logger.warning(
                f"Eliminadas {len(phantom_edges)} aristas phantom (distancia > {self.PHANTOM_THRESHOLD_M/1000:.0f} km "
                f"y discontinuidad > {self.PHANTOM_GAP_M:.0f} m). "
                f"Causa probable: geometría MultiLineString fragmentada en el backend."
            )

        # 3. Aplicar Snapping (Solo si el modo es realista)
        if mode == "REALISTIC_INTEGRATION":
            # Si no se provee tolerancia, usar la Mediana (Q2) por defecto
            if tolerance_m is None:
                tolerance_m = self.STATISTICAL_THRESHOLDS["Q1"]
            
            self._apply_pedestrian_snapping(tolerance_m)
            self._apply_sub_transfers()

        # 4. Aplicar Impedancia
        vft_logger.info("Aplicando Motor de Impedancia...")
        motor_impedancia = VFTImpedanceModel(self.G)
        motor_impedancia.apply_impedance()

        vft_logger.info(
            f"Grafo final: {self.G.number_of_nodes()} nodos, "
            f"{self.G.number_of_edges()} aristas."
        )
        return self.G