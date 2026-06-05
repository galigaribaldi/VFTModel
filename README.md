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

## Prerequisito: Make

Los comandos de este proyecto se ejecutan con `make`. Instalación por SO:

| SO | Instrucción |
|---|---|
| **Ubuntu / Debian** | `sudo apt-get install -y make` |
| **macOS** | `xcode-select --install` (ya incluye make) |
| **Windows** | Instalar [Git Bash](https://gitforwindows.org/) — incluye make. Alternativamente: `choco install make` (Chocolatey) o `scoop install make` |

> En Windows se recomienda correr todos los comandos desde **Git Bash** o **WSL**, no desde CMD ni PowerShell.

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

## uvicorn vs Docker — ¿Cuándo usar cada uno?

| | uvicorn (directo) | Docker |
|---|---|---|
| RAM extra | — | ~10 MB overhead del contenedor |
| CPU overhead | — | <1% en Linux (sin VM); mayor en Mac/Windows |
| Arranque | ~2-3 s | ~5-10 s |
| Hot reload al guardar | ✅ `--reload` automático | ❌ requiere rebuild |
| Dependencias GDAL del SO | Requieren instalación manual | ✅ incluidas en la imagen |
| Acceso al debugger / IDE | ✅ directo | Más complejo |
| Reproducibilidad entre máquinas | Depende del SO | ✅ garantizada |

**Recomendación:**

- **Desarrollo del modelo** → `make run` o `make run-dev`. El hot reload al guardar un archivo es clave cuando se itera sobre algoritmos o endpoints.
- **Consumo desde clientes externos** (QGIS, Transport-gis-zmvm-mjg) → `make docker-run`. Entorno estable apuntando a `apimetro.dev`, sin dependencias del OS local del desarrollador.

> En Linux el overhead de Docker es mínimo (los contenedores son procesos con namespaces, no VMs). En macOS y Windows, Docker Desktop corre una VM Linux — el overhead de CPU/RAM es mayor y el arranque más lento.

---

## Correr el servidor

### Con Make (recomendado)

```bash
source venv/bin/activate   # Linux / macOS
# En Windows (Git Bash): source venv/Scripts/activate

make run                   # uvicorn LOCAL  — puerto 8000
make run-dev               # uvicorn DEV    — puerto 8000 → apimetro.dev
make docker-build          # construye la imagen Docker
make docker-run            # Docker DEV     — puerto 8000 → apimetro.dev
make docker-run-local      # Docker LOCAL   — puerto 8000 → localhost:8080
```

**Puerto personalizado** — cualquier comando acepta `PORT=`:
```bash
make run PORT=8001
make docker-run PORT=8002
```

Ver todos los comandos disponibles:
```bash
make help
```

### Sin Make (manual)

```bash
source venv/bin/activate

# uvicorn LOCAL
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# uvicorn DEV
ENV_FILE=.env.dev python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Docker DEV
docker run -p 8000:8000 vftmodel

# Docker LOCAL (Linux)
docker run -p 8000:8000 --add-host=host.docker.internal:host-gateway \
  -e APIMETRO_URL=http://host.docker.internal:8080/movilidad vftmodel

# Docker LOCAL (macOS / Windows — host.docker.internal resuelve automáticamente)
docker run -p 8000:8000 -e APIMETRO_URL=http://host.docker.internal:8080/movilidad vftmodel
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
