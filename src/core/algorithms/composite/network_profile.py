"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Compilador de la Clasificación Garibelt — Tablero de Diagnóstico Topológico VFT.
              Compila los 5 indicadores disponibles en un perfil multi-dimensional sin agregar
              a un escalar único. Cada dimensión se clasifica en la Escala Garibelt:
              crítico / débil / aceptable / idóneo.
@phase: composite
@route: src/core/algorithms/composite/network_profile.py
"""

import ast
from dataclasses import dataclass
from typing import Optional

import networkx as nx
import pandas as pd

from src.core.algorithms.composite.normalization import (
    classify_band,
    gini_coefficient,
    normalize_scalar,
)

# Constantes de referencia para dimensiones con umbrales externos
# T_REFERENCIA_MIN proviene de AverageTravelTimeOrchestrator → reference.expected_cdmx_approx
T_REFERENCIA_MIN: float = 85.0
# Umbral de peor caso asumido para la red (definido empíricamente como techo razonable)
T_WORST_CASE_MIN: float = 180.0
# DI=1.0 es ruta perfectamente directa; DI>=2.5 se considera críticamente ineficiente
DI_BEST: float = 1.0
DI_WORST: float = 2.5
# Cobertura peatonal 800 m: 0% → crítico, 80% → idóneo (literatura de accesibilidad urbana)
COVERAGE_BEST: float = 80.0


@dataclass
class DimensionProfile:
    dimension: str
    indicador_fuente: str
    valor_bruto: float
    valor_normalizado: float
    banda: str
    metrica_descripcion: str


@dataclass
class ProfileResult:
    dimensions: list[DimensionProfile]
    node_enrichment: pd.DataFrame


class NetworkProfiler:
    """
    Compilador de la Clasificación Garibelt: recibe salidas ya computadas de los algoritmos VFT
    y produce el tablero de diagnóstico topológico de la red. No recalcula ningún indicador.

    Parámetros
    ----------
    coverage_df : pd.DataFrame
        Salida de SpatialCoverageAnalyzer.calculate_general_coverage().
        Columnas requeridas: Demarcacion, Area_Total_km2, Cobertura_Porcentaje.
    capillar_df : pd.DataFrame
        Salida de CapillaryStrengthAnalyzer.calculate_capillary_strength().
        Columnas requeridas: Nodo_ID, Estacion, Fuerza_Capilar_Total.
    detour_df : pd.DataFrame
        Salida de DetourFactorOrchestrator.calculate_sample_routes().
        Columnas requeridas: Factor_Desviacion.
    travel_time_min : float
        T_average_travel_time_minutes de AverageTravelTimeOrchestrator.analyze().
    betweenness_df : pd.DataFrame
        ranking DataFrame de BetweennessOrchestrator.analyze()["ranking"].
        Columnas requeridas: node_id, betweenness_centrality, lon, lat.
    """

    def __init__(
        self,
        coverage_df: Optional[pd.DataFrame],
        capillar_df: pd.DataFrame,
        detour_df: pd.DataFrame,
        travel_time_min: float,
        betweenness_df: Optional[pd.DataFrame] = None,
        G: Optional[nx.DiGraph] = None,
    ):
        self.coverage_df = coverage_df
        self.capillar_df = capillar_df
        self.detour_df = detour_df
        self.travel_time_min = travel_time_min
        self.betweenness_df = betweenness_df
        self.G = G

    def build_profile(self) -> ProfileResult:
        dimensions = [
            self._dim_accesibilidad(),
            self._dim_capilar(),
            self._dim_eficiencia(),
            self._dim_fluidez(),
            self._dim_centralidad(),
        ]
        node_enrichment = self._build_node_enrichment()
        return ProfileResult(dimensions=dimensions, node_enrichment=node_enrichment)

    # ── dimensiones ────────────────────────────────────────────────────────────

    def _dim_accesibilidad(self) -> DimensionProfile:
        if self.coverage_df is None or self.coverage_df.empty:
            return DimensionProfile(
                dimension="accesibilidad",
                indicador_fuente="C — Cobertura Espacial",
                valor_bruto=0.0,
                valor_normalizado=0.0,
                banda="no_disponible",
                metrica_descripcion="Go backend no disponible al momento del cálculo",
            )
        df = self.coverage_df
        total_area = df["Area_Total_km2"].sum()
        if total_area > 0:
            # Media ponderada de cobertura % por área de cada demarcación
            valor_bruto = float((df["Cobertura_Porcentaje"] * df["Area_Total_km2"]).sum() / total_area)
        else:
            valor_bruto = float(df["Cobertura_Porcentaje"].mean())

        # Normalización contra umbral de literatura (0% → 0, 80% → 1)
        valor_norm = normalize_scalar(valor_bruto, 0.0, COVERAGE_BEST)

        return DimensionProfile(
            dimension="accesibilidad",
            indicador_fuente="C — Cobertura Espacial",
            valor_bruto=round(valor_bruto, 4),
            valor_normalizado=round(valor_norm, 4),
            banda=classify_band(valor_norm),
            metrica_descripcion=f"Cobertura peatonal 800 m ponderada por área: {valor_bruto:.1f}%",
        )

    def _dim_capilar(self) -> DimensionProfile:
        fc = self.capillar_df["Fuerza_Capilar_Total"].dropna()
        if fc.empty:
            return DimensionProfile("conectividad_capilar", "Cᵢ — Alimentación Capilar",
                                    0.0, 0.0, "critico", "Sin datos")
        mediana = float(fc.median())

        # Normalización percentilar empírica: mediana contra [Q1, Q3] del propio dataset
        q1 = float(fc.quantile(0.25))
        q3 = float(fc.quantile(0.75))
        valor_norm = normalize_scalar(mediana, q1, q3)

        return DimensionProfile(
            dimension="conectividad_capilar",
            indicador_fuente="Cᵢ — Alimentación Capilar",
            valor_bruto=round(mediana, 4),
            valor_normalizado=round(valor_norm, 4),
            banda=classify_band(valor_norm),
            metrica_descripcion=f"Mediana grado nodal: {mediana:.1f} (escala Q1={q1:.0f}–Q3={q3:.0f})",
        )

    def _dim_eficiencia(self) -> DimensionProfile:
        values = self.detour_df["Factor_Desviacion"].dropna()
        if values.empty:
            return DimensionProfile("eficiencia_ruta", "DI — Índice de Ruta Directa",
                                    0.0, 0.0, "critico", "Sin datos")
        mediana = float(values.median())

        # DI inverso: menor DI = mejor. score = (WORST - DI) / (WORST - BEST)
        valor_norm = normalize_scalar(DI_WORST - mediana, 0.0, DI_WORST - DI_BEST)

        return DimensionProfile(
            dimension="eficiencia_ruta",
            indicador_fuente="DI — Índice de Ruta Directa",
            valor_bruto=round(mediana, 4),
            valor_normalizado=round(valor_norm, 4),
            banda=classify_band(valor_norm),
            metrica_descripcion=f"Mediana Factor Desviación: {mediana:.2f} (1.0 = ruta directa perfecta)",
        )

    def _dim_fluidez(self) -> DimensionProfile:
        valor_bruto = self.travel_time_min

        # T inverso: menor T = mejor. score = (WORST - T) / (WORST - REF)
        valor_norm = normalize_scalar(
            T_WORST_CASE_MIN - valor_bruto,
            0.0,
            T_WORST_CASE_MIN - T_REFERENCIA_MIN,
        )

        return DimensionProfile(
            dimension="fluidez_global",
            indicador_fuente="T — Tiempo de Viaje Promedio",
            valor_bruto=round(valor_bruto, 4),
            valor_normalizado=round(valor_norm, 4),
            banda=classify_band(valor_norm),
            metrica_descripcion=f"T promedio shortest-path: {valor_bruto:.1f} min (ref. CDMX: {T_REFERENCIA_MIN} min)",
        )

    def _dim_centralidad(self) -> DimensionProfile:
        if self.betweenness_df is None or self.betweenness_df.empty:
            return DimensionProfile("centralidad_critica", "B(v) — Centralidad de Intermediación",
                                    0.0, 0.0, "critico", "Sin datos")
        values = self.betweenness_df["betweenness_centrality"].dropna().tolist()
        if not values:
            return DimensionProfile("centralidad_critica", "B(v) — Centralidad de Intermediación",
                                    0.0, 0.0, "critico", "Sin datos")
        gini = gini_coefficient(values)

        # Gini alto = criticidad concentrada en pocos nodos = mayor vulnerabilidad
        # score = 1 - Gini  (red equidistribuida es idónea estructuralmente)
        valor_norm = max(0.0, min(1.0, 1.0 - gini))

        return DimensionProfile(
            dimension="centralidad_critica",
            indicador_fuente="B(v) — Centralidad de Intermediación",
            valor_bruto=round(gini, 6),
            valor_normalizado=round(valor_norm, 4),
            banda=classify_band(valor_norm),
            metrica_descripcion=f"Gini de intermediación: {gini:.4f} (0 = distribuida, 1 = concentrada)",
        )

    # ── enriquecimiento por nodo ───────────────────────────────────────────────

    def _build_node_enrichment(self) -> pd.DataFrame:
        """
        Produce un DataFrame por nodo con scores normalizados de Cᵢ y B(v).
        Coordenadas extraídas de Nodo_ID (capilar) y columnas lon/lat (betweenness).
        Join por node_id string — ambos algoritmos usan str(node) del mismo grafo.
        """
        # ── capilar: normalización por nodo ────────────────────────────────────
        cap = self.capillar_df[["Nodo_ID", "Estacion", "Fuerza_Capilar_Total"]].copy()
        fc_min = float(cap["Fuerza_Capilar_Total"].min())
        fc_max = float(cap["Fuerza_Capilar_Total"].max())
        cap["fc_normalizado"] = cap["Fuerza_Capilar_Total"].apply(
            lambda v: normalize_scalar(float(v), fc_min, fc_max)
        )
        cap["fc_banda"] = cap["fc_normalizado"].apply(classify_band)
        cap["lon"] = cap["Nodo_ID"].apply(lambda s: ast.literal_eval(s)[0])
        cap["lat"] = cap["Nodo_ID"].apply(lambda s: ast.literal_eval(s)[1])

        # ── betweenness: normalización por nodo ────────────────────────────────
        bc = self.betweenness_df[["node_id", "betweenness_centrality"]].copy()
        bc_min = float(bc["betweenness_centrality"].min())
        bc_max = float(bc["betweenness_centrality"].max())
        bc["b_normalizado"] = bc["betweenness_centrality"].apply(
            lambda v: normalize_scalar(float(v), bc_min, bc_max)
        )
        bc["b_banda"] = bc["b_normalizado"].apply(classify_band)

        # ── join por node_id (str(node) en ambos) ─────────────────────────────
        merged = cap.merge(
            bc[["node_id", "betweenness_centrality", "b_normalizado", "b_banda"]],
            left_on="Nodo_ID",
            right_on="node_id",
            how="left",
        )

        # Banda dominante: dimensión más débil por nodo
        def _dominant_band(row):
            fc_n = row["fc_normalizado"]
            b_n = row.get("b_normalizado", None)
            if b_n is None or (isinstance(b_n, float) and pd.isna(b_n)):
                return classify_band(fc_n)
            return classify_band(min(fc_n, float(b_n)))

        merged["banda_dominante"] = merged.apply(_dominant_band, axis=1)

        if self.G is not None:
            merged["sistema"] = merged["Nodo_ID"].apply(
                lambda nid: self.G.nodes.get(ast.literal_eval(nid), {}).get("sistema")
            )

            p75 = merged["fc_normalizado"].quantile(0.75)
            p50 = merged["fc_normalizado"].quantile(0.50)

            def _tipo(fc):
                if fc >= p75: return "hub_principal"
                if fc >= p50: return "nodo_integrador"
                return "nodo_terminal"

            merged["tipo_nodo"] = merged["fc_normalizado"].apply(_tipo)

            if self.coverage_df is not None and not self.coverage_df.empty:
                cov_map = dict(zip(
                    self.coverage_df["Demarcacion"],
                    self.coverage_df["Cobertura_Porcentaje"]
                ))
                merged["_alcaldia"] = merged["Nodo_ID"].apply(
                    lambda nid: self.G.nodes.get(ast.literal_eval(nid), {}).get("alcaldia_municipio")
                )
                merged["dim_accesibilidad"] = merged["_alcaldia"].apply(
                    lambda alc: round(normalize_scalar(cov_map.get(alc, 0.0), 0.0, COVERAGE_BEST), 4)
                    if alc else None
                )
                merged.drop(columns=["_alcaldia"], inplace=True)
            else:
                merged["dim_accesibilidad"] = None
        else:
            merged["sistema"]           = None
            merged["tipo_nodo"]         = None
            merged["dim_accesibilidad"] = None

        return merged[
            [
                "Nodo_ID", "Estacion", "lon", "lat",
                "Fuerza_Capilar_Total", "fc_normalizado", "fc_banda",
                "betweenness_centrality", "b_normalizado", "b_banda",
                "banda_dominante",
                "sistema", "tipo_nodo", "dim_accesibilidad",
            ]
        ].rename(columns={"Nodo_ID": "node_id", "Estacion": "nombre"})
