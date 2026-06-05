# ── VFT Model — Makefile ──────────────────────────────────────────────────────
# Uso básico:      make <comando>
# Puerto custom:   make <comando> PORT=8001
#
# Ejemplos:
#   make run                  → uvicorn LOCAL en puerto 8000
#   make run PORT=8001        → uvicorn LOCAL en puerto 8001
#   make run-dev PORT=8002    → uvicorn DEV en puerto 8002
#   make docker-run PORT=8003 → Docker DEV en puerto 8003

PORT ?= 8000

# ── Desarrollo (uvicorn) ──────────────────────────────────────────────────────

run:
	ENV_FILE=.env.local python -m uvicorn src.api.main:app --host 0.0.0.0 --port $(PORT) --reload

run-dev:
	ENV_FILE=.env.dev python -m uvicorn src.api.main:app --host 0.0.0.0 --port $(PORT) --reload

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:
	docker build -t vftmodel .

docker-run:
	docker run -p $(PORT):8000 vftmodel

docker-run-local:
	docker run -p $(PORT):8000 \
		--add-host=host.docker.internal:host-gateway \
		-e APIMETRO_URL=http://host.docker.internal:8080/movilidad \
		vftmodel

# ── Utilidades ────────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

help:
	@echo ""
	@echo "VFT Model — Comandos disponibles"
	@echo "─────────────────────────────────────────────────────"
	@echo "  make install            Instala dependencias Python"
	@echo "  make run                uvicorn LOCAL  (default: puerto 8000)"
	@echo "  make run-dev            uvicorn DEV    (apimetro.dev)"
	@echo "  make docker-build       Construye la imagen Docker"
	@echo "  make docker-run         Docker DEV     (apimetro.dev)"
	@echo "  make docker-run-local   Docker LOCAL   (localhost:8080)"
	@echo "  make test               Corre la suite pytest"
	@echo ""
	@echo "  Puerto personalizado:   make <comando> PORT=8001"
	@echo "─────────────────────────────────────────────────────"
	@echo ""

.PHONY: run run-dev docker-build docker-run docker-run-local install test help
