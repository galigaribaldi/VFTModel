# Notas del Módulo: `impedance.py`

**¿Qué hace este archivo en resumen?**
Es el "tasador de tiempo" de la red. Una vez que `graph_builder.py` construyó el grafo con sus nodos y aristas, este módulo recorre cada segmento y le inyecta un **peso temporal en minutos** basado en tres factores reales: la distancia física del tramo, la velocidad comercial del sistema, y el nivel de interferencia del tráfico urbano sobre esa vía. Es la implementación directa de la **Ecuación VFT**.

<hr/>

## 1. `FrictionCalculator` — El Coeficiente de Fricción Vial (Cf)

Este módulo auxiliar traduce el tipo de derecho de vía de una línea en un penalizador matemático. La idea central: no es lo mismo correr por un túnel del Metro (sin semáforos, sin tráfico) que circular en un camión por Insurgentes entre autos particulares.

### La Constante de Saturación de la CDMX

```python
BETA_SATURACION_CDMX = 0.759
```

Este valor viene del **TomTom Traffic Index** para Ciudad de México, que mide el nivel promedio de congestión vial. Un beta de 0.759 significa que la ciudad opera al ~76% de saturación en condiciones promedio.

### De Derecho de Vía a Coeficiente

El método `get_friction()` usa un `alpha` que escala el impacto de la saturación:

```python
alpha_map = {
    "exclusivo": 0.0,   # Metro, Suburbano: aislado del tráfico
    "confinado": 0.2,   # Metrobús, Trolé elevado: carril propio pero visible
    "compartido": 0.5,  # Trolebús convencional: comparte vía pero tiene prioridad
    "mixto": 1.0        # RTP, CC: completamente inmerso en el tráfico urbano
}
cf = 1.0 + (alpha * BETA_SATURACION_CDMX)
```

**Resultado numérico por tipo de vía:**

| Derecho de Vía | Alpha | Cf calculado | Significado |
|---|---|---|---|
| `exclusivo` | 0.0 | **1.000** | Sin penalización (flujo ideal) |
| `confinado` | 0.2 | **1.152** | +15% de tiempo por tráfico |
| `compartido` | 0.5 | **1.380** | +38% de tiempo por tráfico |
| `mixto` | 1.0 | **1.759** | +76% de tiempo por tráfico |

El valor por defecto si no se conoce el derecho de vía es `"mixto"` (el peor caso).

<hr/>

## 2. `VFTImpedanceModel` — El Motor de Impedancia

### 2.1 Tablas de Fallback

Si un segmento del GeoJSON no reporta velocidad o frecuencia, el modelo usa valores calibrados por sistema. Estas son **velocidades comerciales ajustadas** (no de diseño):

```python
FALLBACK_VELOCIDAD = {
    "SUB": 65.0,        # Tren Suburbano
    "METRO": 36.0,      # STC Metro
    "MB": 16.3,         # Metrobús
    "TL": 22.0,         # Tren Ligero
    "TROLE": 18.0,      # Trolebús
    "RTP": 14.0,        # Red de Transporte de Pasajeros
    "CC": 11.0,         # Corredores Concesionados
    "CBB": 20.0,        # Cablebús
    "MEXICABLE": 20.0,
    "MEXIBÚS": 16.3,
    "PUMABUS": 11.0
    # "INTERURBANO": 160.0  ← ⚠️ Revisar: parece velocidad de diseño, no comercial
}
```

```python
FALLBACK_FRECUENCIA = {
    "METRO": 3.0,   # minutos entre trenes
    "MB": 5.0,
    "CBB": 10.0,    # ⚠️ Difiere de graph_builder.py donde CBB=1.0
    "CC": 15.0,
    "RTP": 15.0,
    ...
}
```

> **Nota de inconsistencia:** `CBB` tiene frecuencia `10.0` min aquí pero `1.0` min en `graph_builder.py`. Requiere definición canónica.

<hr/>

### 2.2 `haversine()` — La Distancia Real del Segmento

```python
@staticmethod
def haversine(lon1, lat1, lon2, lat2) -> float:
    R = 6371000  # Radio de la Tierra en metros
    phi_1 = math.radians(lat1)
    phi_2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi_1)*math.cos(phi_2)*math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
```

