# Especificación del cliente VFTModel → Transport-gis-zmvm-mjg

Documento de referencia para la integración entre los repositorios
**VFTModel** (fuente de indicadores) y **Transport-gis-zmvm-mjg** (visualización cartográfica).

---

## 1. Modelo de ejecución del cliente

El cliente es un **script CLI de Python** que corre en un entorno virtual propio
del repo `Transport-gis-zmvm-mjg`. No levanta ningún servidor; es un consumidor
puntual que se ejecuta manualmente cuando el analista necesita actualizar los datos.

```
# Activar entorno virtual
source .venv/bin/activate

# Regenerar todas las capas
python analysis/scripts/vft_fetcher.py --mode live

# Regenerar solo una capa
python analysis/scripts/vft_fetcher.py --mode live --layer df_por_alcaldia

# Usar caché existente (no llama a VFTModel, QGIS ya tiene el .gpkg)
python analysis/scripts/vft_fetcher.py --mode cached
```

**Dependencias del cliente (`.venv`):**

| Paquete | Uso |
|---------|-----|
| `requests` | HTTP GET a la API de VFTModel |
| `geopandas` | Conversión GeoJSON → GeoDataFrame → `.gpkg` |
| `shapely` | Implícita en geopandas |

El resultado de cada ejecución en modo `live` es un único archivo:
`data/processed/VFTOutput.gpkg` con todas las capas temáticas.
QGIS consume este archivo del disco; nunca llama a la API directamente.

---

## 2. Endpoints requeridos de VFTModel

El cliente espera que VFTModel exponga los siguientes endpoints bajo el router
`/api/v1/network/geolayers`:

| Método | Ruta | Parámetros query | Capas que produce |
|--------|------|-----------------|-------------------|
| GET | `/api/v1/network/geolayers/coverage` | `radio_m=800`, `entidades=["Ciudad de México"]` | `cobertura_por_alcaldia`, `estaciones`, `cobertura_800m` |
| GET | `/api/v1/network/geolayers/capillary` | `min_fc=3`, `top_n=20`, `snap_tolerance_m=50` | `fc_puntos`, `fc_hubs` |
| GET | `/api/v1/network/geolayers/detour` | `sample_size=100`, `seed=42`, `entidades=["Ciudad de México"]` | `df_puntos`, `df_por_alcaldia` |

El parámetro `layer` en cada request indica qué capa devolver.
Si se omite, el endpoint devuelve la primera capa por defecto.

---

## 3. Contrato de datos

### 3.1 Envoltura estándar (todas las respuestas)

```json
{
  "type": "FeatureCollection",
  "metadata": {
    "indicador":   "cobertura | capillary | detour",
    "layer":       "nombre_del_layer",
    "n_features":  141,
    "crs":         "EPSG:4326",
    "fetched_at":  "2026-06-02T14:30:00Z",
    "parametros": {
      "radio_m":   800,
      "entidades": ["Ciudad de México"]
    }
  },
  "features": [ ... ]
}
```

Toda respuesta es un GeoJSON `FeatureCollection` válido.
El cliente usa `geopandas.GeoDataFrame.from_features(response["features"])` directamente.

### 3.2 Campos estándar en `properties` (toda feature, toda capa)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | string | Identificador único dentro del layer |
| `nombre` | string | Nombre legible (estación, alcaldía, hub, ruta) |
| `indicador` | string | Replica `metadata.indicador` — permite filtrar en QGIS sin joins |
| `layer` | string | Replica `metadata.layer` — mismo motivo |

### 3.3 CRS

**VFTModel entrega todas las capas en `EPSG:4326`.**
El cliente no reprojecta. Si una capa se calcula internamente en `EPSG:32614`
(sjoin métrico, buffers), VFTModel aplica `.to_crs("EPSG:4326")` antes de
serializar a GeoJSON.

---

## 4. Campos por capa

### 4.1 `cobertura_por_alcaldia` — Polígono

