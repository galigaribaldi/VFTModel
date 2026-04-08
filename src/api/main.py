"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Endpoint principal para probar la ingesta y validación de datos espaciales.
@route: src/api/main.py
@date: 2026-04-02
@notes: Este archivo levanta el servidor FastAPI y expone la ruta para validar el contrato 
        de datos entre Go y el Modelo VFT.
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from src.api.schemas.schemas import GeoJSONTransportSchema, TipoEntidad
from src.infrastructure.go_client.client import fetch_full_network
from src.core.services.graph_builder import build_and_plot_network
from src.infrastructure.go_client.client_spatial import fetch_territorial_polygons
from src.core.algorithms.spatial_coverate import SpatialCoverageAnalyzer
import pandas as pd


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
        grafo_vft = build_and_plot_network(validated_payload)

        # 3. Contabilidad de lo validado
        estaciones_count = sum(
            1 for f in validated_payload.features 
            if f.properties.tipo_entidad == TipoEntidad.estacion
            )
        rutas_count = sum(
            1 for f in validated_payload.features 
            if f.properties.tipo_entidad == TipoEntidad.ruta
            )

        return {
            "status": "success",
            "message": "Datos descargados de Go y validados contra el contrato VFT.",
            "data": {
                "total_features": len(validated_payload.features),
                "estaciones_validadas": estaciones_count,
                "rutas_validadas": rutas_count
            }
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
        
        resultados_json = df_resultados.to_dict(orient="records")
        
        return {
            "status": "success",
            "parametros": {
                "radio_caminable_metros": radio_m,
                "entidades_analizadas": entidades
            },
            "data": resultados_json
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fallo en el cálculo de cobertura espacial: {str(e)}"
        )
    
if __name__ == "__main__":
    """Arranca el servidor de desarrollo Uvicorn en el puerto 8000."""
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)