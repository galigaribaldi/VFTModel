# Referencia Apimetro Local para VFTModel

Documento de referencia para el agente que trabaje en VFTModel. Describe el estado actual de Apimetro corriendo en local (`localhost:8080`) y qué datos puede consumir VFTModel de manera automática u optimizada.

---

## Resumen de lo hecho en Apimetro (sesiones previas)

1. **API base de transporte** — CRUD completo (lineas, estaciones, descripciones) para 11 sistemas: METRO, MB, CBB, RTP, TROLE, TL, MEXIBUS, MEXICABLE, INTERURBANO, CC, TODOS.
2. **Capa GeoJSON espacial** — Endpoints de solo lectura que devuelven `FeatureCollection` directamente consumibles: estaciones (Points), líneas con métricas operativas (LineString), polígonos administrativos (Polygon/MultiPolygon).
3. **Extensión Plutarco (analítica v1)** — AGEBs urbanas INEGI, afluencia mensual por línea y por estación Metro. Datos de censos, SEMOVI y STC Metro (2010-2026).
4. **Infraestructura actual** — Docker multi-entorno. Para correr local: `make docker-dev` levanta API en `:8080` y PostgreSQL+PostGIS en `:5433`.

---

## Cómo levantar Apimetro en local

```bash
cd ~/Documentos/Code/Apimetro
make docker-dev
# API disponible en http://localhost:8080
# DB disponible en localhost:5433
```

Para VFTModel con `.env.local`:
```
APIMETRO_URL=http://localhost:8080/movilidad
```

---

## Rutas que VFTModel ya consume (cliente actual)

El cliente (`src/infrastructure/go_client/`) ya tiene integración con estos endpoints:

| Archivo | Endpoint consumido | Uso en VFTModel |
|---------|-------------------|-----------------|
| `client.py` → `fetch_full_network()` | `GET /movilidad/mapas/geojsonEstacion` | Nodos del grafo (Points) |
| `client.py` → `fetch_full_network()` | `GET /movilidad/mapas/geojsonLinea` | Aristas del grafo (LineStrings + métricas) |
| `client_spatial.py` → `fetch_territorial_polygons()` | `GET /movilidad/mapas/geojsonPoligono?entidad=X` | Jurisdicciones para spatial join |

---

## Catálogo completo de rutas disponibles (localhost:8080)

### 1. GeoJSON espacial — `/movilidad/mapas/`

#### `GET /movilidad/mapas/geojsonEstacion`

Todas las estaciones como GeoJSON Points. **Ya consumido por VFTModel.**

| Param | Tipo | Ejemplo | Nota |
|-------|------|---------|------|
| `sistema` | string | `METRO` | Vacío = todos los sistemas |
| `num_comercial` | string | `1`, `A`, `MB1` | Clave de la línea |
| `alcaldia_municipio` | string | `Cuauhtémoc` | Busca por ubicación |
| `nombre_ramal` | string | `Ramal Politécnico` | Variante de ruta |
| `jerarquia_transporte` | string | `Línea principal`, `Ramal` | |
| `derecho_de_via` | string | `Superficie`, `Elevado`, `Subterráneo` | |
| `es_cetram` | string | `true` / `false` | Filtra nodos multimodales |
| `nombre_cetram` | string | `Indios Verdes` | |
| `cetram_real` | string | `Tacubaya` | Radio 250m alrededor del CETRAM |

**Properties de cada Feature:** nombre, sistema, alcaldía, num_comercial, año, datos CETRAM.

#### `GET /movilidad/mapas/geojsonLinea`

Trazos de líneas con métricas operativas. **Ya consumido por VFTModel.**

| Param | Tipo | Ejemplo | Nota |
|-------|------|---------|------|
| `sistema` | string | `MB` | Vacío = todos |
| `num_comercial` | string | `1` | |
| `nombre_ramal` | string | `IDA`, `REGRESO` | |
| `jerarquia_transporte` | string | `Línea principal` | |
| `derecho_de_via` | string | `Superficie` | |
| `es_cetram` | string | `true` / `false` | |
| `sentido` | string | `1` (ida) / `0` (regreso) | |
| `existe` | string | `true` / `false` | Solo líneas activas |
| `cetram_real` | string | `Pantitlán` | |

**Properties de cada Feature:** velocidad_promedio (km/h), frecuencia (min), capacidad_vehiculo, distancia_metros, derecho_de_via, jerarquia_transporte.

#### `GET /movilidad/mapas/geojsonPoligono`

Límites administrativos. **Ya consumido por VFTModel.**

| Param | Tipo | Ejemplo | Nota |
|-------|------|---------|------|
| `entidad` | string | `CDMX`, `Estado de México` | |
| `nivel` | string | `alcaldia`, `municipio`, `entidad` | |
| `nombre` | string | `Cuauhtémoc` | Nombre exacto |

---

### 2. Analítico (Plutarco) — `/movilidad/analitico/`

Estos endpoints NO están integrados aún en VFTModel pero están disponibles para enriquecer los indicadores (especialmente Fase 3-4).

#### `GET /movilidad/analitico/agebs`

AGEBs urbanas INEGI — 11,787 registros. GeoJSON con MultiPolygon.

| Param | Tipo | Ejemplo | Nota |
|-------|------|---------|------|
| `entidad` | string | `09` (CDMX), `15` (EdoMex) | Clave 2 dígitos |
| `municipio_alcaldia` | string | `Cuauhtémoc` | Búsqueda parcial (ILIKE) |
| `limit` | int | `500` (default) | Paginación obligatoria |
| `offset` | int | `0` | |

