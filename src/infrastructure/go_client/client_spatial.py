"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Cliente HTTP asíncrono para la ingesta de límites terriotriales al modelo (polígonos Territoriales)
@route: src/infraestructure/go_client/client_spatial.py
"""

import httpx
import asyncio
from typing import Dict, Any, List
from src.core.utils.logger import vft_logger
from src.infrastructure.go_client.settings import APIMETRO_URL
from src.core.utils.zmvm import ZMVM_ENTIDADES, ZMVM_CVEGEO

async def fetch_territorial_polygons(entidades: List[str] = None) -> Dict[str, Any]:
    """
    Descarga polígonos en formato GeoJSON de manera concurrente para múltiples entidades.
    """
    if entidades is None:
        entidades = ["Ciudad de México", "México"]
        
    async def fetch_single(client: httpx.AsyncClient, entidad: str):
        endpoint = f"{APIMETRO_URL}/mapas/geojsonPoligono"
        
        # REGLA ESTRICTA: Solo enviar 2 parámetros ("existe" y "entidad")
        params = {
            "existe": "true",
            "entidad": entidad
        }
        
        try:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            # Extraer directamente la lista de features para que sea limpio
            return response.json().get("features", [])
        except Exception as e:
            vft_logger.error(f"Error al pedir polígonos para {entidad}: {str(e)}")
            return []

    vft_logger.info(f"Solicitando polígonos territoriales a APIMETRO para: {entidades}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fan-Out: Disparar las peticiones concurrentemente
        tareas = [fetch_single(client, ent) for ent in entidades]
        resultados = await asyncio.gather(*tareas)
        
    # Fan-In: Unir resultados ignorando los vacíos
    features_totales = []
    for features in resultados:
        if features:
            features_totales.extend(features)
            
    vft_logger.info(f"Polígonos combinados exitosamente. Total features: {len(features_totales)}")
    
    return {
        "type": "FeatureCollection",
        "features": features_totales
    }


async def fetch_zmvm_complement(entidades: List[str]) -> Dict[str, Any]:
    """
    Issue #26: descarga las demarcaciones de la ZMVM que pertenecen a entidades NO
    incluidas en `entidades` (con el default CDMX + Estado de México, solo Tizayuca, Hgo.).
    Solo se devuelven claves CVEGEO de la ZMVM: así se evita mezclar homónimos de otras
    entidades (p. ej. "Metepec" existe en Hidalgo y en el Estado de México).
    """
    faltantes = [e for e in ZMVM_ENTIDADES if e not in (entidades or [])]
    if not faltantes:
        return {"type": "FeatureCollection", "features": []}

    extra = await fetch_territorial_polygons(entidades=faltantes)
    features = [
        f for f in extra.get("features", [])
        if f.get("properties", {}).get("cvegeo") in ZMVM_CVEGEO
    ]
    vft_logger.info(f"Complemento ZMVM: {len(features)} demarcaciones de {faltantes}.")
    return {"type": "FeatureCollection", "features": features}
