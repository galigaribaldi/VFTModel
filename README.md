# Vanishing Fig-Tree Model (VFT Model)

Motor analítico geoespacial y topológico para la evaluación de redes de transporte urbano en la Ciudad de México. Desarrollado como parte de la tesis **TAICMAM** — calcula tres indicadores topológicos sobre el grafo de la red: cobertura espacial, fuerza capilar nodal y factor de desviación de rutas.

📖 [Documentación técnica](https://galigaribaldi.github.io/VFTModel)

---

## Prerequisites

| Requisito | Versión | Notas |
|---|---|---|
| Python | 3.12 | Recomendado con `venv` |
| GDAL / libgdal-dev | — | Requerido por GeoPandas/Fiona — instalar a nivel del SO antes de `pip install` |
| [apimetro](https://github.com/galigaribaldi/apimetro) | — | Backend Go — ver sección **Variables de Entorno** para modos de conexión |

El modelo consume estaciones y líneas desde el backend Go. Sin apimetro activo, el grafo se construye vacío (fallback a `map.geojson` local si existe).

**Ubuntu/Debian:**
```bash
sudo apt-get install -y libgdal-dev gdal-bin
```

**macOS (Homebrew):**
```bash
brew install gdal
```

---

## Instalación

```bash
git clone https://github.com/galigaribaldi/VFTModel.git
cd VFTModel

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

---

## Variables de Entorno

El modelo soporta dos entornos de ejecución configurados via archivo `.env`:

| Variable | Descripción | LOCAL | DEV |
|---|---|---|---|
| `APIMETRO_URL` | URL base del backend Go | `http://localhost:8080/movilidad` | `https://apimetro.dev/movilidad` |

**Configuración inicial:**
```bash
# LOCAL — apimetro corriendo en localhost
cp .env.example .env.local

# DEV — apimetro.dev (servidor remoto)
cp .env.example .env.dev
# Editar .env.dev y cambiar APIMETRO_URL a https://apimetro.dev/movilidad
```

El archivo activo se selecciona al arrancar con la variable `ENV_FILE` (ver sección siguiente).

---

## Correr el servidor

```bash
source venv/bin/activate

# Modo LOCAL (default — requiere apimetro en localhost:8080)
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Modo DEV (conecta a apimetro.dev)
ENV_FILE=.env.dev python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI disponible en `http://localhost:8000/docs`.

Para cachear el grafo antes de usar los endpoints analíticos:

```
GET http://localhost:8000/api/v1/network/build-auto?mode=REALISTIC_INTEGRATION&tolerance_m=85
```

---

## Correr los tests

La suite de integración requiere el servidor activo y apimetro corriendo:

```bash
source venv/bin/activate
pytest tests/ -v
```

39 tests — cobertura de los 7 GeoLayers de la API (`/coverage`, `/capillary`, `/detour`).

---

## Arquitectura

Arquitectura hexagonal en tres capas:

```
FastAPI (src/api/)  →  Dominio (src/core/)  →  Infraestructura (src/infrastructure/)
```

```
VFTModel/
├── src/
│   ├── api/
│   │   ├── routes/         # GeoLayers API — output adapters GeoJSON
│   │   └── schemas/        # Validación Pydantic del GeoJSON de Go
│   ├── core/
│   │   ├── algorithms/     # Indicadores topológicos (cobertura, capilar, detour)
│   │   ├── models/         # Modelo de impedancia y fricción vial
│   │   └── services/       # Constructor del grafo NetworkX
│   └── infrastructure/
│       └── go_client/      # Clientes HTTP al backend apimetro
├── tests/                  # Suite pytest de integración (39 tests)
├── notebooks/              # Análisis exploratorio y validación local
├── VFT_CLIENT_SPEC.md      # Contrato de datos para consumidores externos
└── requirements.txt
```

**Flujo de una petición:**
1. FastAPI valida el request con Pydantic
2. `get_or_build_graph()` consulta el caché en memoria; si hay miss, descarga de apimetro y construye el grafo con `VFTGraphBuilder`
3. El algoritmo topológico corre sobre el grafo y devuelve un DataFrame
4. El router GeoLayers serializa el resultado como FeatureCollection GeoJSON

**Consumidor externo:** [Transport-gis-zmvm-mjg](https://github.com/galigaribaldi/Transport-gis-zmvm-mjg) consume los GeoLayers via `vft_fetcher.py` y genera capas GPKG para QGIS.

---

## Indicadores implementados

| Indicador | Endpoint | Estado |
|---|---|---|
| Cobertura espacial (C) | `GET /api/v1/network/geolayers/coverage` | ✅ |
| Fuerza capilar (k_in) | `GET /api/v1/network/geolayers/capillary` | ✅ |
| Factor de desviación (DI) | `GET /api/v1/network/geolayers/detour` | ✅ |
| Tiempo promedio (T) | — | Pendiente Fase 3 |
| Centralidad de intermediación (B) | — | Pendiente Fase 3 |
| Robustez geométrica (ΔE) | — | Pendiente Fase 4 |