```
── campos base ──────────────────────────────────────
nombre              string   Nombre de la alcaldía
area_total_km2      float    Área total de la alcaldía
area_cubierta_km2   float    Área cubierta por buffers de estaciones
cobertura_pct       float    (area_cubierta / area_total) × 100

── subcampos calculados por VFTModel ────────────────
cobertura_deficit   float    = 100 - cobertura_pct
                             Facilita mapas de déficit sin operar en QGIS
categoria_cobertura string   = "alta"  si cobertura_pct > 60
                             = "media" si cobertura_pct 30–60
                             = "baja"  si cobertura_pct < 30
                             Permite simbología categórica directa en QGIS
```

### 4.2 `estaciones` — Point

```
── campos base ──────────────────────────────────────
nombre              string   Nombre de la estación
sistema             string   Metro | Metrobús | RTP | Tren Ligero | ...
tipo_entidad        string   estacion | paradero | terminal

── subcampos calculados por VFTModel ────────────────
sistemas_count      int      Número de sistemas distintos que conecta
                             Proxy de intermodalidad; útil para clasificar nodos
```

### 4.3 `cobertura_800m` — MultiPolygon

```
── sin campos temáticos (solo geometría de la mancha unificada) ──

── subcampo de trazabilidad ─────────────────────────
radio_m             int      Radio usado para el buffer (ej. 800)
                             Permite comparar escenarios 800 m vs 1000 m
```

### 4.4 `fc_puntos` — Point

```
── campos base ──────────────────────────────────────
nombre              string   Nombre de la estación / nodo
fc_total            float    Fuerza Capilar Total del nodo
cx_entrada          int      Conexiones de entrada
cx_salida           int      Conexiones de salida

── subcampos calculados por VFTModel ────────────────
sistemas            string   JSON-encoded list, ej. '["Metro","Metrobús"]'
                             GPKG no soporta arrays nativos; JSON string es el estándar
sistemas_count      int      = len(sistemas)
tipo_nodo           string   Clasificación por umbral de fc_total:
                             "hub_principal"   fc_total > 20
                             "hub_secundario"  fc_total 10–20
                             "nodo_relevante"  fc_total 6–10
                             "nodo_basico"     fc_total 3–6
                             Mismos umbrales usados en la simbología del Coloquio 2026-2
```

### 4.5 `fc_hubs` — Point

```
── campos base ──────────────────────────────────────
nombre              string   Nombre del macro-hub (hub_nombre en origen)
estaciones_agrupadas int     Número de estaciones agrupadas en el hub
fc_total            float    Fuerza Capilar Total del hub

── subcampos calculados por VFTModel ────────────────
sistemas            string   JSON-encoded list
sistemas_count      int      = len(sistemas)
```

### 4.6 `df_puntos` — Point

Geometría: coordenada de inicio de la ruta (`network_route[0]`).

```
── campos base ──────────────────────────────────────
nombre              string   "Origen → Destino" (etiqueta compuesta)
factor_desviacion   float    DF de la ruta
origen              string   Nombre del nodo origen
destino             string   Nombre del nodo destino
dist_red_km         float    Distancia recorrida por la red
dist_recta_km       float    Distancia en línea recta

── subcampos calculados por VFTModel ────────────────
sistemas            string   JSON-encoded list de sistemas involucrados
categoria_df        string   Clasificación por umbral de factor_desviacion:
                             "eficiente" DF ≤ 1.3
                             "moderado"  DF 1.3–1.6
                             "alto"      DF 1.6–2.0
                             "critico"   DF > 2.0
                             Mismos umbrales del choroplético del Coloquio 2026-2
```

### 4.7 `df_por_alcaldia` — Polygon

```
── campos base ──────────────────────────────────────
nombre              string   Nombre de la alcaldía
df_promedio         float    Media del Factor de Desviación en la alcaldía
n_rutas             int      Número de rutas de muestra que pasan por la alcaldía

── subcampos calculados por VFTModel ────────────────
df_stddev           float    Desviación estándar del DF en la alcaldía
                             Muestra variabilidad interna, no solo el promedio
categoria_df        string   Misma clasificación que df_puntos (basada en df_promedio)
```

---

## 5. Capa de trazabilidad `_meta`

