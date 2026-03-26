"""
@author: Galileo Garibaldi
@date: 2026-03-25
@description: Controlador principal de la API REST que orquesta el flujo VFT.
@route: src/api/main.py
@notes: Endpoint de prueba para validar la correcta instanciación de FastAPI, la ingesta de datos y la conversión a NetworkX.
"""
from fastapi import FastAPI, HTTPException
from src.infrastructure.go_client.client import fetch_geojson
from src.core.services.graph_builder import build_graph_from_geojson
from src.core.utils.logger import vft_logger

app = FastAPI(
    title="VFT Model API -TAICMAM",
    description="Motor analítico para topología de red",
    version="1.0.0"
)

@app.get("/")
def health_check():
    """Verifica que el servidor esté activo"""
    return {
        "status": "VFT Model en línea"
    }
    
@app.get("/prototype/build-graph")
async def prototype_build_graph():
    """Ejecuta el flujo completo de obtención de datos y construye el grafo"""
    vft_logger.info("=== NUEVA SIMULACIÓN SOLICITADA ===")
    
    try:
        geojson_data = await fetch_geojson()
        graph = build_graph_from_geojson(geojson_data)
        return {
            "mensaje": "Grafo de la Higuera construido con éxito",
            "metricas_topologicas":{
                "total_nodos": len(graph.nodes),
                "total_aristas": len(graph.edges)
            }
        }
    except Exception as e:
        vft_logger.error(f"La simulación falló: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno en el Modelo")