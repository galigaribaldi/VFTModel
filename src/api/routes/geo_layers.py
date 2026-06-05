"""
@author: Hernán Galileo Cabrera Garibaldi
@description:
        Output adapters GeoJSON para los tres indicadores topológicos VFT.
        Este módulo es exclusivamente una capa de serialización — no contiene
        lógica analítica. Transforma los DataFrames de los algoritmos en
        FeatureCollections consumibles por Transport-gis-zmvm-mjg y QGIS.
@route: src/api/routes/geo_layers.py
@date: 03-06-2026
@notes:
    Contrato de datos definido en VFT_CLIENT_SPEC.md (raíz del repo).
    Todas las geometrías se entregan en EPSG:4326 (WGS84).
    Los algoritmos trabajan internamente en EPSG:32614; se reprojecta antes de serializar.
"""
import ast
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

import geopandas as gpd
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from shapely.geometry import Point, mapping

from src.api.dependencies import DEFAULT_TOLERANCE, get_or_build_graph
from src.infrastructure.go_client.client import fetch_full_network
from src.infrastructure.go_client.client_spatial import fetch_territorial_polygons
from src.core.algorithms.topologicalIndicators.spatial_coverate import SpatialCoverageAnalyzer
from src.core.algorithms.topologicalIndicators.capillar_strength import CapillaryStrengthAnalyzer
from src.core.algorithms.topologicalIndicators.detaurFactor import DetourFactorOrchestrator

from src.core.utils.logger import vft_logger

## Router
router = APIRouter(
    prefix="/api/v1/network/geolayers",
    tags=["GeoLayers"]
)
# ----------------------------------------------------------------------
## Auxiliares de serialización
# ----------------------------------------------------------------------

def _build_feature_collection(
    indicador: str, 
    layer: str, 
    feature: list,
    parametros: dict) -> dict:
    """Envuelve una lista de Features en la envoltura estándar VFT."""
    return {
        "type": "FeatureCollection",
        "metadata": {
            "indicador":    indicador,
            "layer":        layer,
            "n_features":   len(feature),
            "crs":          "EPSG:4326",
            "fetched_at":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parametros": parametros
        },
        "features": feature
    }
    
# ----------------------------------------------------------------------
## Clasificación de Categorias (Umbrales supuestos)
# ----------------------------------------------------------------------

def _clasify_coverage(pct: float) -> str:
    if pct > 60:
        return "alta"
    if pct >= 30:
        return "media"
    return "baja"

def _clasify_node(fc_total: float) -> str:
    if fc_total > 20:
        return "hub_principal"
    if fc_total > 10:
        return "hub_secundario"
    if fc_total > 6:
        return "nodo_relevante"
    return "nodo_basico"

def _clasify_diff(factor: float) -> str:
    if factor <= 1.3:
        return "eficiente"
    if factor <= 1.6:
        return "moderado"
    if factor <= 2.0:
        return "alto"
    return "critico"

# ----------------------------------------------------------------------
## Sección D — Endpoint /coverage
# ----------------------------------------------------------------------

