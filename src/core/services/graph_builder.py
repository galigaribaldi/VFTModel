"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Constructor del Grafo Topológico para el Modelo VFT.
@route: src/core/services/builder/graph_builder.py
@date: 2026-04-09
@notes: Se migró a una arquitectura de Clase para soportar diferentes modos de 
        construcción topológica (Estricta vs. Integración Realista) usando
        umbrales estadísticos de "snapping" peatonal.
"""

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

    def __init__(self, validated_data: GeoJSONTransportSchema):
        """Inicializa el constructor con los datos validados de Go."""
        self.validated_data = validated_data
        self.G = nx.DiGraph()

    def _build_base_network(self):
        """
        Fase 1 y 2: Construye la red base extrayendo las estaciones (nodos) 
        y los trazos (aristas) directamente del JSON sin alteraciones topológicas.
        """
        vft_logger.info("Fase 1 y 2: Extrayendo nodos y trazos base...")
        
        # Procesar Nodos (Estaciones)
        for feature in self.validated_data.features:
            if feature.properties.tipo_entidad == TipoEntidad.estacion:
                lon, lat = feature.geometry.coordinates
                node_id = (lon, lat)
                
                # Extraemos de forma segura el valor del Enum o asignamos un fallback
                jerarquia_val = (
                    feature.properties.jerarquia_transporte.value 
                    if feature.properties.jerarquia_transporte 
                    else "superficie_convencional"
                )
                
                self.G.add_node(
                    node_id, 
                    pos=(lon, lat),
                    nombre=feature.properties.nombre,
                    sistema=feature.properties.sistema,
                    jerarquia=jerarquia_val,
                    es_cetram=feature.properties.es_cetram,
                    nombre_cetram=feature.properties.nombre_cetram,
                    alcaldia_municipio=feature.properties.alcaldia_municipio,
                    tipo_estacion=feature.properties.tipo_estacion,
                    tipo="estacion"
                )

        # Procesar Aristas (Trazos)
        for feature in self.validated_data.features:
            if feature.properties.tipo_entidad == TipoEntidad.ruta:
                coords_list = []
                sentido = feature.properties.sentido
                geom_type = feature.geometry.type
                
                if geom_type == "LineString":
                    coords_list = [feature.geometry.coordinates]
                elif geom_type == "MultiLineString":
                    coords_list = feature.geometry.coordinates
                else:
                    continue
                
                for linea in coords_list:
                    for i in range(len(linea)-1):
                        u = tuple(linea[i])
                        v = tuple(linea[i+1])
                        
                        # Agregar nodos implícitos del trazo si no existen
                        if u not in self.G:
                            self.G.add_node(u, pos=u, tipo="trazo")
                        if v not in self.G:
                            self.G.add_node(v, pos=v, tipo="trazo")
                        
                        props = feature.properties
                        edge_attr = {
                            "sistema": props.sistema,
                            "derecho_de_via": props.derecho_de_via.value if props.derecho_de_via else "mixto",
                            "velocidad_promedio_kmh": props.velocidad_promedio_kmh,
                            "frecuencia_minutos": props.frecuencia_minutos
                        }
                        
                        # Asignar colores por sentido
                        color = 'gray'
                        if sentido == 0: color = 'green'
                        elif sentido == 1: color = 'orange'

                        self.G.add_edge(u, v, color=color, **edge_attr)

    def _apply_pedestrian_snapping(self, tolerance_m: float):
        """
        Fase 3: Busca estaciones cercanas y las une con aristas peatonales
        para crear integración intermodal.
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
            
            for j in range(i + 1, len(nodos_estacion)):
                v_id, v_attr = nodos_estacion[j]
                lon_v, lat_v = v_attr['pos']
                
                # Calcular distancia real usando el motor de impedancia
                distancia_m = VFTImpedanceModel.haversine(lon_u, lat_u, lon_v, lat_v)
                
                # Validar la conexión
                if 0 < distancia_m <= tolerance_m:
                    tiempo_caminata_min = distancia_m / 50.0 # 50 metros/minuto caminata
                    
                    # Arista de Ida
                    self.G.add_edge(u_id, v_id, 
                               sistema="Transbordo Peatonal", 
                               color="blue",
                               distancia_segmento_m=round(distancia_m, 2),
                               travel_time_min=round(tiempo_caminata_min, 2),
                               boarding_cost_min=0)
                               
                    # Arista de Vuelta
                    self.G.add_edge(v_id, u_id, 
                               sistema="Transbordo Peatonal", 
                               color="blue",
                               distancia_segmento_m=round(distancia_m, 2),
                               travel_time_min=round(tiempo_caminata_min, 2),
                               boarding_cost_min=0)
                               
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

        # 2. Aplicar Snapping (Solo si el modo es realista)
        if mode == "REALISTIC_INTEGRATION":
            # Si no se provee tolerancia, usar la Mediana (Q2) por defecto
            if tolerance_m is None:
                tolerance_m = self.STATISTICAL_THRESHOLDS["Q1"]
            
            self._apply_pedestrian_snapping(tolerance_m)

        # 3. Aplicar Impedancia
        vft_logger.info("Aplicando Motor de Impedancia...")
        motor_impedancia = VFTImpedanceModel(self.G)
        motor_impedancia.apply_impedance()

        return self.G