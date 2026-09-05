#!/usr/bin/env bash
# VFTModel — Exportación de capas de polígonos para Tableau Spatial File
#
# Descarga las 3 capas con geometrías complejas (Polygon/MultiPolygon) desde
# la API local y las guarda como archivos .geojson en exports/.
#
# Tableau las carga mediante: Conectar → Archivo espacial → seleccionar .geojson
#
# Uso:
#   bash export_geojson.sh                  # usa localhost:8000 por defecto
#   bash export_geojson.sh http://localhost:9000
#
# Prerequisito: VFTModel corriendo + grafo en caché (build-auto ya ejecutado).

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORTS_DIR="$SCRIPT_DIR/exports"

mkdir -p "$EXPORTS_DIR"

echo "VFTModel GeoJSON Export"
echo "Base URL: $BASE_URL"
echo "Destino:  $EXPORTS_DIR"
echo "──────────────────────────────────────"

# ── 1. cobertura_por_alcaldia (Polygon) ──────────────────────────────────────
echo -n "Descargando cobertura_por_alcaldia... "
curl -sf "$BASE_URL/api/v1/network/geolayers/coverage?layer=cobertura_por_alcaldia&radio_m=800&entidades=Ciudad+de+M%C3%A9xico" \
  -o "$EXPORTS_DIR/cobertura_por_alcaldia.geojson"
echo "✓  ($(wc -c < "$EXPORTS_DIR/cobertura_por_alcaldia.geojson" | tr -d ' ') bytes)"

# ── 2. cobertura_800m (MultiPolygon — mancha de cobertura unificada) ─────────
echo -n "Descargando cobertura_800m... "
curl -sf "$BASE_URL/api/v1/network/geolayers/coverage?layer=cobertura_800m&radio_m=800&entidades=Ciudad+de+M%C3%A9xico" \
  -o "$EXPORTS_DIR/cobertura_800m.geojson"
echo "✓  ($(wc -c < "$EXPORTS_DIR/cobertura_800m.geojson" | tr -d ' ') bytes)"

# ── 3. df_por_alcaldia (Polygon — Factor de Desviación agregado) ─────────────
echo -n "Descargando df_por_alcaldia... "
curl -sf "$BASE_URL/api/v1/network/geolayers/detour?layer=df_por_alcaldia&sample_size=100&seed=42&entidades=Ciudad+de+M%C3%A9xico" \
  -o "$EXPORTS_DIR/df_por_alcaldia.geojson"
echo "✓  ($(wc -c < "$EXPORTS_DIR/df_por_alcaldia.geojson" | tr -d ' ') bytes)"

echo "──────────────────────────────────────"
echo "Listo. Archivos en $EXPORTS_DIR"
echo ""
echo "Para cargar en Tableau Desktop:"
echo "  Conectar → Archivo espacial → seleccionar cada .geojson"
echo ""
echo "Para agregar una capa con URL dinámica (sin archivo local):"
echo "  Conectar → Conector de datos web → ingresar la URL del endpoint directamente"
echo "  Nota: solo funciona si el servidor está activo al abrir el libro."
