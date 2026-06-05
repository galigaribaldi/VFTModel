"""
Tests de integración — GeoLayer /detour
Layers: df_puntos | df_por_alcaldia
"""
import pytest

BASE        = "/api/v1/network/geolayers/detour"
PARAMS      = {"mode": "REALISTIC_INTEGRATION", "tolerance_m": 85}
SAMPLE_SIZE = 100
SEED        = 42


# ──────────────────────────────────────────────────────────────────────────────
# df_puntos
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fc_df_puntos(client):
    res = client.get(BASE, params={**PARAMS,
        "layer":       "df_puntos",
        "sample_size": SAMPLE_SIZE,
        "seed":        SEED,
    })
    assert res.status_code == 200, res.text[:300]
    return res.json()


def test_df_puntos_status(fc_df_puntos):
    assert fc_df_puntos["type"] == "FeatureCollection"


def test_df_puntos_n_features_positivo(fc_df_puntos):
    assert fc_df_puntos["metadata"]["n_features"] > 0


def test_df_puntos_n_features_bajo_sample(fc_df_puntos):
    n = fc_df_puntos["metadata"]["n_features"]
    assert n <= SAMPLE_SIZE, f"n_features={n} supera sample_size={SAMPLE_SIZE}"


def test_df_puntos_geometry_point(fc_df_puntos):
    tipos = {f["geometry"]["type"] for f in fc_df_puntos["features"]}
    assert tipos == {"Point"}, f"Tipos inesperados: {tipos}"


def test_df_puntos_factor_desviacion_minimo(fc_df_puntos):
    """Factor de desviación >= 0.95.
    El límite teórico es 1.0, pero coordenadas snapeadas al KDTree acumulan
    ~3% de error geométrico en rutas cortas (<1.5 km). Ver NOTES.txt.
    """
    fds = [f["properties"]["factor_desviacion"] for f in fc_df_puntos["features"]]
    bajo_umbral = [v for v in fds if v < 0.95]
    assert not bajo_umbral, f"factor_desviacion < 0.95 encontrado: {bajo_umbral[:5]}"


def test_df_puntos_propiedades_presentes(fc_df_puntos):
    required = {"id", "nombre", "factor_desviacion", "origen", "destino",
                "dist_red_km", "dist_recta_km", "sistemas", "categoria_df"}
    for feat in fc_df_puntos["features"]:
        assert required <= feat["properties"].keys()


def test_df_puntos_categoria_df_valida(fc_df_puntos):
    categorias_validas = {"eficiente", "moderado", "alto", "critico"}
    recibidas = {f["properties"]["categoria_df"] for f in fc_df_puntos["features"]}
    assert recibidas <= categorias_validas, f"Categorías no esperadas: {recibidas - categorias_validas}"


def test_df_puntos_dist_red_mayor_recta(fc_df_puntos):
    """dist_red_km >= dist_recta_km con tolerancia de 50 m.
    El snapping KDTree puede acumular ~30 m de error en segmentos cortos. Ver NOTES.txt.
    """
    TOLERANCIA_KM = 0.05  # 50 metros
    pares_invalidos = [
        (f["properties"]["dist_red_km"], f["properties"]["dist_recta_km"])
        for f in fc_df_puntos["features"]
        if f["properties"]["dist_red_km"] < f["properties"]["dist_recta_km"] - TOLERANCIA_KM
    ]
    assert not pares_invalidos, f"dist_red < dist_recta - 50m en: {pares_invalidos[:3]}"


# ──────────────────────────────────────────────────────────────────────────────
# df_por_alcaldia
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fc_df_alcaldia(client):
    res = client.get(BASE, params={**PARAMS,
        "layer":       "df_por_alcaldia",
        "sample_size": SAMPLE_SIZE,
        "seed":        SEED,
        "entidades":   "Ciudad de México",
    })
    assert res.status_code == 200, res.text[:300]
    return res.json()


def test_df_alcaldia_status(fc_df_alcaldia):
    assert fc_df_alcaldia["type"] == "FeatureCollection"


def test_df_alcaldia_n_features_rango(fc_df_alcaldia):
    n = fc_df_alcaldia["metadata"]["n_features"]
    assert 0 < n <= 16, f"n_features={n}: se esperaban entre 1 y 16 alcaldías"


def test_df_alcaldia_geometry_type(fc_df_alcaldia):
    tipos = {f["geometry"]["type"] for f in fc_df_alcaldia["features"]}
    assert tipos <= {"Polygon", "MultiPolygon"}, f"Tipos inesperados: {tipos}"


def test_df_alcaldia_df_promedio_minimo(fc_df_alcaldia):
    valores = [f["properties"]["df_promedio"] for f in fc_df_alcaldia["features"]]
    bajo_uno = [v for v in valores if v is not None and v < 1.0]
    assert not bajo_uno, f"df_promedio < 1.0: {bajo_uno}"


def test_df_alcaldia_propiedades_presentes(fc_df_alcaldia):
    required = {"id", "nombre", "df_promedio", "df_stddev", "n_rutas", "categoria_df"}
    for feat in fc_df_alcaldia["features"]:
        assert required <= feat["properties"].keys()


def test_df_alcaldia_n_rutas_positivo(fc_df_alcaldia):
    for feat in fc_df_alcaldia["features"]:
        assert feat["properties"]["n_rutas"] > 0
