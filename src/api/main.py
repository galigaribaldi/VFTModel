"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Endpoint principal para probar la ingesta y validación de datos espaciales.
@route: src/api/main.py
@date: 2026-04-02
@notes: Este archivo levanta el servidor FastAPI y expone la ruta para validar el contrato 
        de datos entre Go y el Modelo VFT.
"""
import uvicorn
import pandas as pd

from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional


from src.api.schemas.schemas import GeoJSONTransportSchema, TipoEntidad
from src.infrastructure.go_client.client import fetch_full_network
from src.core.services.graph_builder import build_and_plot_network
from src.infrastructure.go_client.client_spatial import fetch_territorial_polygons
from src.core.algorithms.spatial_coverate import SpatialCoverageAnalyzer
from src.core.algorithms.topological_indicators import TopologicalIndicatorAnalyzer
from src.core.utils.logger import vft_logger

app = FastAPI(
    title="VFT Model API",
    description="Motor analítico para topología de red de la Ciudad de México y su área Metropolitana.",
    version="1.0.0"
)
@app.get("/api/v1/network/build-auto", summary="Descarga y valida la red completa desde Go")
async def build_network_auto():
    """
    1. Ejecuta el cliente HTTP para ir a la API de Go.
    2. Descarga Líneas y Estaciones simultáneamente.
    3. Pasa el JSON unificado por el escudo de validación Pydantic.
    """
    try:
        raw_data = await fetch_full_network()
        validated_payload = GeoJSONTransportSchema(**raw_data)
        ## Graficar Grafo
        G = build_and_plot_network(validated_payload)
        return {
            "status": "success",
            "nodos": G.number_of_nodes(),
            "aristas": G.number_of_edges()
            }
        
    except ValueError as val_error: # Captura errores de Pydantic
        raise HTTPException(
            status_code=422,
            detail=f"Fallo en el contrato de datos Pydantic: {str(val_error)}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fallo crítico en la comunicación con el servidor Go: {str(e)}"
            )

@app.get("/api/v1/network/spatial-coverage", summary="Calcula el % de cobertura espacial por demarcación")
async def calculate_spatial_coverage(
    radio_m: float = 800.0,
    entidades: Optional[List[str]] = Query(["Ciudad de México", "Estado de México"])
):
    """
    1. Descarga la estaciones de transporte
    2. Descarga los polígonos territoriales de forma concurrente
    3. Cruza las geometrías y calcula qué porcentaje del área tiene acceso caminable
    """
    try:
        geojson_transporte = await fetch_full_network()
        # Llamamos al cliente de polígonos solo con la lista de entidades
        geojson_poligono = await fetch_territorial_polygons(entidades=entidades)
        
        analyzer = SpatialCoverageAnalyzer(geojson_transporte, geojson_poligono)
        df_resultados = analyzer.calculate_general_coverage(radio_caminable_m=radio_m)
        
        vft_logger.info(f"Entidades analizadas: {entidades}")
        vft_logger.info(f"Radio Caminable por metros: {radio_m}")
        
        return {
            "status": "success", 
            "data": df_resultados.to_dict(orient="records")
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fallo en el cálculo de cobertura espacial: {str(e)}"
        )

@app.get("/api/v1/network/topological/capillary-strength", summary="Fuerza Capilar Estricta (Grado Nodal)")
async def get_capillary_strength():
    """
    Calcula la fuerza capilar basada puramente en las conexiones
    declaradas en el grafo topológico.
    """
    try:
        raw_data = await fetch_full_network()
        validated_payload = GeoJSONTransportSchema(**raw_data)
        G = build_and_plot_network(validated_payload) # Obtenemos el grafo
        
        analyzer = TopologicalIndicatorAnalyzer(G)
        df_resultados = analyzer.calculate_capillary_strength()
        
        return {
            "status": "success",
            "indicador": "Fuerza Capilar (Grado Nodal)",
            "data": df_resultados.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis topológico: {str(e)}")

@app.get("/api/v1/network/topological/geo-capillary", summary="Fuerza Capilar por Proximidad (Macro-Hubs)")
async def get_geo_capillary(tolerance_m: float = 100.0):
    """
    Calcula la fuerza capilar agrupando estaciones que están físicamente
    cercanas (definido por tolerance_m) para identificar Hubs intermodales reales.
    """
    try:
        raw_data = await fetch_full_network()
        validated_payload = GeoJSONTransportSchema(**raw_data)
        G = build_and_plot_network(validated_payload)
        
        analyzer = TopologicalIndicatorAnalyzer(G)
        df_resultados = analyzer.calculate_geo_capillary_strength(tolerance_m=tolerance_m)
        
        return {
            "status": "success",
            "parametros": {"tolerancia_metros": tolerance_m},
            "data": df_resultados.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis geo-topológico: {str(e)}")

@app.get("/api/v1/network/topological/detour-factor", summary="Factor de Desviación (Detour Factor)")
async def get_detour_factor(sample_size: int = 500):
    """
    Evalúa la eficiencia de las rutas comparando la distancia real por la red
    contra la distancia en línea recta (Euclidiana).
    """
    try:
        raw_data = await fetch_full_network()
        validated_payload = GeoJSONTransportSchema(**raw_data)
        G = build_and_plot_network(validated_payload)
        
        analyzer = TopologicalIndicatorAnalyzer(G)
        df_resultados = analyzer.calculate_detour_factor(sample_size=sample_size)
        
        return {
            "status": "success",
            "parametros": {"muestra_estadistica": sample_size},
            "data": df_resultados.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en cálculo de Detour Factor: {str(e)}")
    
if __name__ == "__main__":
    """Arranca el servidor de desarrollo Uvicorn en el puerto 8000."""
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)