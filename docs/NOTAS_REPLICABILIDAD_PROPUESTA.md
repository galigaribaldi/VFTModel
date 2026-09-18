# Notas de Replicabilidad — Propuesta Anillo Periférico Interior

**Fecha:** 2026-09-16 | **Actualizado:** 2026-09-18
**Contexto:** Réplica del estudio VFTModel con red propuesta de Anillo Periférico Interior
**Estado:** VFTModel listo para ejecución — 0 cambios de código, solo configuración de entorno

---

## 1. Propuesta General

Replicar el análisis topológico completo del modelo VFT sobre **3 escenarios** que permiten comparar el impacto de agregar un Anillo Periférico Interior a la red actual de transporte de la ZMVM:

| Escenario | Contenido | Datos en Apimetro |
|-----------|-----------|-------------------|
| **Baseline** | Red actual de transporte (sin modificaciones) | DB original: 12 sistemas, ~1600 estaciones |
| **Escenario MB** | Red actual + 4 líneas de anillo periférico como Metrobús (BRT) | DB original + 98 estaciones + 8 ramales (`sistema=MB`) |
| **Escenario METRO** | Red actual + 4 líneas de anillo periférico como Metro | DB original + 98 estaciones + 8 ramales (`sistema=METRO`) |

Las 4 líneas del anillo (IDs 71-74) están subdivididas por punto cardinal: Sur, Poniente, Norte, Oriente. El inicio de una línea comparte coordenadas exactas con el final de la anterior, cerrando un anillo completo.

### Hipótesis del estudio

El Anillo Periférico Interior como corredor de transporte masivo:
- **Reduce el tiempo promedio de viaje (T)** al crear atajos que acortan caminos mínimos
- **Redistribuye la carga de intermediación (B)** — los nodos del anillo absorben tráfico de nodos saturados
- **Mejora el factor de desviación (DI)** — rutas más directas por el periférico
- **Aumenta la cobertura (C)** — nuevas estaciones cubren zonas sin servicio previo

La comparación MB vs METRO permite evaluar si el tipo de tecnología (BRT vs Metro pesado) altera significativamente estos indicadores, dado que comparten la misma geometría pero difieren en velocidad, frecuencia y fricción.

---

## 2. Arquitectura de 3 Escenarios — Cadena Completa

### 2.1 Diagrama general

Cada escenario es una cadena aislada de 3 servicios: Apimetro (fuente) → VFTModel (cálculo) → Transport-gis (visualización). **Ningún contenedor comparte datos con otro.**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APIMETRO (Go + PostgreSQL/PostGIS)                  │
│                         Rama: feat/propuesta-anillar                        │
│                                                                             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐       │
│  │ apimetro_api_dev  │  │ apimetro_api_     │  │ apimetro_api_     │       │
│  │ :8080             │  │ scenario_mb       │  │ scenario_metro    │       │
│  │                   │  │ :8083             │  │ :8084             │       │
│  │ Red actual        │  │ Red + anillo MB   │  │ Red + anillo METRO│       │
│  │ (12 sistemas)     │  │ (+98 est, +8 ram) │  │ (+98 est, +8 ram) │       │
│  └────────┬──────────┘  └────────┬──────────┘  └────────┬──────────┘       │
│           │ geojsonEstacion      │                      │                   │
│           │ geojsonLinea         │                      │                   │
└───────────┼──────────────────────┼──────────────────────┼───────────────────┘
            │                      │                      │
            ▼                      ▼                      ▼