**Properties:** población total, viviendas habitadas, PEA, área km², densidad poblacional.

**Uso potencial para VFT:** ponderación de cobertura por densidad poblacional, análisis de equidad territorial.

#### `GET /movilidad/analitico/afluencia-linea`

Afluencia mensual por línea — 1,197 registros. JSON.

| Param | Tipo | Ejemplo | Nota |
|-------|------|---------|------|
| `sistema` | string | `METRO`, `MB`, `CBB`, `TL`, `TROLE` | |
| `linea_id` | int | `5` | Ref: public.lineas.id |
| `anio` | int | `2024` | |
| `mes_num` | int | `3` (Marzo) | 1-12 |

**Uso potencial para VFT:** Ponderar importancia de aristas por flujo real, validar indicadores de intermediación (Fase 3).

#### `GET /movilidad/analitico/afluencia-estacion`

Afluencia mensual por estación Metro — 38,219 registros. JSON.

| Param | Tipo | Ejemplo | Nota |
|-------|------|---------|------|
| `linea_id` | int | `1` | |
| `num_comercial` | string | `1`, `A`, `L12` | |
| `estacion_id` | int | `100` | |
| `nombre_estacion` | string | `Pantitlán` | ILIKE (parcial) |
| `anio` | int | `2024` | |
| `mes_num` | int | `6` | |

**Uso potencial para VFT:** Validar Fuerza Capilar contra flujo real, calibrar costos de boarding en impedancia.

---

### 3. CRUD descriptivo — `/movilidad/:sistema/`

Endpoints de lectura/escritura para datos operativos. Útiles para consultas puntuales, no para ingesta masiva.

| Ruta | GET | Nota |
|------|-----|------|
| `/movilidad/METRO/linea` | Lista de líneas con metadata | |
| `/movilidad/METRO/estacion` | Lista de estaciones con metadata | |
| `/movilidad/METRO/descripcion-linea` | Datos históricos de líneas | |
| `/movilidad/METRO/descripcion-estacion` | Datos históricos de estaciones | |

Reemplazar `METRO` por cualquier sistema válido o `TODOS`.

---

## Datos disponibles en la BD (para referencia de volumen)

| Tabla (esquema) | Registros | Nota |
|-----------------|-----------|------|
| estacions (public) | 22,878 | Todos los sistemas |
| lineas (public) | 317 | |
| agebs (plutarco) | 11,787 | 6 estados macrometrópoli |
| calles (plutarco) | 175,540 | Marco Geoestadístico INEGI |
| uso_suelo (plutarco) | 6,879 | |
| curvas_nivel (plutarco) | 2,661 | |
| afluencia_linea (plutarco) | 1,197 | 5 sistemas, mensual |
| afluencia_estacion (plutarco) | 38,219 | Solo Metro, 2010-2026 |
| catalogo_homologacion (plutarco) | 151 | Mapeo CSV→linea_id |

---

## Notas técnicas para consumo automatizado

- **Sin autenticación**: todos los endpoints son públicos.
- **Sin rate limiting**: no hay throttling. Puedes hacer peticiones concurrentes sin restricción.
- **CORS abierto**: `Access-Control-Allow-Origin: *`.
- **Timeout recomendado**: 15s para endpoints ligeros, 30s para polígonos/AGEBs.
- **Paginación en AGEBs**: default 500, máximo recomendado 1000. Iterar con `offset`.
- **Normalización de texto**: la API acepta con o sin acentos/ñ (normalización NFC interna).
- **Filtros combinables**: todos los query params son opcionales y se aplican como AND lógico.
- **Respuestas**:
  - `200`: datos encontrados
  - `404`: filtro válido sin resultados
  - `503`: extensión Plutarco no activada en el entorno (ejecutar `make plutarco-setup` en Apimetro)
- **Fallback en VFTModel**: si Apimetro no responde, `client.py` cae a `map.geojson` local.

---

## Sistemas de transporte y sus claves

| Clave API | Nombre completo |
|-----------|-----------------|
| `METRO` | Sistema de Transporte Colectivo Metro |
| `MB` | Metrobús |
| `CBB` | Cablebús |
| `RTP` | Red de Transporte de Pasajeros |
| `TROLE` | Trolebús |
| `TL` | Tren Ligero |
| `MEXIBUS` | Mexibús (Estado de México) |
| `MEXICABLE` | Mexicable (teleférico EdoMex) |
| `INTERURBANO` | Tren Interurbano México-Toluca |
| `CC` | Corredor Concesionado |
| `TODOS` | Todos los sistemas (solo en CRUD) |

---

## Oportunidades de optimización para VFTModel

1. **Filtrar por sistema en la ingesta**: en vez de descargar TODO con `geojsonEstacion` y `geojsonLinea` sin filtros, usar `?sistema=METRO&sistema=MB` para redes específicas (reduce payload).
2. **Usar `existe=true`** en líneas para excluir trazos discontinuados del grafo.
3. **Usar `sentido=1`** para evitar duplicar aristas (ida + regreso) cuando solo se necesita topología.
4. **Enriquecer con afluencia**: `afluencia-estacion` permite ponderar nodos por flujo real mensual.
5. **AGEBs para equidad**: cruzar cobertura espacial con densidad poblacional de AGEBs.
6. **CETRAMs como hubs**: filtrar `es_cetram=true` para identificar nodos multimodales directamente.

---

*Generado: 2026-07-04. Fuente: repositorio Apimetro (branch DEV, commit 3559475).*
