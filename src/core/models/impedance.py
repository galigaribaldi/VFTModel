"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Motor de Impedancia VFT - Cálculo de costo Temporal de la Red
@route: src/core/models/impedance.py
@date: 2026-04-03
"""
import math
import networkx as nx
from src.core.utils.logger import vft_logger

class FrictionCalculator:
    """Módulo algebraico para deducir el Coeficiente de Fricción Vial (cf)"""
    ## Constante de tráfico de TOMTOM: https://www.tomtom.com/traffic-index/city/mexico-city/
    ## Average_congestion_level
    BETA_SATURACION_CDMX = 0.759
    
    @classmethod
    def get_friction(cls, derecho_de_via: str) -> float:
        ###
        alpha_map = {
            "exclusivo": 0.0, ## Metro, Sub, inter, cablebus
            "confinado": 0.2, ## Metrobus, trole elevado
            "compartido": 0.5, ## Trolebus Tradicional, ciclovias (no implementado)
            "mixto": 1.0 ## RTP, CC
        }
        ## Por defecto se asume que es mixto
        alpha = alpha_map.get(derecho_de_via, 1.0)
        cf = 1.0 + (alpha * cls.BETA_SATURACION_CDMX)
        
        return cf

class VFTImpedanceModel:
    """
    Aplica la Ecuacion de VFT sobre el grafo topologico
    para generar Vectores de tiempo
    """
    FALLBACK_VELOCIDAD = {
        "SUB": 65.0,           # Ajustado: Tren Suburbano
        "INTERURBANO": 70.0,   # Corregido: velocidad comercial (~70 km/h); diseño era 160 km/h
        "METRO": 36.0,         # Ajustado: STC Metro
        "MB": 16.3,            # Ajustado: Metrobús
        "TL": 22.0,            # Ajustado: Tren Ligero
        "TROLE": 18.0,         # Ajustado: Base para convencional. El elevado (25) requiere dato en GeoJSON
        "RTP": 20.0,           # Flujo libre: ~20 km/h. CF(mixto)=1.759 → efectiva ≈ 11.4 km/h pico
        "MEXIBÚS": 16.3,       # Ajustado: Homologado con Metrobús
        "MEXICABLE": 20.0,     # Ajustado: Homologado con CBB
        "CBB": 20.0,           # Ajustado: Cablebús
        "CC": 16.0,            # Flujo libre: ~16 km/h. CF(mixto)=1.759 → efectiva ≈ 9.1 km/h pico
        "PUMABUS": 11.0        # Sin cambio: régimen de tráfico interno de campus (CU)
    }
    
    FALLBACK_FRECUENCIA = {
        "SUB": 5.0,
        "INTERURBANO": 10.0,
        "METRO": 3.0,
        "MB": 5.0,
        "TL": 6.0,
        "TROLE": 8.0,
        "RTP": 15.0,
        "MEXIBÚS": 5.0,
        "MEXICABLE": 2.0,
        "CBB": 10.0,
        "CC": 15.0,
        "PUMABUS": 10.0
    }
    
    def __init__(self, G:nx.Graph):
        self.G = G
    
    @staticmethod
    def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        Calcula la distancia física en metros entre dos coordenadas.
        Indicador: Distancia Euclidiana
        Trazar una línea recta imaginaria sobre la curva de la Tierra
        entre las dos coordenadas geográficas dadas.
        """
        R = 6371000 ## Radio de la tierra en Metros
        phi_1 = math.radians(lat1)
        phi_2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi/2.0)**2 + \
            math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2.0)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def apply_impedance(self) -> nx.DiGraph:
        """Aplica la Ecuación VFT sobre el grafo topológico"""
        vft_logger.info("Iniciando inyección de motor de impendancia sobre VFT:")
        
        aristas_procesadas = 0
        
        for u, v, data in self.G.edges(data=True):
            sistema = data.get("sistema")
            
            ## Si la arista fue creada por el snapping peatonal, ya tiene sus pesos correctos.
            ## Proteger los Transbordos
            if data.get("tipo") == "transfer" or sistema == "Transbordo Peatonal":
                continue
            
            ## Intentamos leer la distancia si el graph_builder ya la inyectó.
            ## Si no (porque aún no arreglamos graph_builder), usamos haversine como salvavidas.
            distancia_segmento_m = data.get("distancia_segmento_m")
            if distancia_segmento_m is None:
                distancia_segmento_m = self.haversine(u[0], u[1], v[0], v[1])
            
            ## 2. Velocidad Comercial (V)
            v_kmh = data.get("velocidad_promedio_kmh")
            if v_kmh is None or v_kmh <= 0:
                v_kmh = self.FALLBACK_VELOCIDAD.get(sistema, 15.0)
            v_m_min = v_kmh * (1000.0 / 60.0)
            
            # 3. Coeficiente de Fricción Vial (Cf)
            derecho_via = data.get("derecho_de_via", "mixto")
            cf = FrictionCalculator.get_friction(derecho_via)
            
            # 4. Cálculo del Tiempo de Traslado Puro
            travel_time_min = (distancia_segmento_m / v_m_min) * cf
        
            # Como esto es una arista de viaje (no un transbordo), la espera es cero.
            boarding_cost_min = 0.0

            # 6. Inyección de Atributos al Grafo
            self.G[u][v].update({
                'distancia_segmento_m': round(distancia_segmento_m, 2),
                'travel_time_min': round(travel_time_min, 4),
                'boarding_cost_min': round(boarding_cost_min, 2),
                'coeficiente_friccion': round(cf, 2),
                'weight': round(travel_time_min + boarding_cost_min, 4) 
            })
            aristas_procesadas += 1

        vft_logger.info(f"Impedancia aplicada exitosamente a {aristas_procesadas} segmentos.")
        return self.G