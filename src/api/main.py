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
import os
import uvicorn
import asyncio
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(os.getenv("ENV_FILE", ".env.local"))
from typing import List, Optional, Union, Tuple


from src.api.schemas.schemas import GeoJSONTransportSchema
from src.infrastructure.go_client.client import fetch_full_network

from src.core.services.graph_builder import VFTGraphBuilder
from src.api.dependencies import (
    DEFAULT_TOLERANCE, get_or_build_graph, get_scc_report,
    get_giant_component, get_travel_time_report, get_betweenness_report,
    get_profile_report, T_CACHE, B_CACHE, P_CACHE, GRAPH_CACHE
)
from src.core.algorithms.composite.network_profile import NetworkProfiler
from src.api.routes import router as geo_router

from src.infrastructure.go_client.client_spatial import fetch_territorial_polygons
from src.core.algorithms.spatial.spatial_coverage import SpatialCoverageAnalyzer
from src.core.algorithms.topological.capillar_strength import CapillaryStrengthAnalyzer
from src.core.algorithms.topological.detaurFactor import DetourFactorOrchestrator
from src.core.algorithms.topological.average_travel_time import AverageTravelTimeOrchestrator
from src.core.algorithms.topological.betweenness_centrality import BetweennessOrchestrator
from src.core.utils.logger import vft_logger