┌───────────┼──────────────────────┼──────────────────────┼───────────────────┐
│           │              VFTMODEL (Python + FastAPI)     │                   │
│           │              Rama: feat/replicabilidad-entornos                  │
│           │                                                                 │
│  ┌────────┴──────────┐  ┌───────┴───────────┐  ┌───────┴───────────┐       │
│  │ VFTModel Baseline │  │ VFTModel MB       │  │ VFTModel METRO    │       │
│  │ :8000             │  │ :8001             │  │ :8002             │       │
│  │ .env.local        │  │ .env.scenario-mb  │  │ .env.scenario-    │       │
│  │                   │  │                   │  │ metro             │       │
│  │ APIMETRO_URL=     │  │ APIMETRO_URL=     │  │ APIMETRO_URL=     │       │
│  │ localhost:8080    │  │ localhost:8083    │  │ localhost:8084    │       │
│  │                   │  │                   │  │                   │       │
│  │ Grafo: ~11,100    │  │ Grafo: ~11,200    │  │ Grafo: ~11,200    │       │
│  │ nodos             │  │ nodos (+98)       │  │ nodos (+98)       │       │
│  │                   │  │                   │  │                   │       │
│  │ Indicadores:      │  │ Indicadores:      │  │ Indicadores:      │       │
│  │ SCC, T, B, C,     │  │ SCC, T, B, C,     │  │ SCC, T, B, C,     │       │
│  │ k_in, DI          │  │ k_in, DI          │  │ k_in, DI          │       │
│  └────────┬──────────┘  └───────┬───────────┘  └───────┬───────────┘       │
│           │ /geolayers/*        │                      │                   │
└───────────┼─────────────────────┼──────────────────────┼───────────────────┘
            │                     │                      │
            ▼                     ▼                      ▼
┌───────────┼─────────────────────┼──────────────────────┼───────────────────┐
│           │         TRANSPORT-GIS-ZMVM-MJG             │                   │
│           │                                                                 │
│  ┌────────┴──────────┐  ┌──────┴────────────┐  ┌──────┴────────────┐       │
│  │ VFTClient         │  │ VFTClient         │  │ VFTClient         │       │
│  │ url=:8000         │  │ url=:8001         │  │ url=:8002         │       │
│  │                   │  │                   │  │                   │       │
│  │ → baseline/       │  │ → scenario_mb/    │  │ → scenario_metro/ │       │
│  │   *.geojson       │  │   *.geojson       │  │   *.geojson       │       │
│  │ → VFTOutput.gpkg  │  │ → VFTOutput_      │  │ → VFTOutput_      │       │
│  │                   │  │   scenario_mb.gpkg│  │   scenario_metro  │       │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘       │
│                                                                             │
│  → QGIS (mapas comparativos)                                               │
│  → Tableau (dashboards)                                                     │
│  → Tesis LaTeX (figuras PNG)                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Inventario de contenedores y procesos

En total corren **7 procesos** (4 contenedores Docker + 3 procesos Python):

| # | Proceso | Tipo | Puerto | Contenido |
|---|---------|------|--------|-----------|
| 1 | `apimetro_api_dev` | Docker | `:8080` | API Go — red actual |
| 2 | `apimetro_api_scenario_mb` | Docker | `:8083` | API Go — red + anillo MB |
| 3 | `apimetro_api_scenario_metro` | Docker | `:8084` | API Go — red + anillo METRO |
| 4 | VFTModel baseline | uvicorn | `:8000` | FastAPI — consume `:8080` |
| 5 | VFTModel scenario-mb | uvicorn | `:8001` | FastAPI — consume `:8083` |
| 6 | VFTModel scenario-metro | uvicorn | `:8002` | FastAPI — consume `:8084` |
| 7 | Transport-gis | CLI Python | — | Consume `:8000`, `:8001`, `:8002` secuencialmente |

> Los contenedores de DB de Apimetro (`:5433`, `:5436`, `:5437`) son internos y no los consume VFTModel directamente.

---

## 3. Decisión Arquitectónica: Claves Existentes

Se decidió usar las claves de sistema ya existentes en VFTModel (`"MB"` y `"METRO"`) en lugar de crear nuevas (como `"METRO_ANILLO"` o `"MB_PERIF"`). Esto elimina la necesidad de modificar código en VFTModel:

- `SistemaTransporte` enum en `src/api/schemas/schemas.py` → sin cambio
- `FALLBACK_VELOCIDAD` y `FALLBACK_FRECUENCIA` en `src/core/models/impedance.py` → sin cambio
- `FALLBACK_FRECUENCIA` en `src/core/services/graph_builder.py` → sin cambio
- `FrictionCalculator` en `src/core/models/impedance.py` → sin cambio (lee `derecho_de_via` del GeoJSON)

Las nuevas líneas heredan automáticamente los parámetros operativos del sistema al que pertenecen. El campo `clasificacion = 'propuesta_periferico'` que Apimetro usa para etiquetar los datos hipotéticos nunca es leído por VFTModel — es transparente para el motor analítico.

---

## 4. Parámetros Operativos por Escenario

| Propiedad | Baseline | Escenario MB | Escenario METRO |
|-----------|----------|-------------|-----------------|
| Datos del anillo | No | Si (como BRT) | Si (como Metro) |
| `sistema` (anillo) | — | `"MB"` | `"METRO"` |
| `jerarquia_transporte` | — | `"masivo_mediano"` | `"masivo_pesado"` |
| `derecho_de_via` | — | `"confinado"` | `"exclusivo"` |
| `velocidad_promedio_kmh` | — | `16.3 km/h` | `36.0 km/h` |
| `frecuencia_minutos` | — | `5.0 min` | `3.0 min` |
| Fricción resultante (CF) | — | `1.152` (alpha=0.2) | `1.0` (alpha=0.0) |
| Boarding cost (transbordo) | — | `2.5 min` | `1.5 min` |

---

## 5. Datos que VFTModel Extrae de Cada Contenedor Apimetro

VFTModel llama a **2 endpoints** de Apimetro al construir el grafo (`fetch_full_network()` en `src/infrastructure/go_client/client.py`):

```
GET {APIMETRO_URL}/mapas/geojsonEstacion   → todas las estaciones como GeoJSON Points
GET {APIMETRO_URL}/mapas/geojsonLinea      → todos los ramales como GeoJSON MultiLineStrings
```

### Lo que recibe cada instancia de VFTModel

| Dato | Baseline (:8080) | Escenario MB (:8083) | Escenario METRO (:8084) |
|------|-------------------|----------------------|-------------------------|
| Estaciones totales | ~1,600 | ~1,600 + 98 del anillo | ~1,600 + 98 del anillo |
| Ramales totales | ~180 | ~180 + 8 del anillo | ~180 + 8 del anillo |
| Sistemas presentes | 12 (METRO, MB, RTP...) | 12 (mismos, MB incluye anillo) | 12 (mismos, METRO incluye anillo) |
| Datos cruzados | — | 0 datos METRO del anillo | 0 datos MB del anillo |

### Transformación en VFTModel

Con esos datos, VFTModel construye un grafo dirigido (`DiGraph` de NetworkX):

1. **Estaciones → Nodos**: `node_id = (lon, lat)`. Estaciones del anillo con coordenadas idénticas a estaciones existentes se fusionan en un solo nodo (transbordo implícito).

2. **Ramales → Aristas**: El graph builder usa un KDTree (`SNAP_TOLERANCE_DEG ≈ 50m`) para detectar qué estaciones caen sobre cada trazo de línea y crea aristas entre estaciones consecutivas.

3. **Impedancia**: Cada arista recibe un peso `weight = (haversine / velocidad) * friccion`. Las aristas del anillo heredan la velocidad, frecuencia y fricción del sistema al que pertenecen (MB o METRO).

4. **Transbordos peatonales** (modo `REALISTIC_INTEGRATION`): El builder conecta estaciones de distintos sistemas que estén a ≤85m (tolerancia Q1) con aristas de caminata ponderadas por distancia + tiempo de espera.

---

## 6. Endpoints que VFTModel Sirve a Transport-gis

Cada instancia de VFTModel expone los mismos endpoints. Transport-gis solo necesita apuntar al puerto correcto.

### 6.1 Warmup (construir grafo y cachear indicadores pesados)

```bash
# Construir grafo — primera llamada: 15-30s, con caché: <100ms
GET /api/v1/network/build-auto?mode=REALISTIC_INTEGRATION&tolerance_m=85

# Tiempo promedio (T) — primera llamada: 2-5 min, con caché: <100ms
GET /api/v1/network/topological/average-travel-time

# Intermediación (B) — primera llamada: 5-8 min, con caché: <100ms
GET /api/v1/network/topological/betweenness-centrality
```

### 6.2 GeoLayers (lo que Transport-gis consume para GeoJSON/.gpkg)

| Endpoint | Layer | Geometría | Indicador |
|----------|-------|-----------|-----------|
| `GET /geolayers/coverage?layer=cobertura_por_alcaldia` | `cobertura_por_alcaldia` | Polygon | Cobertura (C) |
| `GET /geolayers/coverage?layer=estaciones` | `estaciones` | Point | Cobertura (C) |
| `GET /geolayers/coverage?layer=cobertura_800m` | `cobertura_800m` | MultiPolygon | Cobertura (C) |
| `GET /geolayers/capillary?layer=fc_puntos` | `fc_puntos` | Point | Fuerza Capilar (k_in) |
| `GET /geolayers/capillary?layer=fc_hubs` | `fc_hubs` | Point | Fuerza Capilar (k_in) |
| `GET /geolayers/detour?layer=df_puntos` | `df_puntos` | Point | Detour Factor (DI) |
| `GET /geolayers/detour?layer=df_por_alcaldia` | `df_por_alcaldia` | Polygon | Detour Factor (DI) |
| `GET /geolayers/betweenness?layer=b_puntos` | `b_puntos` | Point | Intermediación (B) |

Todos los endpoints devuelven `FeatureCollection` con `metadata` estándar (indicador, layer, n_features, crs, parametros). El formato completo está en `VFT_CLIENT_SPEC.md` del repo transport-gis.

---

## 7. Comandos de Ejecución — VFTModel

### 7.1 Pre-requisitos

```bash
# Activar entorno virtual
source venv/bin/activate

# Verificar que los contenedores Apimetro estén corriendo
curl -s localhost:8080/health   # Baseline (DEV)
curl -s localhost:8083/health   # Escenario MB
curl -s localhost:8084/health   # Escenario METRO
```

### 7.2 Levantar las 3 instancias (3 terminales)

```bash
# Terminal 1 — Baseline (red actual, sin anillo)
make run PORT=8000
# Lee .env.local → APIMETRO_URL=http://localhost:8080/movilidad

# Terminal 2 — Escenario MB (red + anillo como BRT)
make run-scenario-mb PORT=8001
# Lee .env.scenario-mb → APIMETRO_URL=http://localhost:8083/movilidad

# Terminal 3 — Escenario METRO (red + anillo como Metro)
make run-scenario-metro PORT=8002
# Lee .env.scenario-metro → APIMETRO_URL=http://localhost:8084/movilidad
```

### 7.3 Verificar en Swagger

- `http://localhost:8000/docs` → Baseline
- `http://localhost:8001/docs` → Escenario MB
- `http://localhost:8002/docs` → Escenario METRO

### 7.4 Verificación rápida con curl

```bash
# Construir grafo en las 3 instancias (lanzar en paralelo)
curl -s "localhost:8000/api/v1/network/build-auto" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Baseline:', d.get('nodos','?'), 'nodos')"
curl -s "localhost:8001/api/v1/network/build-auto" | python3 -c "import sys,json; d=json.load(sys.stdin); print('MB:      ', d.get('nodos','?'), 'nodos')"
curl -s "localhost:8002/api/v1/network/build-auto" | python3 -c "import sys,json; d=json.load(sys.stdin); print('METRO:   ', d.get('nodos','?'), 'nodos')"
```

Resultado esperado: MB y METRO deben tener ~98 nodos más que Baseline.

---

## 8. Referencia para Transport-gis

### 8.1 Mapa de puertos

Transport-gis debe consumir cada instancia de VFTModel con su `VFTClient`:

| Escenario | VFTModel URL | Apimetro URL (referencia) | Datos |
|-----------|-------------|---------------------------|-------|
| Baseline | `http://localhost:8000` | `http://localhost:8080` | Red actual |
| Escenario MB | `http://localhost:8001` | `http://localhost:8083` | Red + anillo BRT |
| Escenario METRO | `http://localhost:8002` | `http://localhost:8084` | Red + anillo Metro |

### 8.2 Flujo de ejecución recomendado

```
1. Warmup de los 3 VFTModel (build-auto + T + B en cada puerto)
   → Los indicadores pesados quedan en caché
   → Todas las llamadas posteriores responden en <100ms

2. generate_exports.py --url http://localhost:8000 --scenario baseline
   → tableau/exports/geo/baseline/*.geojson
   → data/processed/VFTOutput_baseline.gpkg

3. generate_exports.py --url http://localhost:8001 --scenario scenario_mb
   → tableau/exports/geo/scenario_mb/*.geojson
   → data/processed/VFTOutput_scenario_mb.gpkg

4. generate_exports.py --url http://localhost:8002 --scenario scenario_metro
   → tableau/exports/geo/scenario_metro/*.geojson
   → data/processed/VFTOutput_scenario_metro.gpkg
```

> **Nota:** Los flags `--url` y `--scenario` son una propuesta para transport-gis. Actualmente `generate_exports.py` no los tiene — deben implementarse allá. El cambio es mínimo: pasar `base_url` al `VFTClient` y `output_dir` al `GeoExporter.save()`.

### 8.3 Estructura de salida esperada en Transport-gis

```
tableau/exports/geo/
├── baseline/
│   ├── b_puntos.geojson
│   ├── cobertura_estaciones.geojson
│   ├── df_puntos.geojson
│   ├── fc_puntos.geojson
│   └── ...
├── scenario_mb/
│   ├── b_puntos.geojson
│   ├── cobertura_estaciones.geojson
│   ├── df_puntos.geojson
│   ├── fc_puntos.geojson
│   └── ...
└── scenario_metro/
    ├── b_puntos.geojson
    ├── cobertura_estaciones.geojson
    ├── df_puntos.geojson
    ├── fc_puntos.geojson
    └── ...

data/processed/
├── VFTOutput_baseline.gpkg
├── VFTOutput_scenario_mb.gpkg
└── VFTOutput_scenario_metro.gpkg
```

Cada carpeta contiene exactamente los mismos archivos (mismos nombres, misma estructura). La diferencia son los datos: cada escenario tiene su propia red y sus propios valores de indicadores.

### 8.4 Warmup por escenario desde Transport-gis

El Makefile de `tableau/` en transport-gis actualmente calienta solo `:8000`. Para los 3 escenarios, necesita un target que caliente los 3 puertos. Ejemplo:

```makefile
warmup-scenarios:
	@echo "Calentando los 3 escenarios de VFTModel..."
	@for port in 8000 8001 8002; do \
		echo "  [$${port}] build-auto..."; \
		curl -s --max-time 60 "http://localhost:$${port}/api/v1/network/build-auto?mode=REALISTIC_INTEGRATION&tolerance_m=85" > /dev/null; \
		echo "  [$${port}] average-travel-time (T)..."; \
		curl -s --max-time 360 "http://localhost:$${port}/api/v1/network/topological/average-travel-time" > /dev/null; \
		echo "  [$${port}] betweenness (B)..."; \
		curl -s --max-time 600 "http://localhost:$${port}/api/v1/network/geolayers/betweenness?layer=b_puntos&limit=2000" > /dev/null; \
		echo "  [$${port}] OK"; \
	done
	@echo "Los 3 escenarios están en caché."
```

---

## 9. Componentes de VFTModel que NO se Modifican

**Cero líneas de código Python fueron modificadas para soportar los escenarios.**

| Componente | Archivo | Razón |
|------------|---------|-------|
| Enum `SistemaTransporte` | `src/api/schemas/schemas.py:35-48` | MB y METRO ya existen |
| Velocidades fallback | `src/core/models/impedance.py:37-50` | Ya definidas para MB y METRO |
| Frecuencias fallback | `src/core/models/impedance.py:52-65` | Ya definidas para MB y METRO |
| Frecuencias graph builder | `src/core/services/graph_builder.py:36-39` | Ya definidas para MB y METRO |
| Fricción (CF) | `src/core/models/impedance.py:17-30` | Lee `derecho_de_via` del GeoJSON |
| Cliente Apimetro | `src/infrastructure/go_client/client.py` | Descarga cualquier sistema, sin filtros |
| Graph builder | `src/core/services/graph_builder.py` | Agnóstico a la cantidad de líneas/estaciones |
| Caché | `src/api/dependencies.py` | Dict en memoria, aislado por proceso |
| Todos los indicadores | `src/core/algorithms/` | Algoritmos genéricos de NetworkX/GeoPandas |
| GeoLayers API | `src/api/routes/geo_layers.py` | Serialización genérica de DataFrames |

### Archivos que sí cambian (solo configuración)

| Archivo | Cambio |
|---------|--------|
| `.env.scenario-mb` | **Nuevo** — `APIMETRO_URL=http://localhost:8083/movilidad` |
| `.env.scenario-metro` | **Nuevo** — `APIMETRO_URL=http://localhost:8084/movilidad` |
| `Makefile` | 2 targets nuevos: `run-scenario-mb`, `run-scenario-metro` |
| `docs/NOTAS_REPLICABILIDAD_PROPUESTA.md` | Este documento |

---

## 10. Indicadores Esperados por Escenario

### 10.1 Indicadores que cambian entre escenarios

| Indicador | Baseline | MB (BRT) | METRO |
|-----------|----------|----------|-------|
| **SCC** (% comp. gigante) | ~95% | Sube levemente | Sube levemente |
| **T** (tiempo promedio) | Referencia | Baja moderada (16.3 km/h, CF=1.152) | Baja fuerte (36 km/h, CF=1.0) |
| **B** (intermediación) | Referencia | Redistribución moderada | Redistribución fuerte |
| **DI** (detour factor) | Referencia | Mejora leve | Mejora fuerte |
| **C** (cobertura %) | Referencia | Sube (98 estaciones nuevas) | Sube (misma geometría) |
| **k_in** (fuerza capilar) | Referencia | Nuevos hubs en intersecciones | Misma topología, mismos hubs |

### 10.2 Indicadores idénticos entre MB y METRO

- **C** (cobertura): mismas estaciones, misma geometría → cobertura idéntica
- **k_in** (fuerza capilar): misma topología de red → grado nodal idéntico
- **SCC**: misma estructura de conexiones → componente gigante igual

### 10.3 Indicadores que difieren entre MB y METRO

- **T**: velocidad y fricción distintas → tiempos de viaje distintos
- **B**: pesos de aristas distintos → caminos mínimos distintos → redistribución distinta
- **DI**: depende de los pesos → rutas más directas con velocidad alta (METRO)

---

## 11. Checklist de Ejecución

### Pre-requisitos (completados)
- [x] Apimetro Baseline corriendo en `:8080` (make docker-dev en repo Apimetro)
- [x] Apimetro Escenario MB corriendo en `:8083` (make docker-dev-scenario-mb)
- [x] Apimetro Escenario METRO corriendo en `:8084` (make docker-dev-scenario-metro)
- [x] Aislamiento verificado: 0 datos cruzados entre escenarios
- [x] `.env.scenario-mb` y `.env.scenario-metro` creados
- [x] Targets `run-scenario-mb` y `run-scenario-metro` en Makefile

### Ejecución — VFTModel (este repo)
- [ ] Levantar las 3 instancias (`:8000`, `:8001`, `:8002`)
- [ ] Verificar que cada instancia responde en Swagger
- [ ] `build-auto` en las 3 → confirmar que MB/METRO tienen ~98 nodos más que baseline

### Ejecución — Transport-gis (repo transport-gis-zmvm-mjg)
- [ ] Warmup de indicadores pesados (T, B) en los 3 puertos
- [ ] `generate_exports.py --url :8000 --scenario baseline`
- [ ] `generate_exports.py --url :8001 --scenario scenario_mb`
- [ ] `generate_exports.py --url :8002 --scenario scenario_metro`
- [ ] Verificar que los 3 conjuntos de GeoJSON están en carpetas separadas

### Post-ejecución
- [ ] Comparar indicadores escalares (T, SCC) entre los 3 escenarios
- [ ] Mapas comparativos en QGIS/Tableau
- [ ] Documentar hallazgos para la tesis
