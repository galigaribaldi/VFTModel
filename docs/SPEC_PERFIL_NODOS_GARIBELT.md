# Spec técnica — perfil_nodos Garibelt × 3 escenarios

**Versión:** 1.1 — corregida 2026-09-25  
**Estado:** Aprobada para implementación  
**Rama:** `feat/propuesta-anillar-indicador`

## Correcciones aplicadas respecto al prompt original de Transport-GIS

| Bug | Descripción | Corrección |
|-----|-------------|------------|
| B1 | `dim_accesibilidad` dividía por `100.0` y por `COVERAGE_BEST` — producía `0.000688` en vez de `0.069` | Usar `normalize_scalar(pct, 0.0, COVERAGE_BEST)` directamente |
| B2 | Guard `nota_metodologica` usaba `is None` — `float('nan') is not None` es `True`, nunca activaba el aviso para los 554 nodos aislados | Usar `b is None or pd.isna(b)` |
| B3 | `GARIBELT_COLORS` no existía en ningún archivo | Añadido a `src/core/algorithms/composite/normalization.py` como fuente única ✅ |
| B4 | Return select de `_build_node_enrichment()` no incluía las columnas nuevas — las truncaba silenciosamente | Actualizar el select explícito al final del método |

---

## Objetivo

Extender `GET /api/v1/network/geolayers/profile?layer=perfil_nodos` para que devuelva
campos enriquecidos por nodo sin romper ningún contrato de datos existente.
Los 3 GeoJSONs resultantes (baseline / mb / metro) habilitan análisis comparativo
de transición de bandas entre escenarios en Transport-GIS.

## Repositorios involucrados

- **VFTModel** — modificar exactamente los 3 archivos indicados
- **Transport-GIS** — NO modificar; solo consume el nuevo output

---

## Restricciones de integridad (no negociables)

- Los algoritmos de T, B(v), DI, C, Cᵢ **NO** se tocan
- `_dim_accesibilidad()` a nivel red **NO** se modifica
- `banda_dominante` **NO** incluye `dim_accesibilidad` — la cobertura CDMX (~5.5%) normalizaría a ~0.069 y colapsaría todos los nodos a "crítico"
- `NetworkProfiler` backward compatible: `G=None` preserva comportamiento actual del notebook 06
- El schema de `/topological/network-profile` **NO** cambia
- Notebooks existentes **NO** requieren re-ejecución

---

## PARTE 1 — Archivos a modificar

### 1.1 `src/core/algorithms/composite/normalization.py`

**Estado:** ✅ Ya aplicado — `GARIBELT_COLORS` añadido.

```python
GARIBELT_COLORS: dict[str, str] = {
    "critico":       "#E74C3C",
    "debil":         "#F39C12",
    "aceptable":     "#F1C40F",
    "idoneo":        "#27AE60",
    "no_disponible": "#95A5A6",
}
```

---

### 1.2 `src/core/algorithms/composite/network_profile.py`

#### 1.2.1 — Import `nx` y `Optional`

Añadir al bloque de imports:
```python
import networkx as nx
from typing import Optional
```

#### 1.2.2 — `NetworkProfiler.__init__()` — parámetro `G` opcional

```python
def __init__(
    self,
    coverage_df: Optional[pd.DataFrame],
    capillar_df: pd.DataFrame,
    detour_df: pd.DataFrame,
    travel_time_min: float,
    betweenness_df: Optional[pd.DataFrame] = None,  # opcional — guard en _dim_centralidad
    G: Optional[nx.DiGraph] = None,                 # nuevo
):
    self.G = G
    # resto sin cambios
```

#### 1.2.3 — Guard en `_dim_centralidad()` para `betweenness_df=None`

```python
def _dim_centralidad(self) -> DimensionProfile:
    if self.betweenness_df is None or self.betweenness_df.empty:
        return DimensionProfile("centralidad_critica", "B(v) — Centralidad de Intermediación",
                                0.0, 0.0, "critico", "Sin datos")
    values = self.betweenness_df["betweenness_centrality"].dropna().tolist()
    # resto sin cambios
```

