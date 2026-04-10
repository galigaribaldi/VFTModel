"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Motor analítico para evaluar el Nivel de Cobertura Espacial (C).
@route: src/core/algorithms/spatial_coverage.py
"""

import geopandas as gpd
from shapely.geometry import shape
import pandas as pd
from typing import Dict, Any

class SpatialCoverageAnalyzer():
    """
    Clase encargada de calcular el porcentaje de territorio que tiene acceso
    caminable a una estación de transporte masivo
    """
    CRS_WGS84 = "EPSG:4326" ## GPS Mundial
    CRS_METRICO_CDMX = "EPSG:32614"
    
    def __init__(self, estaciones_geojson: Dict[str, Any], poligonos_geojson: Dict[str, Any]):
        """
        Inicializando el motor ingiriendo los dos GeoJson (Estaciones y Fronteras)
        Se covnierten datos crudos a GeoDataframes
        """
        features_est = [
            f for f in estaciones_geojson.get('features', []) 
            if f.get('properties', {}).get('tipo_entidad') == 'estacion'
        ]
        
        if not features_est:
            raise ValueError("GeoPandas no recibió estaciones. Verifica que el campo 'tipo_entidad' exista y sea 'estacion' en el JSON de Go.")
            
        self.gdf_estaciones = gpd.GeoDataFrame.from_features(features_est, crs=self.CRS_WGS84)
        self.gdf_estaciones = self.gdf_estaciones.to_crs(self.CRS_METRICO_CDMX)
        
        features_pol = poligonos_geojson.get('features', [])
        
        # Si Go devuelve la respuesta envuelta en "data" (ej. {"status": "success", "data": {"features": [...]}})
        if not features_pol and 'data' in poligonos_geojson:
            features_pol = poligonos_geojson.get('data', {}).get('features', [])
        
        if not features_pol:
            raise ValueError("GeoPandas no encontró la lista de features de los polígonos territoriales.")

        self.gdf_poligonos = gpd.GeoDataFrame.from_features(features_pol, crs=self.CRS_WGS84)
        self.gdf_poligonos = self.gdf_poligonos.to_crs(self.CRS_METRICO_CDMX)
        
        # CORRECCIÓN DE DUPLICADOS: 
        # Fusionar geometrías fragmentadas que pertenezcan a la misma demarcación
        if 'nombre' in self.gdf_poligonos.columns:
            self.gdf_poligonos = self.gdf_poligonos.dissolve(by='nombre').reset_index()
        
    def _core_coverage_math(self, gdf_puntos: gpd.GeoDataFrame, radio_m: float) -> pd.DataFrame:
        """
        Ejecuta la matemática espacial pura:
        Buffers - Unary Union - Intersección - Porcentaje
        """
        if gdf_puntos.empty:
            return pd.DataFrame()
        buffers = gdf_puntos.geometry.buffer(radio_m)
        mancha_cobertura = gpd.GeoDataFrame(
            geometry = [buffers.unary_union],
            crs = self.CRS_METRICO_CDMX
            )
        resultados = []
        for idx, row in self.gdf_poligonos.iterrows():
            nombre_demarcacion = row.get('nombre', f'Poligono_{idx}')
            geometria_demarcacion = row.geometry
            
            area_total_km2 = geometria_demarcacion.area / 1_000_000
            
            ## Interseccion
            interseccion = mancha_cobertura.clip(geometria_demarcacion)
            area_cubierta_total_km2 = 0.0
            if not interseccion.empty:
                area_cubierta_total_km2 = interseccion.geometry.area.sum() / 1_000_000
            
            ## Porcentaje
            porcentaje_cobertura = (area_cubierta_total_km2/area_total_km2)*100 if area_total_km2 > 0 else 0
            resultados.append({
                "Demarcacion": nombre_demarcacion,
                "Area_Total_km2": round(area_total_km2, 2),
                "Area_Cubierta_km2": round(area_cubierta_total_km2, 2),
                "Cobertura_Porcentaje": round(porcentaje_cobertura, 2)
            })
            
        return pd.DataFrame(resultados).sort_values(by="Cobertura_Porcentaje", ascending=False)            
        
    
    def calculate_general_coverage(self, radio_caminable_m: float = 800) -> pd.DataFrame:
        """
        Calcula la cobertura agregada de TODO el sistema de transporte.
        """
        return self._core_coverage_math(self.gdf_estaciones, radio_caminable_m)
    
    def calculate_coverage_by_system(self, radio_caminable_m: float = 800) -> Dict[str, pd.DataFrame]:
        """
        Calcula la cobertura de manera individual iterando por cada sistema.
        Retorna un diccionario: {'metro': DataFrame, 'rtp': DataFrame, ...}
        """
        resultados_por_sistema = {}
        
        if 'sistema' not in self.gdf_estaciones.columns:
            raise KeyError("La propiedad 'sistema' no se encontró en el GeoJSON de las estaciones.")
        
        sistemas_unicos = self.gdf_estaciones['sistema'].dropna().unique()
        
        for sistema in sistemas_unicos:
            gdf_filtrado = self.gdf_estaciones[self.gdf_estaciones['sistema'] == sistema]
            df_resultado = self._core_coverage_math(gdf_filtrado, radio_caminable_m)
            resultados_por_sistema[sistema] = df_resultado
        
        return resultados_por_sistema