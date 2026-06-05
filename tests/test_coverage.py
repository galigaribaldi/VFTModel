"""
Tests de integración — GeoLayer /coverage
Layers: cobertura_por_alcaldia | estaciones | cobertura_800m
"""
import pytest

BASE   = "/api/v1/network/geolayers/coverage"
PARAMS = {"mode": "REALISTIC_INTEGRATION", "tolerance_m": 85}


# ──────────────────────────────────────────────────────────────────────────────
# cobertura_por_alcaldia
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fc_alcaldias(client):
    res = client.get(BASE, params={**PARAMS,
        "layer":    "cobertura_por_alcaldia",
        "radio_m":  800,
        "entidades": "Ciudad de México",
    })
    assert res.status_code == 200, res.text[:300]
    return res.json()


def test_alcaldias_status(fc_alcaldias):
    assert fc_alcaldias["type"] == "FeatureCollection"


def test_alcaldias_n_features(fc_alcaldias):
    assert fc_alcaldias["metadata"]["n_features"] == 16


def test_alcaldias_crs(fc_alcaldias):
    assert fc_alcaldias["metadata"]["crs"] == "EPSG:4326"


def test_alcaldias_cobertura_pct_rango(fc_alcaldias):
    pcts = [f["properties"]["cobertura_pct"] for f in fc_alcaldias["features"]]
    assert all(0 <= p <= 100 for p in pcts), f"Valores fuera de rango: {pcts}"


def test_alcaldias_geometry_type(fc_alcaldias):
    tipos = {f["geometry"]["type"] for f in fc_alcaldias["features"]}
    assert tipos <= {"Polygon", "MultiPolygon"}


def test_alcaldias_propiedades_presentes(fc_alcaldias):
    required = {"id", "nombre", "area_total_km2", "area_cubierta_km2",
                "cobertura_pct", "cobertura_deficit", "categoria_cobertura"}
    for feat in fc_alcaldias["features"]:
        assert required <= feat["properties"].keys()


# ──────────────────────────────────────────────────────────────────────────────
# estaciones
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fc_estaciones(client):
    res = client.get(BASE, params={**PARAMS, "layer": "estaciones"})
    assert res.status_code == 200, res.text[:300]
    return res.json()


def test_estaciones_status(fc_estaciones):
    assert fc_estaciones["type"] == "FeatureCollection"


def test_estaciones_n_features_minimo(fc_estaciones):
    n = fc_estaciones["metadata"]["n_features"]
    assert n > 500, f"Se esperaban >500 estaciones, se recibieron {n}"


def test_estaciones_geometry_point(fc_estaciones):
    tipos = {f["geometry"]["type"] for f in fc_estaciones["features"]}
    assert tipos == {"Point"}, f"Tipos de geometría inesperados: {tipos}"


def test_estaciones_propiedades_presentes(fc_estaciones):
    required = {"id", "nombre", "sistema", "tipo_entidad"}
    for feat in fc_estaciones["features"]:
        assert required <= feat["properties"].keys()


# ──────────────────────────────────────────────────────────────────────────────
# cobertura_800m
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fc_800m(client):
    res = client.get(BASE, params={**PARAMS, "layer": "cobertura_800m", "radio_m": 800})
    assert res.status_code == 200, res.text[:300]
    return res.json()


def test_800m_status(fc_800m):
    assert fc_800m["type"] == "FeatureCollection"


def test_800m_n_features_es_uno(fc_800m):
    """La unión de todos los buffers produce exactamente 1 feature."""
    assert fc_800m["metadata"]["n_features"] == 1


def test_800m_geometry_type(fc_800m):
    tipos = {f["geometry"]["type"] for f in fc_800m["features"]}
    assert tipos <= {"Polygon", "MultiPolygon"}


def test_800m_radio_en_propiedades(fc_800m):
    assert fc_800m["features"][0]["properties"]["radio_m"] == 800