app = FastAPI(
    title="VFT Model API",
    description="Motor analítico para topología de red de la Ciudad de México y su área Metropolitana.",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(geo_router)

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

@app.get("/get_detour_factor")
async def get_detour_factor(
    muestra: int = Query(500, description="Tamaño de la muestra estadística"),
    seed: Optional[int] = Query(None, description="Semilla para reproducibilidad"),
    visualize: bool = Query(False, description="Si es True, devuelve geometrías para el mapa"),
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia de transbordo")
):
    """
    Calcula el Factor de Desviación masivo. 
    Ahora puede devolver datos tabulares o enriquecidos para el visualizador.
    """
    try:
        G = await get_or_build_graph(mode, tolerance_m)
        
        # Instanciamos el Orquestador (Inyección de dependencia del grafo)
        orchestrator = DetourFactorOrchestrator(G)
        
        # Ejecución delegada a un hilo para no bloquear el event loop
        resultados = await asyncio.to_thread(
            orchestrator.calculate_sample_routes, 
            muestra, 
            seed, 
            visualize # <--- Aquí pasamos el flag de retorno
        )
        
        # Si no es para visualizar, convertimos el DataFrame a diccionario
        data_to_send = resultados if visualize else resultados.to_dict(orient="records")
        
        return {
            "status": "success",
            "parametros": {
                "muestra_estadistica": muestra,
                "modo_grafo": mode,
                "visualizacion_activa": visualize
            },
            "data": data_to_send
        }
    except Exception as e:
        vft_logger.error(f"Error en Detour Factor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_detour_factor_any_node")
async def get_detour_factor_any_node(
    origen: Union[str, Tuple[float, float]] = Body(..., description="ID del nodo o tupla (lon, lat)"),
    destino: Union[str, Tuple[float, float]] = Body(..., description="ID del nodo o tupla (lon, lat)"),
    visualize: bool = Query(True, description="Por defecto devuelve geometrías para rutas únicas"),
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia de transbordo")
):
    """
    Calcula la eficiencia entre dos puntos, devolviendo métricas detalladas 
    y la geometría de la ruta paso a paso.
    """
    try:
        G = await get_or_build_graph(mode, tolerance_m)
        
        orchestrator = DetourFactorOrchestrator(G)
        
        # Llamada al método de ruta personalizada
        res = await asyncio.to_thread(
            orchestrator.calculate_custom_route, 
            origen, 
            destino, 
            visualize
        )
        
        if (visualize and not res) or (not visualize and res.empty):
            return {"status": "no_path", "message": "No se encontró una ruta válida entre los puntos."}

        data_to_send = res if visualize else res.to_dict(orient="records")

        return {
            "status": "success",
            "data": data_to_send
        }
    except Exception as e:
        vft_logger.error(f"Error en Detour Factor Arbitrario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en el motor: {str(e)}")

@app.get("/api/v1/network/topological/scc-analysis",
         summary="Diagnóstico de Componentes Fuertemente Conexas (SCC)")
async def get_scc_analysis(
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia de transbordo")
):
    """
    Verifica la estructura de conectividad del grafo (Tarjan).
    Prerequisito para Fase 3: si la componente gigante > 80% → apto para T y B.
    """
    try:
        G = await get_or_build_graph(mode, tolerance_m)
        report = get_scc_report(mode, tolerance_m)
        if report is None:
            raise HTTPException(500, "SCC analysis no disponible — reconstruir grafo.")
        return {
            "status": "success",
            "parametros": {"modo_grafo": mode, "tolerancia_transbordo_m": tolerance_m},
            "data": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis SCC: {str(e)}")

@app.get("/api/v1/network/topological/average-travel-time",
         summary="T — Tiempo Promedio de Viaje (Indicador VFT Fase 3)")
async def get_average_travel_time(
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia de transbordo")
):
    """
    Calcula T = promedio de caminos más cortos ponderados sobre la componente gigante.
    Prerequisito: SCC verificado y apto (componente gigante > 80%).
    Nota: Primera ejecución tarda ~2-5 min por all-pairs shortest paths.
    """
    try:
        await get_or_build_graph(mode, tolerance_m)

        cached = get_travel_time_report(mode, tolerance_m)
        if cached:
            return {
                "status": "success",
                "parametros": {"modo_grafo": mode, "tolerancia_transbordo_m": tolerance_m},
                "data": cached
            }

        G_scc = get_giant_component(mode, tolerance_m)
        if G_scc is None:
            raise HTTPException(500, "Componente gigante no disponible — reconstruir grafo.")

        orchestrator = AverageTravelTimeOrchestrator(G_scc)
        report = await asyncio.to_thread(orchestrator.analyze)

        T_CACHE[f"{mode}_{tolerance_m}"] = report
        return {
            "status": "success",
            "parametros": {"modo_grafo": mode, "tolerancia_transbordo_m": tolerance_m},
            "data": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en cálculo de T: {str(e)}")


@app.get("/api/v1/network/topological/betweenness-centrality",
         summary="B — Centralidad de Intermediación (Indicador VFT Fase 3)")
async def get_betweenness_centrality(
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia de transbordo"),
    limit: int = Query(100, description="Límite de resultados para no congestar Swagger UI")
):
    """
    Calcula B(v) = centralidad de intermediación normalizada sobre la componente gigante.
    Prerequisito: SCC verificado y apto (componente gigante > 80%).
    Nota: Primera ejecución tarda ~30-90s (algoritmo de Brandes).
    """
    try:
        await get_or_build_graph(mode, tolerance_m)

        cached = get_betweenness_report(mode, tolerance_m)
        if cached:
            df_ranking = cached["ranking"]
            df_limpio = df_ranking.where(pd.notna(df_ranking), None).head(limit)
            return {
                "status": "success",
                "parametros": {"modo_grafo": mode, "tolerancia_transbordo_m": tolerance_m},
                "data": {
                    "summary": cached["summary"],
                    "ranking": df_limpio.to_dict(orient="records")
                }
            }

        G_scc = get_giant_component(mode, tolerance_m)
        if G_scc is None:
            raise HTTPException(500, "Componente gigante no disponible — reconstruir grafo.")

        orchestrator = BetweennessOrchestrator(G_scc)
        report = await asyncio.to_thread(orchestrator.analyze)

        B_CACHE[f"{mode}_{tolerance_m}"] = report

        df_ranking = report["ranking"]
        df_limpio = df_ranking.where(pd.notna(df_ranking), None).head(limit)
        return {
            "status": "success",
            "parametros": {"modo_grafo": mode, "tolerancia_transbordo_m": tolerance_m},
            "data": {
                "summary": report["summary"],
                "ranking": df_limpio.to_dict(orient="records")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en cálculo de B: {str(e)}")


@app.get("/api/v1/network/topological/network-profile",
         summary="Clasificación Garibelt — Tablero de Diagnóstico Topológico VFT")
async def get_network_profile(
    mode: str = Query("REALISTIC_INTEGRATION", description="Modo de construcción del grafo"),
    tolerance_m: float = Query(DEFAULT_TOLERANCE, description="Tolerancia de transbordo"),
    radio_cobertura_m: float = Query(800.0, description="Radio peatonal para dimensión de accesibilidad"),
    entidades: Optional[List[str]] = Query(["Ciudad de México", "Estado de México"], description="Entidades para análisis de cobertura"),
    sample_size_di: int = Query(500, description="Muestra de pares O-D para Detour Factor"),
    seed_di: Optional[int] = Query(42, description="Semilla para reproducibilidad del Detour Factor"),
):
    """
    Clasificación Garibelt: tablero de diagnóstico topológico multi-dimensional de la ZMVM.
    Compila los 5 indicadores disponibles en la Escala Garibelt: crítico / débil / aceptable / idóneo.
    Nota: primera ejecución tarda varios minutos si T y B no están en caché.
    Recomendado: ejecutar warmup-all en Transport-GIS antes de llamar este endpoint.
    """
    try:
        await get_or_build_graph(mode, tolerance_m)

        cached = get_profile_report(mode, tolerance_m)
        if cached:
            scc_r = get_scc_report(mode, tolerance_m)
            scc_stats = None
            if scc_r:
                _g = scc_r["giant_component"]
                scc_stats = {
                    "giant_component_nodes": _g["nodes"],
                    "isolated_nodes": scc_r["total_nodes"] - _g["nodes"],
                    "pct_giant": _g["pct_of_total_nodes"],
                }
            return {
                "status": "success",
                "parametros": {"modo_grafo": mode, "tolerancia_transbordo_m": tolerance_m},
                "data": {**cached["report"], "scc_stats": scc_stats},
            }

        G_scc = get_giant_component(mode, tolerance_m)
        G = GRAPH_CACHE.get(f"{mode}_{tolerance_m}")
        if G_scc is None or G is None:
            raise HTTPException(500, "Componente gigante no disponible — reconstruir grafo.")

        scc_r = get_scc_report(mode, tolerance_m)
        scc_stats = None
        if scc_r:
            _g = scc_r["giant_component"]
            scc_stats = {
                "giant_component_nodes": _g["nodes"],
                "isolated_nodes": scc_r["total_nodes"] - _g["nodes"],
                "pct_giant": _g["pct_of_total_nodes"],
            }

        # T — usa caché si disponible
        t_data = get_travel_time_report(mode, tolerance_m)
        if not t_data:
            t_orch = AverageTravelTimeOrchestrator(G_scc)
            t_data = await asyncio.to_thread(t_orch.analyze)
            T_CACHE[f"{mode}_{tolerance_m}"] = t_data
        travel_time_min = t_data["T_average_travel_time_minutes"]

        # B — usa caché si disponible
        b_data = get_betweenness_report(mode, tolerance_m)
        if not b_data:
            b_orch = BetweennessOrchestrator(G_scc)
            b_data = await asyncio.to_thread(b_orch.analyze)
            B_CACHE[f"{mode}_{tolerance_m}"] = b_data
        betweenness_df = b_data["ranking"]

        # Capilar y Detour — rápidos, sin caché individual
        cap_analyzer = CapillaryStrengthAnalyzer(G)
        capillar_df = await asyncio.to_thread(cap_analyzer.calculate_capillary_strength)

        detour_orch = DetourFactorOrchestrator(G)
        detour_df = await asyncio.to_thread(
            detour_orch.calculate_sample_routes, sample_size_di, seed_di
        )

        # Cobertura — graceful degradation si Go backend no disponible
        coverage_df = None
        try:
            geojson_transporte = await fetch_full_network()
            geojson_poligono = await fetch_territorial_polygons(entidades=entidades)
            cov_analyzer = SpatialCoverageAnalyzer(geojson_transporte, geojson_poligono)
            coverage_df = await asyncio.to_thread(
                cov_analyzer.calculate_general_coverage, radio_cobertura_m
            )
        except Exception:
            vft_logger.warning("Garibelt: cobertura no disponible — dimensión omitida.")

        profiler = NetworkProfiler(
            coverage_df=coverage_df,
            capillar_df=capillar_df,
            detour_df=detour_df,
            travel_time_min=travel_time_min,
            betweenness_df=betweenness_df,
            G=G,
        )
        result = await asyncio.to_thread(profiler.build_profile)

        report = {
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "indicador_fuente": d.indicador_fuente,
                    "valor_bruto": d.valor_bruto,
                    "valor_normalizado": d.valor_normalizado,
                    "banda": d.banda,
                    "metrica_descripcion": d.metrica_descripcion,
                }
                for d in result.dimensions
            ],
            "node_enrichment_count": len(result.node_enrichment),
            "parametros_calculo": {
                "radio_cobertura_m": radio_cobertura_m,
                "sample_size_di": sample_size_di,
                "seed_di": seed_di,
            },
            "scc_stats": scc_stats,
        }

        P_CACHE[f"{mode}_{tolerance_m}"] = {
            "report": report,
            "node_enrichment": result.node_enrichment,
        }

        return {
            "status": "success",
            "parametros": {"modo_grafo": mode, "tolerancia_transbordo_m": tolerance_m},
            "data": report,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en Clasificación Garibelt: {str(e)}")


if __name__ == "__main__":
    """Arranca el servidor de desarrollo Uvicorn en el puerto 8000."""
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)