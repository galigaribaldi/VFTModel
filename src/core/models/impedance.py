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
    ## Constante de tráfico presupuesto: https://www.gob.mx/cms/uploads/attachment/file/509173/Manual_de_calles_2019.pdf
    BETA_SATURACION_CDMX = 0.8
    
    @classmethod
    def get_friction(cls, derecho_de_via: str) -> float:
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
        "SUB": 60.0, "INTERURBANO": 60.0, "METRO": 40.0, "MB": 25.0,
        "TL": 25.0, "TROLE": 20.0, "RTP": 20.0, "MEXIBÚS": 20.0,
        "MEXICABLE": 20.0, "CBB": 15.0, "CC": 15.0, "PUMABUS": 15.0
    }
    
    FALLBACK_FRECUENCIA = {
        "SUB": 5.0, "INTERURBANO": 10.0, "METRO": 3.0, "MB": 5.0,
        "TL": 6.0, "TROLE": 8.0, "RTP": 15.0, "MEXIBÚS": 5.0,
        "MEXICABLE": 2.0, "CBB": 10.0, "CC": 15.0, "PUMABUS": 10.0
    }
    
    def __init__(self, G:nx.Graph):
        self.G = G
    
    @staticmethod
    def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        Calcula la distancia física en metros entre dos coordenadas.
        Indicador: Distancia Euclidiana
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
        """
        Itera sobre las aristas e inyecta el peso matemático en minutos.
        
        """
        vft_logger.info("Iniciando inyección de motor de impendancia sobre VFT:")
        
        aristas_procesadas = 0
        
        for u, v, data in self.G.edges(data=True):
            distancia_segmento_m = self.haversine(u[0], u[1], v[0], v[1])
            ## En caso de que no encontremos el sistema,
            ## le añadimos el CC al ser el menor transporte con rpestaciones
            sistema = data.get("sistema", "CC")
            v_kmh = data.get("velocidad_promedio_kmh")
            if v_kmh is None or v_kmh <= 0:
                v_kmh = self.FALLBACK_VELOCIDAD.get(sistema, 15.0)
            
            # Conversión de km/h a metros por minuto
            v_m_min = v_kmh * (1000.0 / 60.0)
            
            # 3. Coeficiente de Fricción Vial (Cf)
            derecho_via = data.get("derecho_de_via", "mixto")
            cf = FrictionCalculator.get_friction(derecho_via)
            
            # 4. Cálculo del Tiempo de Traslado Puro
            travel_time_min = (distancia_segmento_m / v_m_min) * cf
            
            # 5. Extracción y Fallback de Frecuencia (F) para costo de abordaje
            frecuencia = data.get("frecuencia_minutos")
            if frecuencia is None or frecuencia <= 0:
                frecuencia = self.FALLBACK_FRECUENCIA.get(sistema, 15.0)
            boarding_cost_min = frecuencia / 2.0

            # 6. Inyección de Atributos al Grafo
            self.G[u][v]['distancia_segmento_m'] = round(distancia_segmento_m, 2)
            self.G[u][v]['travel_time_min'] = round(travel_time_min, 4)
            self.G[u][v]['boarding_cost_min'] = round(boarding_cost_min, 2)
            self.G[u][v]['coeficiente_friccion'] = round(cf, 2)
            
            # El "weight" estándar para algoritmos de enrutamiento como Dijkstra
            self.G[u][v]['weight'] = self.G[u][v]['travel_time_min']
            
            aristas_procesadas += 1

        vft_logger.info(f"Impedancia aplicada exitosamente a {aristas_procesadas} segmentos.")
        return self.G