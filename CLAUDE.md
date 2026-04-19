# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Vanishing Fig-Tree Model (VFT Model)** — Motor analítico geoespacial y topológico para la evaluación de redes de transporte en la Ciudad de México. Calculates three topological indicators for urban transport networks: capillary strength (nodal centrality), spatial coverage (geographic reach), and detour factor (route efficiency).

## Running the Server

```bash
# Activate virtual environment first
source venv/bin/activate

# Start FastAPI server (development)
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Or directly
python src/api/main.py
```

API docs available at `http://localhost:8000/docs` (Swagger UI).

## Key Dependencies

```
FastAPI 0.110.0, Uvicorn 0.29.0, httpx 0.27.0, Pydantic 2.6.4
GeoPandas 0.14.3, NetworkX 3.2.1, Momepy 0.7.0, Shapely 2.0.3
```

Install: `pip install -r requirements.txt`

There is no formal test suite. Validation happens via Pydantic schemas and Jupyter notebooks in `notebooks/`.

## Architecture

Hexagonal architecture with three layers:

```
FastAPI (src/api/)  →  Domain Logic (src/core/)  →  Infrastructure (src/infrastructure/)
```

**Request flow for a typical topological endpoint:**
1. FastAPI validates request with Pydantic schemas (`src/api/schemas/`)
2. CPU-bound work is delegated to a thread pool via `asyncio.to_thread`
3. `get_or_build_graph()` checks an in-memory cache keyed by `(mode, tolerance_m)`; on miss, fetches from the Go backend via `src/infrastructure/go_client/client.py` (falls back to `map.geojson` if unavailable)
4. `VFTGraphBuilder` constructs the NetworkX graph in two phases: base network (stations→nodes, routes→edges), then optional pedestrian snapping (transfer edges between stations within tolerance)
5. `VFTImpedanceModel` weights edges by travel time: `(haversine_distance / velocity) × friction_coefficient + boarding_cost`
6. A topological analyzer runs on the graph and returns a Pandas DataFrame
7. FastAPI returns JSON

## Core Components

### `src/core/services/graph_builder.py` — `VFTGraphBuilder`

Two build modes:
- `STRICT_TOPOLOGY`: Mathematical graph, no intermodal transfers
- `REALISTIC_INTEGRATION`: Adds pedestrian walking edges within a configurable tolerance

Pre-configured distance thresholds (meters): `MIN=15, Q1=85, Q2=180, MEAN=245, Q3=420, MAX=880`

### `src/core/models/impedance.py` — `VFTImpedanceModel`

Friction coefficients based on right-of-way type. Travel time formula:
```
impedance = (haversine(a, b) / velocity) × friction + frequency/2
```

### `src/core/algorithms/topologicalIndicators/`

| File | Class | What it computes |
|------|-------|-----------------|
| `capillar_strength.py` | `CapillaryStrengthAnalyzer` | Nodal degree centrality with spatial grid hashing (0.001° cells); filters internal trace nodes |
| `spatial_coverage.py` | `SpatialCoverageAnalyzer` | % of each jurisdiction (alcaldía/municipio) covered by 800m station buffers |
| `detaur_factor.py` | `DetourFactorAnalyzer` | DF = Network distance / Euclidean distance for sampled O-D pairs |

### `src/api/schemas/` — Pydantic Validation

- 4-level transport hierarchy enum: heavy mass → light surface
- 4 right-of-way types: exclusive / confined / shared / mixed
- Taxonomy imputation rules for missing fields
- CETRAM (transit center) node support

### `src/infrastructure/go_client/`

- `client.py`: Fetches stations + lines from Go backend concurrently; merges into a single FeatureCollection
- `client_spatial.py`: Fetches territorial polygons (CDMX + State of Mexico) with fan-out/fan-in pattern

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/network/build-auto` | Build and cache graph |
| `GET /api/v1/network/spatial-coverage` | Coverage % by jurisdiction |
| `GET /api/v1/network/topological/capillary-strength` | Nodal degree ranking |
| `GET /api/v1/network/topological/geo-capillary` | Proximity macro-hub detection |
| `GET /api/v1/network/topological/detour-factor` | Route efficiency (general + arbitrary nodes) |

## Notebooks

`notebooks/` contains four sequential analysis notebooks. They use local GeoJSON data in `notebooks/ASSETS/` and are the primary exploratory/validation environment (no formal test suite exists).

## Open Development Items (from NOTES.txt)

- Verify Haversine formula for segment velocities and average speeds
- Correct impedance analysis notebook and code
- Check analysis by AGEBs (Electoral Section) in CDMX and State of Mexico
- Improve capillary force documentation with component formulas