@router.get("/coverage", summary="Cobertura Espacial como FeatureCollection GeoJSON")
async def get_geolayer_coverage(
    layer:       str                 = Query("cobertura_por_alcaldia",
                                             description="cobertura_por_alcaldia | estaciones | cobertura_800m"),
    radio_m:     float               = Query(800.0,  description="Radio de buffer peatonal en metros"),
    entidades:   Optional[List[str]] = Query(None,   description="Entidades federativas (default: Ciudad de México, Estado de México)"),
    mode:        str                 = Query("REALISTIC_INTEGRATION"),
    tolerance_m: float               = Query(DEFAULT_TOLERANCE)
):
    if entidades is None:
        entidades = ["Ciudad de México", "Estado de México"]
    try:
        # ── cobertura_por_alcaldia ─────────────────────────────────────────
        if layer == "cobertura_por_alcaldia":
            net, pol = await asyncio.gather(
                fetch_full_network(),
                fetch_territorial_polygons(entidades=entidades)
            )
            analyzer = SpatialCoverageAnalyzer(net, pol)
            df       = await asyncio.to_thread(analyzer.calculate_general_coverage, radio_m)
            gdf_pol  = analyzer.gdf_poligonos.to_crs("EPSG:4326")

            features = []
            for _, row in df.iterrows():
                nombre  = row["Demarcacion"]
                pol_row = gdf_pol[gdf_pol["nombre"] == nombre]
                if pol_row.empty:
                    continue
                geom    = pol_row.iloc[0].geometry
                cob_pct = row["Cobertura_Porcentaje"]
                features.append({
                    "type": "Feature",
                    "geometry": mapping(geom),
                    "properties": {
                        "id":                  nombre,
                        "nombre":              nombre,
                        "indicador":           "cobertura",
                        "layer":               layer,
                        "area_total_km2":      row["Area_Total_km2"],
                        "area_cubierta_km2":   row["Area_Cubierta_km2"],
                        "cobertura_pct":       cob_pct,
                        "cobertura_deficit":   round(100 - cob_pct, 2),
                        "categoria_cobertura": _clasify_coverage(cob_pct)
                    }
                })

        # ── estaciones ────────────────────────────────────────────────────
        elif layer == "estaciones":
            net          = await fetch_full_network()
            features_est = [f for f in net["features"]
                            if f.get("properties", {}).get("tipo_entidad") == "estacion"]
            gdf_est      = gpd.GeoDataFrame.from_features(features_est, crs="EPSG:4326")
            gdf_est      = gdf_est.drop_duplicates(subset=["nombre", "sistema"])

            features = []
            for _, row in gdf_est.iterrows():
                features.append({
                    "type": "Feature",
                    "geometry": mapping(row.geometry),
                    "properties": {
                        "id":            str(row.get("id", "")),
                        "nombre":        row.get("nombre", "Sin nombre"),
                        "indicador":     "cobertura",
                        "layer":         layer,
                        "sistema":       str(row.get("sistema", "")),
                        "tipo_entidad":  row.get("tipo_entidad", "estacion"),
                        "sistemas_count": 1
                    }
                })

        # ── cobertura_800m ────────────────────────────────────────────────
        elif layer == "cobertura_800m":
            net          = await fetch_full_network()
            features_est = [f for f in net["features"]
                            if f.get("properties", {}).get("tipo_entidad") == "estacion"]
            gdf_est      = gpd.GeoDataFrame.from_features(features_est, crs="EPSG:4326")
            gdf_est_m    = gdf_est.to_crs("EPSG:32614")
            mancha       = gdf_est_m.geometry.buffer(radio_m).unary_union
            gdf_mancha   = gpd.GeoDataFrame(geometry=[mancha], crs="EPSG:32614").to_crs("EPSG:4326")
            geom_mancha  = gdf_mancha.iloc[0].geometry

            features = [{
                "type": "Feature",
                "geometry": mapping(geom_mancha),
                "properties": {
                    "id":        "cobertura_800m",
                    "nombre":    f"Cobertura {int(radio_m)}m",
                    "indicador": "cobertura",
                    "layer":     layer,
                    "radio_m":   int(radio_m)
                }
            }]

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Layer '{layer}' no reconocida. Opciones: cobertura_por_alcaldia, estaciones, cobertura_800m"
            )

        return _build_feature_collection(
            indicador  = "cobertura",
            layer      = layer,
            feature    = features,
            parametros = {"radio_m": radio_m, "entidades": entidades}
        )

    except HTTPException:
        raise
    except Exception as e:
        vft_logger.error(f"Error en GeoLayer coverage [{layer}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en GeoLayer coverage: {str(e)}")

# ----------------------------------------------------------------------
## Sección E — Endpoint /capillary
# ----------------------------------------------------------------------

