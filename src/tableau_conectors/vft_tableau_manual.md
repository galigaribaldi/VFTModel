# VFTModel — Manual de Integración con Tableau

Este documento tiene dos audiencias:

- **Analista de Tableau / Transport GIS** — busca la sección "Inicio rápido" (§0) y el "Protocolo de actualización" (§10). No necesita leer más.
- **Desarrollador / IA que retoma el trabajo** — documento completo: decisiones de diseño, esquemas exactos, protocolo para agregar nuevos indicadores.

---

## Índice

0. [Inicio rápido — cargar datos en Tableau Desktop](#0-inicio-rápido--cargar-datos-en-tableau-desktop)
1. [Contexto y responsabilidades](#1-contexto-y-responsabilidades)
2. [Arquitectura de conectores](#2-arquitectura-de-conectores)
3. [Prerrequisitos de ejecución](#3-prerrequisitos-de-ejecución)
4. [Estado actual — 7 GeoLayers implementados](#4-estado-actual--7-geolayers-implementados)
5. [Estrategia por tipo de geometría](#5-estrategia-por-tipo-de-geometría)
6. [Esquemas de tablas para el WDC](#6-esquemas-de-tablas-para-el-wdc)
7. [Tiempos de respuesta medidos](#7-tiempos-de-respuesta-medidos)
8. [Protocolo para agregar nuevos indicadores](#8-protocolo-para-agregar-nuevos-indicadores)
9. [Estructura de archivos del directorio](#9-estructura-de-archivos-del-directorio)
10. [Protocolo de actualización — re-exportar cuando VFTModel cambie](#10-protocolo-de-actualización--re-exportar-cuando-vftmodel-cambie)
11. [Referencia de endpoints](#11-referencia-de-endpoints)

---

## 0. Inicio rápido — cargar datos en Tableau Desktop

### Qué necesitas

Dos carpetas del repositorio **Transport GIS**:

```
vft_wdc.html                          ← conector de tablas de puntos
exports/
  cobertura_por_alcaldia.geojson      ← polígonos de cobertura por alcaldía
  cobertura_800m.geojson              ← mancha de cobertura unificada
  df_por_alcaldia.geojson             ← Factor de Desviación agregado por alcaldía
```

### Paso 1 — Servicios activos (quien opera VFTModel)

Antes de abrir Tableau, los dos servicios deben estar corriendo:

| Servicio | Puerto | Comando |
|----------|--------|---------|
| Apimetro (backend Go) | 8080 | `make dev` en el repo apimetro |
| VFTModel API | 8000 | `make run` en el repo VFTModel |

> Si solo vas a trabajar con las capas de polígonos (GeoJSON estáticos), los servicios **no son necesarios** — Tableau los abre desde disco.

### Paso 2 — Cargar las 6 tablas de puntos (WDC)

1. Tableau Desktop → **Conectar** → **Conector de datos web**
2. Ingresar la ruta local al archivo `vft_wdc.html` (o arrastrarlo a la ventana)
3. En el formulario del conector:
   - **URL base de VFTModel**: `http://localhost:8000`
   - **Tamaño de muestra**: 100 (aumentar para más precisión en Factor de Desviación)
   - **Radio de cobertura**: 800 m
4. Clic en **Cargar datos en Tableau**
5. El conector llama primero a `build-auto` para calentar el grafo (~18 ms si ya está en caché, ~30 s la primera vez), luego descarga las 6 tablas

Tablas que aparecerán en Tableau:

| Tabla | Indicador | Filas aprox. |
|-------|-----------|-------------|
| `estaciones` | Estaciones de toda la red | ~800 |
| `fc_puntos` | Fuerza Capilar por nodo | ~10,537 |
| `fc_hubs` | Macro-hubs intermodales | top 20 |
| `df_puntos` | Factor de Desviación (pares O-D) | según muestra |
| `b_puntos` | Centralidad de Intermediación (B) | ~10,561 |
| `t_escalar` | Tiempo Promedio de Viaje (T) | 1 fila (KPI global) |

### Paso 3 — Cargar las 3 capas de polígonos (Spatial File)

Para cada archivo `.geojson` en `exports/`:

1. Tableau Desktop → **Conectar** → **Archivo espacial**
2. Seleccionar el archivo `.geojson`
3. Tableau lo abrirá como una capa geográfica con geometría de polígono

| Archivo | Contiene | Geometría |
|---------|----------|-----------|
| `cobertura_por_alcaldia.geojson` | % cobertura peatonal (800 m) por alcaldía | Polygon |
| `cobertura_800m.geojson` | Mancha unificada de cobertura | MultiPolygon |
| `df_por_alcaldia.geojson` | Factor de Desviación promedio por alcaldía | Polygon |

### Paso 4 — Crear extracto (recomendado)

Después de cargar todas las fuentes, crear un extracto `.hyper` (**Datos → Extraer datos**) para trabajar sin conexión y mejorar el rendimiento.

---

## 1. Contexto y responsabilidades

**VFTModel** es el motor analítico. Su responsabilidad termina al exponer los datos: no genera visualizaciones ni proyectos `.twb`/`.qgz`. El repositorio de visualización en Tableau es independiente.

Lo que **sí** vive en este directorio:

- El archivo WDC (`vft_wdc.html`) que Tableau carga como fuente de datos tabulares.
- El script de exportación de GeoJSON estáticos para las capas con geometrías complejas.
- Este manual.

Lo que **no** vive aquí:

- El proyecto `.twb` / `.twbx` de Tableau (repositorio separado).
- Estilos, colores, cálculos de Tableau ni configuración de dashboards.

### Relación con el conector de Apimetro

El directorio `requerimientos_apimetro_tableau.md` documenta cómo el backend Go (Apimetro) se conectó a Tableau. El patrón es idéntico para VFTModel:

- **WDC** para datos tabulares y capas de puntos (lat/lon extraído).
- **GeoJSON estático** para capas con geometrías de tipo Polygon o MultiPolygon (Tableau las carga como Spatial File, no admite estas geometrías vía WDC).

---

## 2. Arquitectura de conectores

```
Tableau Desktop
    │
    ├── [Conector de datos web]  ──────►  vft_wdc.html
    │       │                                │
    │       │  tablas de puntos              │  llama a VFTModel API (localhost:8000)
    │       │                                │
    │       └── estaciones                   ├── GET /geolayers/coverage?layer=estaciones
    │       └── fc_puntos                    ├── GET /geolayers/capillary?layer=fc_puntos
    │       └── fc_hubs                      ├── GET /geolayers/capillary?layer=fc_hubs
    │       └── df_puntos                    └── GET /geolayers/detour?layer=df_puntos
    │
    └── [Archivo espacial]  ───────────►  exports/
            │                                │
            │  capas de polígonos            ├── cobertura_por_alcaldia.geojson
            ├── cobertura_por_alcaldia        ├── cobertura_800m.geojson
            ├── cobertura_800m               └── df_por_alcaldia.geojson
            └── df_por_alcaldia
```

> **Por qué la separación?** Tableau WDC 2.x solo admite datos tabulares (filas y columnas). Las geometrías de tipo Polygon y MultiPolygon requieren entrar como Spatial File. Las capas de puntos se tabulariza extrayendo `lat` y `lon`, lo que sí funciona en WDC.

---

## 3. Prerrequisitos de ejecución

Antes de abrir Tableau, los siguientes servicios deben estar activos:

| Servicio | Puerto | Comando |
|----------|--------|---------|
| **Apimetro** (backend Go) | 8080 | `make dev` en el repo apimetro |
| **VFTModel API** (FastAPI) | 8000 | `source .venv/bin/activate && make run` |

Verificar que el grafo está en caché (obligatorio antes de que el WDC llame a los endpoints analíticos):

```
GET http://localhost:8000/api/v1/network/build-auto?mode=REALISTIC_INTEGRATION&tolerance_m=85
```

Respuesta esperada:
```json
{ "status": "success", "mensaje": "Grafo listo y en caché.", "nodos": 11115, "aristas": 45497 }
```

Si el grafo no está en caché, los endpoints de cobertura, fuerza capilar y detour tardarán entre 15 y 60 segundos la primera vez. Con caché, los tiempos son los documentados en la sección 7.

---

## 4. Estado actual — 8 GeoLayers implementados

Fuente canónica: `src/api/routes/geo_layers.py`. Cada layer es una capa GeoJSON `FeatureCollection` con la envoltura estándar VFT.

| Layer | Endpoint | Geometría | Método Tableau | Fase | Estado |
|-------|----------|-----------|----------------|------|--------|
| `cobertura_por_alcaldia` | `/geolayers/coverage` | Polygon | Spatial File | 1 | ✅ |
| `estaciones` | `/geolayers/coverage` | Point | WDC | 1 | ✅ |
| `cobertura_800m` | `/geolayers/coverage` | MultiPolygon | Spatial File | 1 | ✅ |
| `fc_puntos` | `/geolayers/capillary` | Point | WDC | 1 | ✅ |
| `fc_hubs` | `/geolayers/capillary` | Point | WDC | 1 | ✅ |
| `df_puntos` | `/geolayers/detour` | Point | WDC | 1 | ✅ |
| `df_por_alcaldia` | `/geolayers/detour` | Polygon | Spatial File | 1 | ✅ |
| `b_puntos` | `/geolayers/betweenness` | Point | WDC | 3 | ✅ |
| `t_escalar` | `/topological/average-travel-time` | Sin geometría (escalar global) | WDC — 1 fila | 3 | ✅ |

> **Nota `b_puntos`:** migrado a GeoLayer estándar en `geo_layers.py` (2026-09-06). El WDC ahora lo parsea con `rowsFromFeatures()` igual que los otros 4 layers de puntos. El endpoint anterior `/topological/betweenness-centrality` se mantiene en `main.py` para uso en Swagger UI con `summary` y `limit`.

> **Nota `t_escalar`:** se decidió **no** homologar a GeoLayer. Es un KPI escalar global sin geometría espacial — forzarlo a `FeatureCollection` sería artificial. Permanece en `main.py` como endpoint analítico independiente. El WDC lo trata como caso especial de 1 fila.

### Envoltura estándar de toda respuesta

Todo endpoint GeoLayers devuelve:

```json
{
  "type": "FeatureCollection",
  "metadata": {
    "indicador":  "cobertura | capillary | detour",
    "layer":      "nombre_del_layer",
    "n_features": 16,
    "crs":        "EPSG:4326",
    "fetched_at": "2026-09-05T03:46:05Z",
    "parametros": { ... }
  },
  "features": [ ... ]
}
```

CRS de todas las capas: **EPSG:4326 (WGS84)**. No se requiere reproyección en Tableau.

---

## 5. Estrategia por tipo de geometría

### 5.1 Capas de puntos → WDC

El WDC extrae `geometry.coordinates[0]` (lon) y `geometry.coordinates[1]` (lat) de cada Feature y los agrega como columnas numéricas. Tableau las reconoce como coordenadas geográficas si se marcan con el rol geográfico correspondiente.

**Capas que van al WDC:** `estaciones`, `fc_puntos`, `fc_hubs`, `df_puntos`.

### 5.2 Capas de polígonos → GeoJSON estático (Spatial File)

Tableau Desktop puede abrir un archivo `.geojson` directamente desde **Conectar → Archivo espacial**. El archivo puede ser local o una URL que devuelva `Content-Type: application/geo+json`.

**Capas que van como Spatial File:** `cobertura_por_alcaldia`, `cobertura_800m`, `df_por_alcaldia`.

El script `export_geojson.py` descarga estas tres capas desde la API, valida que la respuesta sea GeoJSON válido y las guarda en `exports/`. Ejecutar cuando los datos de base cambien (nueva versión de Apimetro, nuevo cálculo).

```bash
# Desde la raíz del repositorio VFTModel, con el servidor activo:
make export-geojson

# Puerto personalizado:
make export-geojson PORT=9000
```

El script llama `build-auto` automáticamente para asegurar que el grafo esté en caché antes de exportar. Si el servidor no está activo o devuelve un error, falla con un mensaje claro en lugar de guardar silenciosamente un archivo inválido.

---

## 6. Esquemas de tablas para el WDC

Estas son las columnas que el WDC declara en `getSchema` y los campos de `properties` de cada Feature que mapean a ellas. El campo `id`, `nombre`, `indicador` y `layer` son estándar en todas las capas (contrato VFT_CLIENT_SPEC.md).

### 6.1 Tabla `estaciones`

Fuente: `GET /api/v1/network/geolayers/coverage?layer=estaciones`

| Columna WDC | Tipo | Campo en `properties` | Descripción |
|-------------|------|-----------------------|-------------|
| `id` | string | `id` | Identificador único |
| `nombre` | string | `nombre` | Nombre de la estación |
| `sistema` | string | `sistema` | METRO, MB, RTP, TL, TROLE, CBB, CC… |
| `tipo_entidad` | string | `tipo_entidad` | estacion, paradero, terminal |
| `sistemas_count` | int | `sistemas_count` | Número de sistemas que conecta |
| `lat` | float | extraído de `geometry.coordinates[1]` | Latitud WGS84 |
| `lon` | float | extraído de `geometry.coordinates[0]` | Longitud WGS84 |

### 6.2 Tabla `fc_puntos`

Fuente: `GET /api/v1/network/geolayers/capillary?layer=fc_puntos`

| Columna WDC | Tipo | Campo en `properties` | Descripción |
|-------------|------|-----------------------|-------------|
| `id` | string | `id` | Coordenada nodo como string `(lon, lat)` |
| `nombre` | string | `nombre` | Nombre de la estación |
| `fc_total` | float | `fc_total` | Fuerza Capilar Total (grado nodal) |
| `cx_entrada` | int | `cx_entrada` | Conexiones entrantes |
| `cx_salida` | int | `cx_salida` | Conexiones salientes |
| `sistemas` | string | `sistemas` | JSON-encoded list: `'["Metro","Metrobús"]'` |
| `sistemas_count` | int | `sistemas_count` | Número de sistemas |
| `tipo_nodo` | string | `tipo_nodo` | hub_principal / hub_secundario / nodo_relevante / nodo_basico |
| `lat` | float | extraído de `geometry.coordinates[1]` | Latitud |
| `lon` | float | extraído de `geometry.coordinates[0]` | Longitud |

Umbrales de `tipo_nodo` (definidos en `geo_layers.py:_clasify_node`):

| Valor | Condición |
|-------|-----------|
| `hub_principal` | `fc_total > 20` |
| `hub_secundario` | `fc_total > 10` |
| `nodo_relevante` | `fc_total > 6` |
| `nodo_basico` | `fc_total <= 6` |

### 6.3 Tabla `fc_hubs`

Fuente: `GET /api/v1/network/geolayers/capillary?layer=fc_hubs`

| Columna WDC | Tipo | Campo en `properties` | Descripción |
|-------------|------|-----------------------|-------------|
| `id` | string | `id` | Nombre del macro-hub |
| `nombre` | string | `nombre` | Nombre del macro-hub |
| `estaciones_agrupadas` | int | `estaciones_agrupadas` | Nodos agrupados en el hub |
| `fc_total` | float | `fc_total` | Fuerza Capilar Total del hub |
| `sistemas` | string | `sistemas` | JSON-encoded list |
| `sistemas_count` | int | `sistemas_count` | Número de sistemas |
| `lat` | float | extraído de `geometry.coordinates[1]` | Latitud |
| `lon` | float | extraído de `geometry.coordinates[0]` | Longitud |

### 6.4 Tabla `df_puntos`

Fuente: `GET /api/v1/network/geolayers/detour?layer=df_puntos`

| Columna WDC | Tipo | Campo en `properties` | Descripción |
|-------------|------|-----------------------|-------------|
| `id` | string | `id` | `Origen_Destino` concatenado |
| `nombre` | string | `nombre` | `"Origen → Destino"` |
| `factor_desviacion` | float | `factor_desviacion` | Factor de Desviación de la ruta |
| `origen` | string | `origen` | Nombre del nodo origen |
| `destino` | string | `destino` | Nombre del nodo destino |
| `dist_red_km` | float | `dist_red_km` | Distancia recorrida por la red (km) |
| `dist_recta_km` | float | `dist_recta_km` | Distancia en línea recta (km) |
| `sistemas` | string | `sistemas` | JSON-encoded list |
| `categoria_df` | string | `categoria_df` | eficiente / moderado / alto / critico |
| `lat` | float | extraído de `geometry.coordinates[1]` | Coordenada de inicio de ruta |
| `lon` | float | extraído de `geometry.coordinates[0]` | Coordenada de inicio de ruta |

Umbrales de `categoria_df` (definidos en `geo_layers.py:_clasify_diff`):

| Valor | Condición |
|-------|-----------|
| `eficiente` | `factor_desviacion <= 1.3` |
| `moderado` | `1.3 < factor_desviacion <= 1.6` |
| `alto` | `1.6 < factor_desviacion <= 2.0` |
| `critico` | `factor_desviacion > 2.0` |

---

### 6.5 Tabla `b_puntos` — Centralidad de Intermediación (Fase 3)

Fuente: `GET /api/v1/network/topological/betweenness-centrality?limit=100`

Estructura de respuesta:
```json
{
  "status": "success",
  "data": {
    "summary": { "total_stations_ranked": N, "top_5": [...] },
    "ranking": [
      { "node_id": "...", "nombre": "Tacubaya", "sistema": "METRO",
        "alcaldia_municipio": "Miguel Hidalgo", "es_cetram": true,
        "lon": -99.187, "lat": 19.401, "betweenness_centrality": 0.2179 }
    ]
  }
}
```

El WDC itera `response.data.ranking`. El campo `lon`/`lat` ya viene aplanado — no hay que extraerlos de `geometry.coordinates`.

| Columna WDC | Tipo | Campo en JSON | Descripción |
|-------------|------|---------------|-------------|
| `node_id` | string | `ranking[i].node_id` | ID interno del nodo en el grafo |
| `nombre` | string | `ranking[i].nombre` | Nombre de la estación |
| `sistema` | string | `ranking[i].sistema` | METRO, MB, RTP… |
| `alcaldia_municipio` | string | `ranking[i].alcaldia_municipio` | Alcaldía o municipio |
| `es_cetram` | bool | `ranking[i].es_cetram` | Si la estación es CETRAM |
| `betweenness_centrality` | float | `ranking[i].betweenness_centrality` | B(v) normalizado [0–1] |
| `lat` | float | `ranking[i].lat` | Latitud WGS84 |
| `lon` | float | `ranking[i].lon` | Longitud WGS84 |

> **Primera ejecución:** 30–90 s (algoritmo de Brandes sobre ~10,561 nodos). Con caché: <100 ms. El WDC debe mostrar un mensaje de espera o hacer el build-auto + warmup de B antes de cargar la tabla.

### 6.6 Tabla `t_escalar` — Tiempo Promedio de Viaje (Fase 3)

Fuente: `GET /api/v1/network/topological/average-travel-time`

Estructura de respuesta:
```json
{
  "status": "success",
  "data": {
    "T_average_travel_time_minutes": 108.92,
    "graph_info": { "nodes": 10561, "edges": 43200, "is_strongly_connected": true },
    "reference": { "expected_cdmx_approx": 85.0, "unit": "minutes" }
  }
}
```

Es un indicador escalar global — una sola fila. Se usa como KPI en Tableau, no como capa de mapa.

| Columna WDC | Tipo | Campo en JSON | Descripción |
|-------------|------|---------------|-------------|
| `T_minutos` | float | `data.T_average_travel_time_minutes` | Tiempo promedio de viaje en minutos |
| `nodos_scc` | int | `data.graph_info.nodes` | Nodos de la componente gigante |
| `aristas_scc` | int | `data.graph_info.edges` | Aristas de la componente gigante |
| `referencia_cdmx` | float | `data.reference.expected_cdmx_approx` | Valor de referencia esperado (85 min) |

> **Primera ejecución:** 2–5 minutos (all-pairs shortest paths). Con caché: <100 ms.

---

## 7. Tiempos de respuesta medidos

Medidos con el servidor local y el grafo **en caché** (`REALISTIC_INTEGRATION`, `tolerance_m=85`). Apimetro corriendo en `localhost:8080`.

| Endpoint | Layer | Features | Tiempo (caché caliente) |
|----------|-------|----------|------------------------|
| `build-auto` | — | — | ~18 ms (hit de caché) |
| `/geolayers/coverage` | `cobertura_por_alcaldia` | 16 | ~2.1 s |
| `/geolayers/capillary` | `fc_puntos` | 10,537 | ~0.5 s |
| `/geolayers/detour` | `df_por_alcaldia` | 16 | ~1.9 s |

**Primera llamada sin caché:** el grafo tarda 15–60 s en construirse según el hardware. El WDC debe documentar este comportamiento o hacer el `build-auto` automáticamente.

**Implicación para Tableau:** la carga inicial del WDC tomará ~5 s sumando todas las tablas (con caché caliente). Crear un extracto `.hyper` después de la primera carga para trabajar sin conexión.

---

## 8. Protocolo para agregar nuevos indicadores

Cuando se implemente un nuevo indicador en `src/core/algorithms/` y se exponga vía `src/api/routes/geo_layers.py`, el conector Tableau debe actualizarse siguiendo estos pasos:

### Paso 1 — Identificar el tipo de geometría

Revisar qué devuelve el nuevo endpoint:

| Tipo de geometría | Acción en el conector |
|-------------------|-----------------------|
| `Point` | Agregar tabla nueva al WDC |
| `LineString` / `MultiLineString` | No entra en WDC. Agregar al script `export_geojson.py` |
| `Polygon` / `MultiPolygon` | No entra en WDC. Agregar al script `export_geojson.py` |

### Paso 2 — Documentar el esquema de la tabla (en este archivo)

Agregar una sección nueva en el apartado 6 con:
- Fuente (endpoint + parámetros por defecto)
- Tabla de columnas WDC: nombre, tipo, campo en `properties`, descripción
- Umbrales de clasificación si el campo tiene categorías

### Paso 3 — Si es capa de puntos: agregar al WDC

En `vft_wdc.html`, dentro del array `connector.getSchema`:

```javascript
// Ejemplo esqueleto para un nuevo indicador "tiempo_promedio"
{
  id: "tiempo_promedio",
  alias: "Tiempo Promedio de Viaje (T)",
  columns: [
    { id: "id",              dataType: tableau.dataTypeEnum.string },
    { id: "nombre",          dataType: tableau.dataTypeEnum.string },
    { id: "tiempo_promedio", dataType: tableau.dataTypeEnum.float  },
    { id: "lat",             dataType: tableau.dataTypeEnum.float  },
    { id: "lon",             dataType: tableau.dataTypeEnum.float  }
    // agregar los campos propios del indicador aquí
  ]
}
```

En `connector.getData`, agregar el `case` correspondiente:

```javascript
case "tiempo_promedio":
  url = `${BASE_URL}/geolayers/tiempo_promedio?layer=t_puntos&sample_size=100`;
  // fetch, mapear features → rows, extraer lat/lon de geometry.coordinates
  break;
```

### Paso 4 — Si es capa de polígonos/líneas: agregar al script de exportación

En `export_geojson.py`, agregar una entrada al array `LAYERS`:

```python
{
    "name": "nueva_capa",
    "url": "/api/v1/network/geolayers/nuevo_endpoint?layer=nueva_capa&param=valor",
},
```

Luego re-exportar con:

```bash
make export-geojson
```

### Paso 5 — Actualizar la tabla de estado (sección 4 de este documento)

Agregar la nueva fila a la tabla de GeoLayers con: layer, endpoint, geometría, método Tableau, fase, estado.

---

### Indicadores pendientes (Fase 4)

Los siguientes indicadores aún no están implementados. Cuando se implementen, seguir el protocolo anterior.

| Indicador | Issue | Fase | Tipo de geometría esperado | Método Tableau |
|-----------|-------|------|---------------------------|----------------|
| Robustez Geométrica (ΔE) | #5 | 4 | Por definir | Por definir |
| Node Score Tipo B (VFT_score) | #12 | — | Point (nodo) | WDC |

**Fase 3 completada (PR #15 — 2026-07-05):**
- T implementado en `topological/average_travel_time/` → tabla `t_escalar` en el WDC
- B implementado en `topological/betweenness_centrality/` → tabla `b_puntos` en el WDC
- SCC verificado: componente gigante 95.02% (10,561/11,115 nodos)

---

## 9. Estructura de archivos del directorio

```
src/tableau_conectors/
│
├── vft_tableau_manual.md          ← Este archivo. Leer antes de tocar cualquier otro.
├── requerimientos_apimetro_tableau.md  ← Referencia: cómo apimetro se conectó a Tableau.
│
├── vft_wdc.html                   ← WDC con 6 tablas (5 de puntos + t_escalar).
├── export_geojson.py              ← Script de exportación de capas de polígonos (make export-geojson).
│
└── exports/                       ← GeoJSON estáticos generados por el script.
    ├── cobertura_por_alcaldia.geojson
    ├── cobertura_800m.geojson
    └── df_por_alcaldia.geojson
```

---

## 10. Protocolo de actualización — re-exportar cuando VFTModel cambie

Ejecutar este protocolo cuando:
- Se mergea un PR con cambios en algoritmos o datos de red
- Se actualiza la versión de Apimetro (nuevas estaciones o líneas)
- Se implementa un indicador nuevo de Fase 4

### Pasos

**En el repo VFTModel** (quien opera el motor):

```bash
# 1. Jalar los últimos cambios
git pull origin DEV

# 2. Levantar el servidor
source .venv/bin/activate
make run                          # Terminal 1 — dejar corriendo

# 3. Re-exportar los GeoJSON estáticos
make export-geojson               # Terminal 2

# Salida esperada:
# Verificando grafo en caché... OK — success, 11115 nodos
# cobertura_por_alcaldia... ✓  16 features
# cobertura_800m...         ✓  1 features
# df_por_alcaldia...        ✓  16 features
```

Los 3 archivos se generan en `src/tableau_conectors/exports/`.  
> Estos archivos están en `.gitignore` de VFTModel — **no** se commitean aquí.

**En el repo Transport GIS** (quien mantiene la visualización):

```bash
# 4. Copiar los GeoJSON regenerados al repo de Transport GIS
cp /ruta/a/VFTModel/src/tableau_conectors/exports/*.geojson \
   /ruta/a/TransportGIS/data/vftmodel/

# 5. Commitear y pushear
cd /ruta/a/TransportGIS
git add data/vftmodel/*.geojson
git commit -m "chore(data): actualizar GeoJSON VFTModel — <fecha o versión>"
git push
```

**En Tableau Desktop** (el analista):

```
6. Abrir el libro .twb / .twbx
7. Datos → [cada GeoJSON] → Actualizar ahora
8. Si usas extracto: Datos → Extraer datos → Actualizar extracto
```

### Cuándo NO es necesario re-exportar

| Cambio en VFTModel | ¿Re-exportar? |
|--------------------|---------------|
| Fix de bug en API sin cambio de datos | No |
| Nueva versión de Apimetro (nuevas estaciones) | **Sí** |
| Cambio en parámetros de `radio_m` o `sample_size` | **Sí**, si cambia el análisis |
| Refactor de código sin cambio de resultados | No |
| Indicador nuevo agregado | **Sí**, y también actualizar el WDC |

---

## 11. Referencia de endpoints

Base URL local: `http://localhost:8000`

### Cache warming (ejecutar primero, siempre)

```
GET /api/v1/network/build-auto?mode=REALISTIC_INTEGRATION&tolerance_m=85
```

### GeoLayers — Cobertura

```
GET /api/v1/network/geolayers/coverage
  ?layer=cobertura_por_alcaldia
  &radio_m=800
  &entidades=Ciudad de México

GET /api/v1/network/geolayers/coverage
  ?layer=estaciones
  &radio_m=800
  &entidades=Ciudad de México

GET /api/v1/network/geolayers/coverage
  ?layer=cobertura_800m
  &radio_m=800
  &entidades=Ciudad de México
```

### GeoLayers — Fuerza Capilar

```
GET /api/v1/network/geolayers/capillary
  ?layer=fc_puntos
  &min_fc=3
  &snap_tolerance_m=50

GET /api/v1/network/geolayers/capillary
  ?layer=fc_hubs
  &top_n=20
  &snap_tolerance_m=50
```

### GeoLayers — Factor de Desviación

```
GET /api/v1/network/geolayers/detour
  ?layer=df_puntos
  &sample_size=100
  &seed=42

GET /api/v1/network/geolayers/detour
  ?layer=df_por_alcaldia
  &sample_size=100
  &seed=42
  &entidades=Ciudad de México
```

### GeoLayers — Centralidad de Intermediación (Fase 3)

```
GET /api/v1/network/geolayers/betweenness
  ?layer=b_puntos
  &limit=2000
```

`limit=0` devuelve todos los nodos (~10,561). Primera ejecución: 30–90 s. Con caché: <100 ms.

### Endpoints analíticos no-GeoLayer (Fase 3)

```
GET /api/v1/network/topological/average-travel-time
GET /api/v1/network/topological/betweenness-centrality?limit=100
```

Estos endpoints usan la envoltura `{ "status", "parametros", "data" }` en lugar de `FeatureCollection`. Se mantienen para consumo directo en Swagger UI y para `t_escalar` en el WDC.

### Parámetros de modo de grafo (todos los endpoints analíticos)

| Parámetro | Default | Opciones |
|-----------|---------|----------|
| `mode` | `REALISTIC_INTEGRATION` | `STRICT_TOPOLOGY`, `REALISTIC_INTEGRATION` |
| `tolerance_m` | `85` | Metros. Umbrales pre-configurados: 15, 85, 180, 245, 420, 880 |

---

*Última actualización: 2026-09-07. b_puntos migrado a GeoLayer estándar (`/geolayers/betweenness`); t_escalar documentado como KPI no-GeoLayer por diseño. Incluye §0 Inicio rápido, §10 Protocolo de actualización. Basado en la medición directa contra el servidor local con apimetro en `localhost:8080`.*
