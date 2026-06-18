# CLAUDE.md

Este archivo guía a Claude Code cuando trabaja con este repositorio.

## Descripción del Proyecto

**Vanishing Fig-Tree Model (VFT Model)** — Motor analítico geoespacial y topológico para la evaluación de redes de transporte en la Zona Metropolitana del Valle de México. Calcula 8 indicadores topológicos en 4 fases de desarrollo para redes de transporte urbano.

Este es un proyecto de investigación académica en transporte urbano. El autor del modelo conoce la arquitectura en profundidad.

## Estructura de Carpetas

```
src/
├── api/                    # FastAPI — endpoints y schemas Pydantic
│   ├── main.py             # Entry point (monolítico, pendiente split en routers — Issue #9)
│   ├── routes/             # GeoLayers API (geo_layers.py)
│   └── schemas/            # Validación Pydantic: jerarquía 4 niveles, 4 tipos vía, CETRAM
├── core/                   # Dominio — algoritmos, modelos, servicios
│   ├── algorithms/
│   │   └── topologicalIndicators/
│   │       ├── capillar_strength.py   # Fuerza Capilar (k_in) — Fase 1 ✅
│   │       ├── spatial_coverage.py    # Cobertura Espacial (C) — Fase 1 ✅
│   │       └── detaur_factor.py       # Detour Factor (DI) — Fase 1 ✅
│   ├── models/
│   │   └── impedance.py              # Fricción Vial (CF) — Fase 2 ✅
│   ├── services/
│   │   ├── graph_builder.py           # VFTGraphBuilder (STRICT / REALISTIC)
│   │   └── orchestator.py            # Orquestador de cálculo de rutas
│   └── utils/
└── infrastructure/
    ├── go_client/
    │   ├── client.py                  # Fetch estaciones + líneas de Apimetro
    │   ├── client_spatial.py          # Fetch polígonos territoriales
    │   └── settings.py               # APIMETRO_URL via os.getenv (fuente única)
    ├── geojson_service/
    └── persistence/

tests/                      # Suite pytest de integración (39 tests)
notebooks/                  # Análisis exploratorio y validación (no publicados)
├── ASSETS/                 # GeoJSON y datos locales para notebooks
├── NOTES/                  # Documentación técnica (PDFs, markdown)
DOCSL/                      # Documentación LaTeX del modelo (XeLaTeX + Biber)
```

## Comandos de Ejecución

```bash
# Activar entorno virtual
source venv/bin/activate

# --- Con Make (recomendado) ---
make run               # uvicorn LOCAL en puerto 8000
make run-dev           # uvicorn DEV en puerto 8000
make docker-build      # Build imagen Docker
make docker-run        # Docker DEV en puerto 8000
make docker-run-local  # Docker LOCAL (Linux: requiere --add-host)
make install           # pip install -r requirements.txt
make test              # pytest (requiere servidor activo + apimetro)
# Override de puerto: make run PORT=9000

# --- Sin Make ---
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Multi-entorno

- `.env.local` → `APIMETRO_URL=http://localhost:8080` (desarrollo local con apimetro corriendo)
- `.env.dev` → `APIMETRO_URL=https://apimetro.dev/movilidad` (servidor remoto)
- Selección: `ENV_FILE=.env.dev make run-dev`

API docs: `http://localhost:8000/docs` (Swagger UI)

## Dependencias y Requisitos

```
Python 3.12
FastAPI 0.110.0, Uvicorn 0.29.0, httpx 0.27.0, Pydantic 2.6.4
GeoPandas 0.14.3, NetworkX 3.2.1, Momepy 0.7.0, Shapely 2.0.3
python-dotenv 1.0.1, pytest
```

**Requisito de sistema:** GDAL debe estar instalado a nivel de SO:
- Linux: `sudo apt install gdal-bin libgdal-dev`
- macOS: `brew install gdal`
- Windows: via OSGeo4W o conda

**Docker:** `python:3.12-slim-bookworm` (bookworm fijado — Trixie no tiene libgdal32)

Instalar deps Python: `pip install -r requirements.txt`

## Arquitectura

Arquitectura hexagonal en tres capas:

```
FastAPI (src/api/)  →  Dominio (src/core/)  →  Infraestructura (src/infrastructure/)
```

**Flujo de un endpoint topológico:**
1. FastAPI valida request con schemas Pydantic
2. CPU-bound → `asyncio.to_thread`
3. `get_or_build_graph()` revisa caché en memoria `(mode, tolerance_m)`; en miss, fetch del Go backend (fallback a `map.geojson`)
4. `VFTGraphBuilder` construye grafo NetworkX: red base (estaciones→nodos, rutas→aristas) + snapping peatonal opcional
5. `VFTImpedanceModel` pondera aristas: `(haversine / velocidad) × fricción + boarding_cost`
6. Analizador topológico → DataFrame → JSON

