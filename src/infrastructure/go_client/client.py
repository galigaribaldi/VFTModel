"""
@author: Galileo Garibaldi
@date: 2026-03-25
@description: Cliente asíncrono HTTP para consumir el servicio de GeoJSON en Go.
@route: src/infrastructure/go_client/client.py
@notes: Contiene un fallback para leer 'map.geojson' localmente si el servidor Go está inactivo, asegurando que el desarrollo no se detenga.
"""

import httpx
import json
import os
from src.core.utils.logger import vft_logger

async def fetch_geojson(api_url: str = "http://localhost:8080/movilidad/mapas/geojsonLinea") -> dict:
    """Obtiene el GeoJSON de la red desde la API en Go de forma asíncrona.

    Args:
        api_url (str): La URL del endpoint en Go que sirve el mapa.

    Returns:
        dict: Un diccionario de Python que representa el FeatureCollection GeoJSON.
    """
    vft_logger.info("Petición a APIMETRO", api_url)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            response.raise_for_status()
            vft_logger.info("Datos espaciales descargados exitosamente desde Go.")
            return response.json()
    except httpx.RequestError as exc:
        vft_logger.warning(f"Fallo de conexión con Go: {exc}. Activando protocolo Fallback (Archivo Local).")
        
        file_path = os.path.join(os.getcwd(), "map.geojson")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            vft_logger.error(f"Error crítico: No se pudo leer el archivo local fallback: {e}")
            raise e