@router.get("/capillary", summary="Fuerza Capilar como FeatureCollection GeoJSON")
async def get_geolayer_capillary(
    layer:            str   = Query("fc_puntos",
                                    description="fc_puntos | fc_hubs"),
    min_fc:           int   = Query(3,     description="Umbral mínimo de Fuerza Capilar (solo fc_puntos)"),
    top_n:            int   = Query(20,    description="Top N macro-hubs (solo fc_hubs)"),
    snap_tolerance_m: float = Query(25.0,  description="Tolerancia de agrupación nodal interna"),
    hub_tolerance_m:  float = Query(100.0, description="Radio de agrupación geográfica para macro-hubs"),
    mode:             str   = Query("REALISTIC_INTEGRATION"),
    tolerance_m:      float = Query(DEFAULT_TOLERANCE)
):
    try:
        G        = await get_or_build_graph(mode, tolerance_m)
        analyzer = CapillaryStrengthAnalyzer(G)

        # ── fc_puntos ──────────────────────────────────────────────────────
        if layer == "fc_puntos":
            df = await asyncio.to_thread(analyzer.calculate_capillary_strength, snap_tolerance_m)
            df = df[df["Fuerza_Capilar_Total"] >= min_fc]

            features = []
            for _, row in df.iterrows():
                lon, lat = ast.literal_eval(row["Nodo_ID"])
                sistemas = row["Sistemas_Integrados"] if isinstance(row["Sistemas_Integrados"], list) \
                           else [row["Sistemas_Integrados"]]
                fc_total = row["Fuerza_Capilar_Total"]
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "id":             row["Nodo_ID"],
                        "nombre":         row["Estacion"],
                        "indicador":      "capillary",
                        "layer":          layer,
                        "fc_total":       fc_total,
                        "cx_entrada":     row["Conexiones_Entrada"],
                        "cx_salida":      row["Conexiones_Salida"],
                        "sistemas":       json.dumps(sistemas),
                        "sistemas_count": len(sistemas),
                        "tipo_nodo":      _clasify_node(fc_total)
                    }
                })

        # ── fc_hubs ────────────────────────────────────────────────────────
        elif layer == "fc_hubs":
            df = await asyncio.to_thread(
                analyzer.calculate_geo_capillary_strength,
                hub_tolerance_m,
                snap_tolerance_m
            )
            df = df.head(top_n)

            features = []
            for _, row in df.iterrows():
                lon, lat = row["Pos_Representativa"]   # tupla (lon, lat) WGS84
                sistemas = row["Sistemas_Integrados"] if isinstance(row["Sistemas_Integrados"], list) \
                           else [row["Sistemas_Integrados"]]
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "id":                   row["Macro_Hub"],
                        "nombre":               row["Macro_Hub"],
                        "indicador":            "capillary",
                        "layer":                layer,
                        "estaciones_agrupadas": row["Estaciones_Agrupadas"],
                        "fc_total":             row["Fuerza_Capilar_Total"],
                        "sistemas":             json.dumps(sistemas),
                        "sistemas_count":       len(sistemas)
                    }
                })

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Layer '{layer}' no reconocida. Opciones: fc_puntos, fc_hubs"
            )

        return _build_feature_collection(
            indicador  = "capillary",
            layer      = layer,
            feature    = features,
            parametros = {
                "min_fc": min_fc, "top_n": top_n,
                "snap_tolerance_m": snap_tolerance_m,
                "hub_tolerance_m":  hub_tolerance_m
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        vft_logger.error(f"Error en GeoLayer capillary [{layer}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en GeoLayer capillary: {str(e)}")

# ----------------------------------------------------------------------
## Sección F — Endpoint /detour
# ----------------------------------------------------------------------

@router.get("/detour", summary="Factor de Desviación como FeatureCollection GeoJSON")
async def get_geolayer_detour(
    layer:       str                 = Query("df_puntos",
                                             description="df_puntos | df_por_alcaldia"),
    sample_size: int                 = Query(100,  description="Tamaño de muestra de rutas O-D"),
    seed:        Optional[int]       = Query(42,   description="Semilla para reproducibilidad"),
    mode:        str                 = Query("REALISTIC_INTEGRATION"),
    tolerance_m: float               = Query(DEFAULT_TOLERANCE),
    entidades:   Optional[List[str]] = Query(None, description="Entidades para df_por_alcaldia (default: Ciudad de México, Estado de México)")
):
    if entidades is None:
        entidades = ["Ciudad de México", "Estado de México"]
    try:
        G            = await get_or_build_graph(mode, tolerance_m)
        orchestrator = DetourFactorOrchestrator(G)

        # ── df_puntos ──────────────────────────────────────────────────────
        if layer == "df_puntos":
            resultados = await asyncio.to_thread(
                orchestrator.calculate_sample_routes, sample_size, seed, True
            )

            features = []
            for res in resultados:
                m    = res["metrics"]
                ruta = res["map_data"]["network_route"]
                if not ruta:
                    continue
                lon, lat = ruta[0]["lon"], ruta[0]["lat"]
                sistemas = m.get("Sistemas_Involucrados", [])
                fd       = m["Factor_Desviacion"]
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "id":               f"{m['Origen']}_{m['Destino']}",
                        "nombre":           f"{m['Origen']} → {m['Destino']}",
                        "indicador":        "detour",
                        "layer":            layer,
                        "factor_desviacion": fd,
                        "origen":           m["Origen"],
                        "destino":          m["Destino"],
                        "dist_red_km":      m["Distancia_Red_km"],
                        "dist_recta_km":    m["Distancia_Recta_km"],
                        "sistemas":         json.dumps(sistemas),
                        "categoria_df":     _clasify_diff(fd)
                    }
                })

        # ── df_por_alcaldia ────────────────────────────────────────────────
        elif layer == "df_por_alcaldia":
            # G ya está cacheado — correr cálculo y fetch de polígonos en paralelo
            resultados, geojson_pol = await asyncio.gather(
                asyncio.to_thread(orchestrator.calculate_sample_routes, sample_size, seed, True),
                fetch_territorial_polygons(entidades=entidades)
            )

            # GeoDataFrame de puntos (coordenada de inicio de cada ruta)
            puntos_data = []
            for res in resultados:
                m    = res["metrics"]
                ruta = res["map_data"]["network_route"]
                if not ruta:
                    continue
                puntos_data.append({
                    "factor_desviacion": m["Factor_Desviacion"],
                    "geometry": Point(ruta[0]["lon"], ruta[0]["lat"])
                })
            gdf_puntos = gpd.GeoDataFrame(puntos_data, crs="EPSG:4326")

            # GeoDataFrame de polígonos territoriales
            features_pol = geojson_pol.get("features", [])
            if not features_pol and "data" in geojson_pol:
                features_pol = geojson_pol["data"].get("features", [])
            gdf_pol = gpd.GeoDataFrame.from_features(features_pol, crs="EPSG:4326")
            if "nombre" in gdf_pol.columns:
                gdf_pol = gdf_pol.dissolve(by="nombre").reset_index()

            # Spatial join punto → alcaldía + agregación
            joined  = gpd.sjoin(gdf_puntos, gdf_pol[["nombre", "geometry"]], how="left", predicate="within")
            grouped = (
                joined
                .groupby("nombre")["factor_desviacion"]
                .agg(df_promedio="mean", df_stddev="std", n_rutas="count")
                .reset_index()
            )

            features = []
            for _, row in grouped.iterrows():
                nombre  = row["nombre"]
                pol_row = gdf_pol[gdf_pol["nombre"] == nombre]
                if pol_row.empty:
                    continue
                geom    = pol_row.iloc[0].geometry
                df_prom = round(row["df_promedio"], 3)
                features.append({
                    "type": "Feature",
                    "geometry": mapping(geom),
                    "properties": {
                        "id":           nombre,
                        "nombre":       nombre,
                        "indicador":    "detour",
                        "layer":        layer,
                        "df_promedio":  df_prom,
                        "df_stddev":    round(row["df_stddev"], 3) if pd.notna(row["df_stddev"]) else None,
                        "n_rutas":      int(row["n_rutas"]),
                        "categoria_df": _clasify_diff(df_prom)
                    }
                })

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Layer '{layer}' no reconocida. Opciones: df_puntos, df_por_alcaldia"
            )

        return _build_feature_collection(
            indicador  = "detour",
            layer      = layer,
            feature    = features,
            parametros = {"sample_size": sample_size, "seed": seed, "entidades": entidades}
        )

    except HTTPException:
        raise
    except Exception as e:
        vft_logger.error(f"Error en GeoLayer detour [{layer}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en GeoLayer detour: {str(e)}")