### Graph Builder — Modos

- `STRICT_TOPOLOGY`: Grafo matemático sin transferencias intermodales
- `REALISTIC_INTEGRATION`: Agrega aristas de caminata dentro de tolerancia configurable

Umbrales pre-configurados (metros): `MIN=15, Q1=85, Q2=180, MEAN=245, Q3=420, MAX=880`

### Impedance Model

```
impedance = (haversine(a, b) / velocity) × friction + frequency/2
```

Fricción basada en tipo de derecho de vía. `BETA_SATURACION_CDMX = 0.759` (TomTom Traffic Index).

## Indicadores Topológicos — Roadmap

| # | Indicador | Fase | Estado | Archivo / Issue |
|---|-----------|------|--------|-----------------|
| 1 | Cobertura (C) | 1 | ✅ | `spatial_coverage.py` |
| 2 | Fuerza Capilar (k_in) | 1 | ✅ | `capillar_strength.py` |
| 3 | Detour Factor (DI) | 1 | ✅ | `detaur_factor.py` |
| 4 | Fricción Vial (CF) | 2 | ✅ | `impedance.py` |
| 5 | Penalización Transferencia (W) | 2 | ✅ parcial | `graph_builder.py` |
| 6 | Tiempo Promedio (T) | 3 | ❌ | Issue #2 |
| 7 | Intermediación (B) | 3 | ❌ | Issue #3 |
| 8 | Robustez (ΔE) | 4 | ❌ | Issue #5 |

**Regla de dependencia:** sin Fases 1-2 completadas no se avanza a Fase 3-4.

**Prerequisito Fase 3:** verificar SCC del grafo (Issue #1). Si componente gigante > 80% nodos → implementar T y B directamente.

## API Endpoints

| Endpoint | Descripción |
|----------|-------------|
| `POST /api/v1/network/build-auto` | Construir y cachear grafo |
| `GET /api/v1/network/spatial-coverage` | Cobertura % por jurisdicción |
| `GET /api/v1/network/topological/capillary-strength` | Ranking de grado nodal |
| `GET /api/v1/network/topological/geo-capillary` | Detección de macro-hubs |
| `GET /api/v1/network/topological/detour-factor` | Eficiencia de rutas |
| GeoLayers API (`src/api/routes/geo_layers.py`) | 7 layers GeoJSON para cobertura, capilar, detour |

## Convenciones del Proyecto

### Git — Branching y Commits

```
feature/mi-cambio  →  PR a DEV  →  merge  →  PR de DEV a main  →  merge
```

Nunca push directo a `main` ni `DEV`. Todo vía Pull Request. Ver `CONTRIBUTING.md` para detalles completos.

**Commits:** `tipo(scope): descripción en imperativo` — tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

**Ramas:** `feature/`, `fix/`, `docs/`, `refactor/` + nombre descriptivo.

### Idioma

- Código: nombres de variables y funciones en inglés
- Documentación, notas y comunicación: español
- Comentarios en código: español

### Tests

Suite pytest de integración (39 tests). Requiere servidor activo + apimetro corriendo:
```bash
make run-dev   # terminal 1
make test      # terminal 2
```

No hay suite unitaria formal. Validación adicional vía notebooks y schemas Pydantic.

## Reglas de Trabajo con Claude Code

### Aprobación antes de editar código

Antes de modificar archivos de código (`src/`) o celdas de notebook, presentar:
1. El archivo/celda exacta que cambia
2. Diff legible (actual vs. nuevo)
3. Razón del cambio

Pedir aprobación explícita antes de ejecutar la edición. No aplica a archivos de documentación/notas donde el cambio es claramente aditivo.

### Scope por notebook

No mezclar indicadores entre notebooks. Solo incluir análisis de indicadores cuyo algoritmo esté implementado en `src/core/algorithms/`. Si un indicador está pendiente, mencionarlo como "pendiente en notebook XX" sin estimar valores.

Scope: 01=impedancia/velocidades/Haversine, 02=cobertura, 03=fuerza capilar + detour factor.

## Tracking de Issues

Todos los issues pendientes están en GitHub Issues: https://github.com/galigaribaldi/VFTModel/issues

Categorías: `fase-3`, `fase-4`, `deuda-tecnica`, `documentation`, `bloqueado`.

## Compilar Documentación LaTeX

```bash
cd DOCSL/
xelatex main.tex && biber main && xelatex main.tex && xelatex main.tex
```

Genera `main.pdf` (~25 páginas). Requiere XeLaTeX + Biber.
