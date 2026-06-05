"""
Tests de integración — GeoLayer /capillary
Layers: fc_puntos | fc_hubs
"""
import pytest

BASE   = "/api/v1/network/geolayers/capillary"
PARAMS = {"mode": "REALISTIC_INTEGRATION", "tolerance_m": 85}
MIN_FC = 3
TOP_N  = 20


# ──────────────────────────────────────────────────────────────────────────────
# fc_puntos
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fc_puntos(client):
    res = client.get(BASE, params={**PARAMS, "layer": "fc_puntos", "min_fc": MIN_FC})
    assert res.status_code == 200, res.text[:300]
    return res.json()


def test_puntos_status(fc_puntos):
    assert fc_puntos["type"] == "FeatureCollection"


def test_puntos_n_features_positivo(fc_puntos):
    assert fc_puntos["metadata"]["n_features"] > 0


def test_puntos_geometry_point(fc_puntos):
    tipos = {f["geometry"]["type"] for f in fc_puntos["features"]}
    assert tipos == {"Point"}, f"Tipos inesperados: {tipos}"


def test_puntos_fc_total_sobre_umbral(fc_puntos):
    valores = [f["properties"]["fc_total"] for f in fc_puntos["features"]]
    bajo_umbral = [v for v in valores if v < MIN_FC]
    assert not bajo_umbral, f"fc_total < {MIN_FC} encontrado: {bajo_umbral[:5]}"


def test_puntos_propiedades_presentes(fc_puntos):
    required = {"id", "nombre", "fc_total", "cx_entrada", "cx_salida",
                "sistemas", "sistemas_count", "tipo_nodo"}
    for feat in fc_puntos["features"]:
        assert required <= feat["properties"].keys()


def test_puntos_tipo_nodo_valido(fc_puntos):
    tipos_validos = {"hub_principal", "hub_secundario", "nodo_relevante", "nodo_basico"}
    tipos_recibidos = {f["properties"]["tipo_nodo"] for f in fc_puntos["features"]}
    assert tipos_recibidos <= tipos_validos, f"Tipos no esperados: {tipos_recibidos - tipos_validos}"


# ──────────────────────────────────────────────────────────────────────────────
# fc_hubs
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fc_hubs(client):
    res = client.get(BASE, params={**PARAMS, "layer": "fc_hubs", "top_n": TOP_N})
    assert res.status_code == 200, res.text[:300]
    return res.json()


def test_hubs_status(fc_hubs):
    assert fc_hubs["type"] == "FeatureCollection"


def test_hubs_n_features_respeta_top_n(fc_hubs):
    n = fc_hubs["metadata"]["n_features"]
    assert 0 < n <= TOP_N, f"n_features={n} fuera del rango (0, {TOP_N}]"


def test_hubs_geometry_point(fc_hubs):
    tipos = {f["geometry"]["type"] for f in fc_hubs["features"]}
    assert tipos == {"Point"}, f"Tipos inesperados: {tipos}"


def test_hubs_fc_total_positivo(fc_hubs):
    valores = [f["properties"]["fc_total"] for f in fc_hubs["features"]]
    assert all(v > 0 for v in valores)


def test_hubs_propiedades_presentes(fc_hubs):
    required = {"id", "nombre", "estaciones_agrupadas", "fc_total",
                "sistemas", "sistemas_count"}
    for feat in fc_hubs["features"]:
        assert required <= feat["properties"].keys()
