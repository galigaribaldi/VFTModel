"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Endpoint principal para probar la ingesta y validación de datos espaciales.
@route: src/api/main.py
@date: 2026-04-09
@notes:
            Se actualizó para consumir la nueva clase VFTGraphBuilder, permitiendo 
            diferentes modos de construcción topológica (STRICT_TOPOLOGY vs REALISTIC_INTEGRATION)
            y controlando la tolerancia de transbordo peatonal (Q1 por defecto).
        
            Se implementó un Caché en Memoria (Singleton) y delegación a hilos (to_thread)
            para evitar bloqueos (TimeOuts) del Event Loop de FastAPI.        
"""
import uvicorn
import asyncio
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Body
from typing import List, Optional, Union, Tuple


from src.api.schemas.schemas import GeoJSONTransportSchema
from src.infrastructure.go_client.client import fetch_full_network
from src.core.services.graph_builder import VFTGraphBuilder
from src.infrastructure.go_client.client_spatial import fetch_territorial_polygons
from src.core.algorithms.topologicalIndicators.spatial_coverate import SpatialCoverageAnalyzer
from src.core.algorithms.topologicalIndicators.capillar_strength import CapillaryStrengthAnalyzer
from src.core.algorithms.topologicalIndicators.detaur_factor import DetourFactorAnalyzer
from src.core.utils.logger import vft_logger

app = FastAPI(
    title="VFT Model API",
    description="Motor analítico para topología de red de la Ciudad de México y su área Metropolitana.",
    version="1.0.0"
)

# Constante extraída del diccionario de la clase para mantener consistencia
DEFAULT_TOLERANCE = VFTGraphBuilder.STATISTICAL_THRESHOLDS["Q1"]

## Grafo topológico en memoria Caché
GRAPH_CACHE = {}

async def get_or_build_graph(mode: str, tolerance_m: float):
    """
    Recupera el grafo de la memoria si ya fue construido con esos parámetros.
    Si no existe, lo construye en un hilo separado para no bloquear FastAPI.
    Delegamos el cálculo pesado (CPU-bound) a un hilo de fondo
    Instanciamos el Builder
    Guardamos en caché
    """
    cache_key = f"{mode}_{tolerance_m}"
    
    if cache_key in GRAPH_CACHE:
        vft_logger.info(f"⚡ Recuperando grafo desde caché en memoria: [{cache_key}]")
        return GRAPH_CACHE[cache_key]
        
    vft_logger.info(f"⏳ Construyendo grafo desde cero para: [{cache_key}]")
    raw_data = await fetch_full_network()
    validated_payload = GeoJSONTransportSchema(**raw_data)

    builder = VFTGraphBuilder(validated_payload)
    G = await asyncio.to_thread(builder.build_graph, mode, tolerance_m)    
    
    GRAPH_CACHE[cache_key] = G
    return G


@app.get("/api/v1/network/build-auto", summary="Descarga y valida la red completa (Cache Warming)")
async def build_network_auto(
    mode: str = Query("REALISTIC_INTEGRATION", description="Modos: STRICT_TOPOLOGY o REALISTIC_INTEGRATION"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Distancia máxima en metros para transbordos peatonales.")
):
    """
    1. Ejecuta el cliente HTTP para ir a la API de Go.
    2. Descarga Líneas y Estaciones simultáneamente.
    3. Pasa el JSON unificado por el escudo de validación Pydantic.
    Llama a este endpoint al iniciar el servidor 
    para que el grafo quede listo en la memoria RAM para los demás endpoints.
    """
    try:
        G = await get_or_build_graph(mode, tolerance_m)
        return {
            "status": "success",
            "mensaje": "Grafo listo y en caché.",
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
    radio_m: float = Query(800.0, description="Radio de influencia caminable desde cada estación."),
    entidades: Optional[List[str]] = Query(["Ciudad de México", "Estado de México"], description="Entidades federativas a analizar")
):
    """
    Analiza qué porcentaje del área de cada alcaldía/municipio está cubierta por el transporte.
    Nota: Este análisis es puramente geográfico (buffers), no depende de la topología del grafo.
    """
    try:
        geojson_transporte = await fetch_full_network()
        geojson_poligono = await fetch_territorial_polygons(entidades=entidades)
        
        analyzer = SpatialCoverageAnalyzer(geojson_transporte, geojson_poligono)
        # También mandamos el cálculo espacial a un hilo separado por ser pesado
        df_resultados = await asyncio.to_thread(analyzer.calculate_general_coverage, radio_m)
        
        return {"status": "success", "data": df_resultados.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo en cobertura espacial: {str(e)}")

@app.get("/api/v1/network/topological/capillary-strength", summary="Fuerza Capilar (Grado Nodal Central)")
async def get_capillary_strength(
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia del grafo para transbordos"),
    snap_tolerance_m: float = Query(25.0, description="Tolerancia interna para agrupar nombres"),
    limit: int = Query(100, description="Límite de resultados para no congelar Swagger UI")
):
    """
    Calcula la Fuerza Capilar. Al usar REALISTIC_INTEGRATION, las estaciones que actúan 
    como hubs multimodales aumentarán masivamente su grado nodal.
    """
    try:
        G = await get_or_build_graph(mode, tolerance_m)
        
        vft_logger.info("Calculando Fuerza Capilar...")
        analyzer = CapillaryStrengthAnalyzer(G)
        df_resultados = await asyncio.to_thread(analyzer.calculate_capillary_strength, snap_tolerance_m)
        df_limpio = df_resultados.where(pd.notna(df_resultados), None)
        df_recortado = df_limpio.head(limit)
        
        return {
            "status": "success",
            "parametros": {
                "modo_grafo": mode, 
                "tolerancia_transbordo_grafo_m": tolerance_m,
                "tolerancia_agrupacion_algoritmo_m": snap_tolerance_m
                },
            "data": df_recortado.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis geo-topológico: {str(e)}")

@app.get("/api/v1/network/topological/geo-capillary", summary="Fuerza Capilar por Proximidad (Reporte de Macro-Hubs)")
async def get_geo_capillary(
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia física para el grafo"),
    group_tolerance_m: float = Query(100.0, description="Tolerancia del algoritmo para agrupar estaciones en un solo Hub"),
    limit: int = Query(100, description="Límite de resultados para no congelar Swagger UI")
):
    """
    A diferencia de la fuerza capilar simple, este endpoint agrupa estaciones 
    cercanas bajo un mismo nombre de 'Macro-Hub' para el análisis.
    """
    try:
        G = await get_or_build_graph(mode, tolerance_m)
        
        vft_logger.info("Calculando Fuerza Capilar por Proximidad...")
        analyzer = CapillaryStrengthAnalyzer(G)
        df_resultados = await asyncio.to_thread(analyzer.calculate_geo_capillary_strength, group_tolerance_m)
        df_limpio = df_resultados.where(pd.notna(df_resultados), None)
        df_recortado = df_limpio.head(limit)
        
        return {
            "status": "success",
            "parametros": {
                "modo_grafo": mode,
                "tolerancia_grafo_m": tolerance_m,
                "tolerancia_agrupacion_hubs_m": group_tolerance_m
                },
            "data": df_recortado.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis geo-topológico: {str(e)}")

@app.get("/api/v1/network/topological/detour-factor", summary="Factor de Desviación (Detour Factor) General")
async def get_detour_factor(
    sample_size: int = Query(500, description="Tamaño de la muestra estadística"),
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia de transbordo")):
    """
    Evalúa la eficiencia de las rutas. Con REALISTIC_INTEGRATION, el modelo 
    descubrirá atajos multimodales usando transbordos peatonales.
    """
    try:
        G = await get_or_build_graph(mode, tolerance_m)
        
        analyzer = DetourFactorAnalyzer(G)
        df_resultados = await asyncio.to_thread(analyzer.calculate_detaur_factor, sample_size)
        clean_df = df_resultados.where(pd.notna(df_resultados), None)
        
        return {
            "status": "success",
            "parametros": {
                "muestra_estadistica": sample_size,
                "modo_grafo": mode,
                "tolerancia_transbordo_m": tolerance_m
                },
            "data": clean_df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en cálculo de Detour Factor: {str(e)}")

@app.post("/api/v1/network/topological/detour-factor/any-node", summary="Detour Factor desde Coordenadas Arbitrarias")
async def get_detour_factor_any_node(
    origen: Union[str, Tuple[float, float]] = Body(..., description="ID del nodo o tupla (lon, lat)"),
    destino: Union[str, Tuple[float, float]] = Body(..., description="ID del nodo o tupla (lon, lat)"),
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia de transbordo")
):
    """
    Calcula la eficiencia espacial entre dos puntos arbitrarios, incluyendo 
    la caminata hacia la estación válida más cercana.
    """
    try:
        G = await get_or_build_graph(mode, tolerance_m)
        
        analyzer = DetourFactorAnalyzer(G)
        
        df_resultados = await asyncio.to_thread(
            analyzer.calculate_any_node_detaur_factor, 
            origen, 
            destino
        )
        
        df_limpio = df_resultados.where(pd.notna(df_resultados), None)
        
        return {
            "status": "success",
            "parametros": {
                "origen": origen,
                "destino": destino,
                "modo_grafo": mode,
                "tolerancia_transbordo_m": tolerance_m
                },
            "data": df_limpio.to_dict(orient="records")
        }
    except Exception as e:
        vft_logger.error(f"Error en Detour Factor Arbitrario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudo calcular la ruta: {str(e)}")

if __name__ == "__main__":
    """Arranca el servidor de desarrollo Uvicorn en el puerto 8000."""
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)