# ── Stage 1: Builder ──────────────────────────────────────────────────────────
# Instala dependencias en una imagen temporal para no contaminar la final
FROM python:3.12-slim AS builder

# GDAL y dependencias del SO para GeoPandas / Fiona / Shapely
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    gdal-bin \
    libgeos-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Solo las libs del SO que necesita el runtime (no el compilador)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal32 \
    libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar paquetes instalados desde el builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código fuente del proyecto
COPY src/ ./src/
COPY pytest.ini .

# Variable de entorno por defecto: apunta a DEV (modo producción del contenedor)
# Override en runtime: docker run -e APIMETRO_URL=http://... vftmodel
ENV APIMETRO_URL=https://apimetro.dev/movilidad

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