#### 1.2.4 — `_build_node_enrichment()` — columnas nuevas + return select corregido

Al final del método, **antes del return**, añadir:

```python
if self.G is not None:
    # sistema: atributo de nodo del grafo
    merged["sistema"] = merged["node_id"].apply(
        lambda nid: self.G.nodes.get(nid, {}).get("sistema")
    )

    # tipo_nodo: clasificación por percentil de fc_normalizado
    p75 = merged["fc_normalizado"].quantile(0.75)
    p50 = merged["fc_normalizado"].quantile(0.50)

    def _tipo(fc):
        if fc >= p75:   return "hub_principal"
        if fc >= p50:   return "nodo_integrador"
        return "nodo_terminal"

    merged["tipo_nodo"] = merged["fc_normalizado"].apply(_tipo)

    # dim_accesibilidad: cobertura de la alcaldía del nodo
    # FUERA de banda_dominante — informativo únicamente
    if self.coverage_df is not None and not self.coverage_df.empty:
        cov_map = dict(zip(
            self.coverage_df["Demarcacion"],
            self.coverage_df["Cobertura_Porcentaje"]
        ))
        merged["alcaldia"] = merged["node_id"].apply(
            lambda nid: self.G.nodes.get(nid, {}).get("alcaldia_municipio")
        )
        merged["dim_accesibilidad"] = merged["alcaldia"].apply(
            lambda alc: round(normalize_scalar(cov_map.get(alc, 0.0), 0.0, COVERAGE_BEST), 4)
            if alc else None
        )
        merged.drop(columns=["alcaldia"], inplace=True)
    else:
        merged["dim_accesibilidad"] = None
else:
    merged["sistema"]           = None
    merged["tipo_nodo"]         = None
    merged["dim_accesibilidad"] = None
```

**Return select corregido** (Bug 4 — incluir columnas nuevas):

```python
return merged[
    [
        "Nodo_ID", "Estacion", "lon", "lat",
        "Fuerza_Capilar_Total", "fc_normalizado", "fc_banda",
        "betweenness_centrality", "b_normalizado", "b_banda",
        "banda_dominante",
        "sistema", "tipo_nodo", "dim_accesibilidad",   # nuevas
    ]
].rename(columns={"Nodo_ID": "node_id", "Estacion": "nombre"})
```

---

### 1.3 `src/api/main.py`

En `get_network_profile()`, pasar `G` al profiler (`G` ya está en scope como `GRAPH_CACHE.get(...)`):

```python
profiler = NetworkProfiler(
    coverage_df=coverage_df,
    capillar_df=capillar_df,
    detour_df=detour_df,
    travel_time_min=travel_time_min,
    betweenness_df=betweenness_df,
    G=G,               # nuevo
)
```

---

### 1.4 `src/api/routes/geo_layers.py`

#### Import adicional

Añadir a los imports de `normalization`:
```python
from src.core.algorithms.composite.normalization import (
    classify_band, GARIBELT_COLORS
)
```

#### Serialización del handler `perfil_nodos`

