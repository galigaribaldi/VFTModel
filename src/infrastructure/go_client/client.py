"""
@author: Hernán Galileo Cabrera Garibaldi
@date: 2026-04-25
@description: Cliente asíncrono HTTP para consumir el servicio de GeoJSON en Go.
@route: src/infrastructure/go_client/client.py
@notes: Modificado para descargar estaciones y líneas en paralelo, unificándolas 
        en un solo FeatureCollection para el análisis topológico del Modelo VFT.
"""

import httpx
import asyncio
import json
import os
from src.core.utils.logger import vft_logger

## URL de la API en Go que sirve el GeoJSON de la red de transporte
GO_API_BASE_URL = "http://localhost:8080/movilidad"


# Lista de sistemas aceptados
SISTEMAS_VALIDOS = [
    "METRO", "MB", "RTP", "CBB", 
    "TL", "TROLE", "CC", "MEXIBÚS", "MEXICABLE"
    "INTERURBANO", "SUB"
]

async def fetch_single_geojson(url: str) -> dict:
    """Descarga un endpoint espacial individual y maneja errores."""
    vft_logger.info(f"Solicitando capa espacial a: {url}")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as exc:
        vft_logger.error(f"Fallo de conexión en {url}: {exc}")
        return {"type": "FeatureCollection", "features": []}
    except Exception as e:
        vft_logger.warning(f"Error parseando JSON de {url}: {e}")
        return {"type": "FeatureCollection", "features": []}


async def fetch_full_network() -> dict:
    """
    Descarga las estaciones y líneas directamente de los endpoints espaciales.
    Luego unifica todo en un solo FeatureCollection masivo para el validador VFT.
    """
    vft_logger.info("Construyendo el puente hacia el módulo espacial de Go...")

    # Rutas exactas del módulo espacial según contrato
    url_estaciones = f"{GO_API_BASE_URL}/mapas/geojsonEstacion"#?sistema=TL
    url_lineas = f"{GO_API_BASE_URL}/mapas/geojsonLinea"

    # Ejecutamos las dos peticiones HTTP al mismo tiempo (concurrencia)
    resultados = await asyncio.gather(
        fetch_single_geojson(url_estaciones),
        fetch_single_geojson(url_lineas)
    )
    
    features_unificados = []
    for geojson in resultados:
        features_unificados.extend(geojson.get("features", []))

    # Protocolo Fallback local
    if not features_unificados:
        vft_logger.warning("No se obtuvieron datos. Activando protocolo Fallback (map.geojson local).")
        file_path = os.path.join(os.getcwd(), "map.geojson")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                fallback_data = json.load(f)
                features_unificados = fallback_data.get("features", [])
        except Exception as e:
            vft_logger.error(f"Fallo en Fallback local: {e}")

    vft_logger.info(f"Red extraída: {len(features_unificados)} entidades espaciales listas para VFT.")

    return {
        "type": "FeatureCollection",
        "features": features_unificados
    }