**¿Por qué Haversine y no distancia euclidiana?** Porque las coordenadas son geográficas (lon/lat en grados). Una resta directa de coordenadas daría distancias en "grados", no en metros, y además ignoraría la curvatura de la Tierra. Haversine traza la línea recta más corta sobre la superficie esférica terrestre (ortodrómica), dando metros reales con precisión suficiente para distancias urbanas (error < 0.3% dentro de la CDMX).

**Firma importante:** recibe `(lon, lat, lon, lat)` — primero longitud, luego latitud. Los nodos del grafo están almacenados como `(lon, lat)`, así que la llamada siempre es `haversine(u[0], u[1], v[0], v[1])`.

<hr/>

### 2.3 `apply_impedance()` — La Inyección sobre el Grafo

Este método itera sobre todas las aristas del grafo `DiGraph` y aplica la Ecuación VFT en 6 pasos:

```python
for u, v, data in self.G.edges(data=True):

    # PASO 0: Proteger transbordos peatonales (ya calculados por graph_builder)
    if data.get("tipo") == "transfer":
        continue

    # PASO 1: Distancia geodésica del segmento
    distancia_m = haversine(u[0], u[1], v[0], v[1])

    # PASO 2: Velocidad comercial (del GeoJSON o fallback por sistema)
    v_kmh = data.get("velocidad_promedio_kmh") or FALLBACK_VELOCIDAD.get(sistema, 15.0)

    # PASO 3: Conversión a m/min para compatibilidad de unidades
    v_m_min = v_kmh * (1000.0 / 60.0)

    # PASO 4: Coeficiente de fricción según derecho de vía
    cf = FrictionCalculator.get_friction(data.get("derecho_de_via", "mixto"))

    # PASO 5: Tiempo de traslado puro (la Ecuación VFT)
    travel_time_min = (distancia_m / v_m_min) * cf

    # PASO 6: Boarding cost (frecuencia / 2, solo para análisis; no suma al weight)
    boarding_cost_min = frecuencia / 2.0
```

**Atributos que inyecta en cada arista:**

| Atributo | Unidad | Descripción |
|---|---|---|
| `distancia_segmento_m` | metros | Distancia Haversine del segmento |
| `travel_time_min` | minutos | Tiempo de traslado con fricción |
| `boarding_cost_min` | minutos | Costo de abordaje (F/2) — informativo |
| `coeficiente_friccion` | adimensional | Cf aplicado |
| `weight` | minutos | **= travel_time_min** (lo que usan los algoritmos de rutas) |

> **Decisión de diseño clave:** el `weight` solo incluye `travel_time_min`, **no** `boarding_cost_min`. El boarding cost se registra como atributo informativo pero no penaliza el camino en los segmentos normales. La penalización por espera ocurre únicamente en las aristas de transbordo peatonal, donde sí se suma al weight (`tiempo_caminata + wait`).

<hr/>

## 3. El Flujo Completo en Contexto

```
GeoJSON  →  VFTGraphBuilder  →  [Grafo base + transbordos peatonales]
                                           ↓
                              VFTImpedanceModel.apply_impedance()
                                           ↓
              Cada arista normal recibe:  weight = (D / V) × Cf
              Cada arista transfer tiene: weight = t_caminata + (F_destino / 2)
                                           ↓
                              Grafo listo para Dijkstra / análisis topológico
```

<hr/>

## 4. Issues Abiertos sobre este Módulo

1. **Velocidad INTERURBANO (160 km/h):** El fallback de 160 km/h corresponde a velocidad de diseño del tren, no comercial. La velocidad operativa real es ~70 km/h. Requiere corrección.
2. **Inconsistencia CBB:** `FALLBACK_FRECUENCIA["CBB"]` = 10.0 aquí vs 1.0 en `graph_builder.py`. Definir el valor canónico.
3. **Boarding cost no suma al weight:** Esta es una decisión de diseño consciente. Verificar si el análisis de rutas debe o no incluirlo para los segmentos normales (actualmente solo aplica en transbordos).
4. **Fuente de los coeficientes alpha:** Pendiente citar la tabla exacta del Manual de Calles SEDATU 2019 que fundamenta los valores `alpha = {0.0, 0.2, 0.5, 1.0}`.