```python
# Guards existentes (no cambiar)
b_norm      = row.get("b_normalizado")
b_banda_raw = row.get("b_banda")
b_banda     = b_banda_raw if isinstance(b_banda_raw, str) else "no_disponible"
fc_banda_raw = row.get("fc_banda")
fc_banda     = fc_banda_raw if isinstance(fc_banda_raw, str) else "no_disponible"
bc           = row.get("betweenness_centrality")

# Guard nota_metodologica — usa pd.isna (Bug 2 corregido)
_b = row.get("b_normalizado")
nota = (
    "sin_betweenness — nodo fuera del SCC gigante"
    if (_b is None or pd.isna(_b)) else ""
)

# dims_disponibles — solo cuenta dimensiones usadas en banda_dominante
_dims = sum(1 for v in [row.get("fc_normalizado"), _b]
            if v is not None and not pd.isna(v))

banda_dom = row.get("banda_dominante", "no_disponible")

properties = {
    # ── existentes (NO cambiar) ─────────────────────────────────────────
    "id":                     row["node_id"],
    "nombre":                 row["nombre"],
    "fc_total":               int(row["Fuerza_Capilar_Total"]),
    "fc_normalizado":         round(float(row["fc_normalizado"]), 4),
    "fc_banda":               fc_banda,
    "betweenness_centrality": round(float(bc), 6) if bc is not None and not pd.isna(bc) else None,
    "b_normalizado":          round(float(b_norm), 4) if b_norm is not None and not pd.isna(b_norm) else None,
    "b_banda":                b_banda,
    "banda_dominante":        banda_dom,

    # ── nuevos ──────────────────────────────────────────────────────────
    "sistema":                row.get("sistema"),
    "tipo_nodo":              row.get("tipo_nodo"),

    # aliases semánticos para Transport-GIS
    "dim_capilar":            round(float(row["fc_normalizado"]), 4),
    "dim_centralidad":        round(float(b_norm), 4) if b_norm is not None and not pd.isna(b_norm) else None,
    "dim_accesibilidad":      row.get("dim_accesibilidad"),

    # dimensiones no computables por nodo — documentadas explícitamente
    "dim_eficiencia":         None,   # DI es escalar de red (500 pares O-D)
    "dim_fluidez":            None,   # T es promedio global all-pairs

    # soporte para Transport-GIS
    "banda_color":            GARIBELT_COLORS.get(banda_dom, "#95A5A6"),
    "dims_disponibles":       _dims,
    "nota_metodologica":      nota,
}
```

---

## PARTE 2 — Verificación (Notebook 07)

Crear `notebooks/07_perfil_nodos_verification.ipynb`:

### Sección A — Distribución de banda_dominante
- Total nodos por banda
- % con `dims_disponibles = 1` vs `= 2`
- Confirmar `nota_metodologica != ""` ≈ 554 nodos

### Sección B — Integridad de campos nuevos
- % nodos con `sistema` no-null (esperado: ~100%)
- Distribución `tipo_nodo` (hub_principal / nodo_integrador / nodo_terminal)
- Histograma `dim_accesibilidad` — esperado: mayoría ≈ 0.069 (C≈5.5% CDMX)
- Confirmar `dim_accesibilidad` no modifica `banda_dominante`
- Confirmar `dim_eficiencia = null` y `dim_fluidez = null` en todos los nodos

### Sección C — Cross-tab
- Tabla `banda_dominante × fc_banda × b_banda`
- Top-20 nodos por `b_normalizado` con su `banda_dominante`

Consumo del endpoint:
```python
import requests
r = requests.get("http://localhost:8000/api/v1/network/geolayers/profile")
features = r.json()["features"]
```

---

## Contrato de salida — lo que consumirá Transport-GIS

```
GET http://localhost:{port}/api/v1/network/geolayers/profile?layer=perfil_nodos

Response: GeoJSON FeatureCollection — un Point por nodo.
Total features: 11,115 (baseline) / ~11,209 (MB, METRO con +94 nodos del anillo)
```

> **Nota:** el prompt original de Transport-GIS indicaba ~10,537 features.
> El valor correcto es **11,115** — todos los nodos del grafo tienen coordenadas
> válidas (los transbordos peatonales son aristas, no nodos).
> Transport-GIS debe actualizar su validación esperada.

Archivos de salida en Transport-GIS:
```
data/processed/garibelt/perfil_nodos_baseline.geojson
data/processed/garibelt/perfil_nodos_mb.geojson
data/processed/garibelt/perfil_nodos_metro.geojson
```

---

## Checklist de verificación

- [ ] `GET /geolayers/profile` devuelve los nuevos campos
- [ ] `banda_dominante` no cambia respecto al valor previo al warmup
- [ ] ~554 nodos tienen `dim_centralidad = null` y `nota_metodologica != ""`
- [ ] `dim_eficiencia` y `dim_fluidez` son `null` en todos los nodos
- [ ] `dim_accesibilidad` no afecta `banda_dominante`
- [ ] `GET /topological/network-profile` sigue funcionando igual
- [ ] Notebook 07 ejecuta sin errores con servidor en `:8000`
- [ ] Features baseline = 11,115 (no 10,537)