Una capa sin geometría, una sola fila. El cliente la escribe al final de cada
ejecución exitosa en modo `live`. Permite saber si `VFTOutput.gpkg` está actualizado.

| Campo | Tipo | Ejemplo |
|-------|------|---------|
| `fetched_at` | string | `"2026-06-02T14:30:00Z"` |
| `vftmodel_url` | string | `"http://localhost:8000"` |
| `radio_m` | int | `800` |
| `entidades` | string | `'["Ciudad de México"]'` |
| `git_sha` | string | Hash del commit HEAD de VFTModel al momento del fetch |

---

## 6. Estructura simulada del cliente

```
analysis/scripts/vft_fetcher.py
│
├── CONFIG
│   BASE_URL    = "http://localhost:8000/api/v1/network/geolayers"
│   OUTPUT_PATH = "data/processed/VFTOutput.gpkg"
│
├── LAYER_REGISTRY: list[LayerDef]
│   Cada LayerDef tiene: endpoint, layer_name, params_default
│   ┌──────────────────────┬────────────────┬──────────────────────────────┐
│   │ endpoint             │ layer_name     │ params_default               │
│   ├──────────────────────┼────────────────┼──────────────────────────────┤
│   │ /coverage            │ cobertura_por_ │ radio_m=800                  │
│   │                      │ alcaldia       │ entidades=["Ciudad de México"]│
│   ├──────────────────────┼────────────────┼──────────────────────────────┤
│   │ /coverage            │ estaciones     │ (mismos)                     │
│   ├──────────────────────┼────────────────┼──────────────────────────────┤
│   │ /coverage            │ cobertura_800m │ (mismos)                     │
│   ├──────────────────────┼────────────────┼──────────────────────────────┤
│   │ /capillary           │ fc_puntos      │ min_fc=3, snap_tolerance_m=50│
│   ├──────────────────────┼────────────────┼──────────────────────────────┤
│   │ /capillary           │ fc_hubs        │ top_n=20, snap_tolerance_m=50│
│   ├──────────────────────┼────────────────┼──────────────────────────────┤
│   │ /detour              │ df_puntos      │ sample_size=100, seed=42     │
│   ├──────────────────────┼────────────────┼──────────────────────────────┤
│   │ /detour              │ df_por_alcaldia│ sample_size=100, seed=42     │
│   │                      │                │ entidades=["Ciudad de México"]│
│   └──────────────────────┴────────────────┴──────────────────────────────┘
│
├── fetch_layer(session, layer_def, overrides) → GeoDataFrame
│   └── GET {BASE_URL}/{endpoint}?layer={layer_name}&{params}
│       → response.json() → GeoDataFrame.from_features(features)
│
├── write_gpkg(gdfs: dict[str, GeoDataFrame], path: Path)
│   └── por cada (layer_name, gdf): gdf.to_file(path, layer=layer_name, driver="GPKG")
│   └── escribe capa _meta al final
│
└── main()  ← argparse
    --mode      live | cached          (default: live)
    --layer     nombre_layer | all     (default: all)
    --url       base URL de VFTModel   (default: http://localhost:8000)
    --output    ruta del .gpkg         (default: data/processed/VFTOutput.gpkg)
    --radio-m   int                    (default: 800)
    --entidades JSON string            (default: '["Ciudad de México"]')
```

---

## 7. Salida: `data/processed/VFTOutput.gpkg`

Un solo archivo GeoPackage con las siguientes capas:

| Layer | Geometría | CRS de escritura |
|-------|-----------|-----------------|
| `cobertura_por_alcaldia` | Polygon | EPSG:4326 |
| `estaciones` | Point | EPSG:4326 |
| `cobertura_800m` | MultiPolygon | EPSG:4326 |
| `fc_puntos` | Point | EPSG:4326 |
| `fc_hubs` | Point | EPSG:4326 |
| `df_puntos` | Point | EPSG:4326 |
| `df_por_alcaldia` | Polygon | EPSG:4326 |
| `_meta` | *(sin geometría)* | — |

QGIS carga este archivo como fuente de datos. Los proyectos `.qgz` referencian
las capas por nombre, por lo que los nombres de layer son **estables y no deben cambiar**.
