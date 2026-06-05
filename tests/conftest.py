"""
Fixtures de sesión para la suite de integración VFT GeoLayers.
El cliente httpx y el warmup del grafo se crean una sola vez por ejecución.
"""
import pytest
import httpx

BASE_URL    = "http://localhost:8000"
MODE        = "REALISTIC_INTEGRATION"
TOLERANCE_M = 85


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=180) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def warm_graph(client):
    """Calienta el caché del grafo antes de cualquier test de la suite."""
    res = client.get(
        "/api/v1/network/build-auto",
        params={"mode": MODE, "tolerance_m": TOLERANCE_M}
    )
    assert res.status_code == 200, (
        f"Warmup falló ({res.status_code}). "
        "Verifica que el servidor y el backend Go estén corriendo."
    )
    data = res.json()
    nodos = data.get("nodos", 0)
    assert nodos > 0, (
        f"Grafo construido con 0 nodos. "
        f"Respuesta completa: {data}. "
        "Verifica que el backend Go tenga datos (apimetro)."
    )
