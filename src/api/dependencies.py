"""
@author: Hernán Galileo Cabrera Garibaldi
@description:   Dependencias Compartidas entre Routers de al API VFT
                Centraliza el caché de grafos y el helper get_or_build_graph
                para que tanto main.py como los routers accedan a la misma instancia
@route: src/api/dependences.py
@date: 03-06-2026
"""

import asyncio
from src.api.schemas.schemas import GeoJSONTransportSchema
from src.infrastructure.go_client.client import fetch_full_network
from src.core.services.graph_builder import VFTGraphBuilder
from src.core.utils.logger import vft_logger

## Constante de rolerancia pro defecto (Q1)
DEFAULT_TOLERANCE = VFTGraphBuilder.STATISTICAL_THRESHOLDS["Q1"]

## Caché en memoria - Singleton por proceso
GRAPH_CACHE = {}

async def get_or_build_graph(mode: str, tolerance_m: float):
    """
    Recupera el grafo de la memoria si ya fue construido con esos parámetros.
    Si no existe, lo construye en un hilo separado para no bloquear FASTAPI.
    """
    cache_key = f"{mode}_{tolerance_m}"
    if cache_key in GRAPH_CACHE:
        vft_logger.info(f"Recuperando grafo caché desde memoria: [{cache_key}]")
        return GRAPH_CACHE[cache_key]
    vft_logger.info(f" Cosnstruyendo grafo desde cero para: [{cache_key}]")
    raw_data = await fetch_full_network()
    validated_payload = GeoJSONTransportSchema(**raw_data)
    builder = VFTGraphBuilder(validated_payload)
    G = await asyncio.to_thread(builder.build_graph, mode, tolerance_m)
    GRAPH_CACHE[cache_key] = G
    return G