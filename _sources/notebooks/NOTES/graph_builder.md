# Notas del Módulo: `graph_builder.py`

**¿Qué hace este archivo en resumen?**
Es el "arquitecto" de nuestra red. Toma todas las estaciones y líneas de transporte sueltas y las teje para formar un grafo (una red conectada). Su trabajo más importante es simular la realidad: conectar estaciones cercanas para que el usuario pueda transbordar caminando, cobrándole el tiempo de caminata más el tiempo de espera en el andén.

<hr/>
## 1. Los Diccionarios Base (Los Acuerdos de la Realidad)

Antes de conectar cosas, la clase `VFTGraphBuilder` define las reglas del juego usando diccionarios:

### Umbrales de Caminata (`STATISTICAL_THRESHOLDS`)

Define qué tan lejos estamos dispuestos a obligar al usuario a caminar para cambiar de transporte.

- **MIN (15m):** Literalmente la misma estación o el mismo paradero.
- **Q1 (85m):** Un transbordo rápido, cruzando la calle.
- **Q2_MEDIAN (180m):** El transbordo promedio en un CETRAM de la CDMX.
- **Q3 (420m):** El límite del dolor; lo máximo que alguien caminaría por necesidad.

### Tiempos de Espera (`FALLBACK_FRECUENCIA`)

Si un sistema no nos dice cada cuánto pasa, usamos estos promedios (en minutos) para calcular cuánto tiempo va a perder el usuario esperando en el andén durante un transbordo.

```python
FALLBACK_FRECUENCIA = {
    "METRO": 3.0, "MB": 5.0, "TL": 10.0, "TROLE": 8.0,
    "RTP": 15.0, "SUB": 12.0, "CBB": 1.0, "CC": 15.0, "MEXIBÚS": 6.0
}
```

<hr/>
## 2. El Director de Orquesta: `build_graph()`

Es la función principal. Lo que hace es:

1. Construye las vías normales (trenes y camiones avanzando de estación a estación).
2. Si le decimos que opere en modo `"REALISTIC_INTEGRATION"`, manda llamar a la función de "snapping" para crear los caminos peatonales invisibles entre estaciones cercanas.

<hr/>
## 3. La Magia de los Transbordos: `_apply_pedestrian_snapping()`

Aquí es donde ocurre la integración intermodal. El algoritmo agarra un compás, se para en una estación y busca si hay otras estaciones dentro del radio de tolerancia (ej. 85 metros). Si encuentra una, crea un puente peatonal de ida y vuelta.

### El Costo del Transbordo (Caminata + Espera)

Cuando creamos esa conexión, le cobramos al usuario dos cosas en el `weight` (el peso que lee el algoritmo de rutas):

1. Lo que tarda en caminar.
2. Lo que tarda esperando su nuevo transporte (que en promedio es la mitad de la frecuencia total del sistema).

```python
# 1. Calculamos la caminata. Usamos la velocidad normativa de 5000m/60min (83.33 m/min)
tiempo_caminata_min = distancia_m / (5000.0 / 60.0)

# 2. Calculamos cuánto va a esperar (Boarding Cost). Frecuencia / 2
wait_v = self.FALLBACK_FRECUENCIA.get(sistema_v, 10.0) / 2.0

# 3. Sumamos ambas cosas en el peso matemático final
peso_total = tiempo_caminata_min + wait_v
```

<hr/>
## 🚨 Justificación Técnica de la Velocidad Peatonal

Para calcular el `tiempo_caminata_min`, en el código hacemos una conversión equivalente a caminar a **5 km/h (1.38 m/s)**.

**¿De dónde sale este número para no inventarlo?** Se toma el límite superior del estándar operativo nacional basado en el [*Manual de Calles: Diseño Vial para Ciudades Mexicanas* (SEDATU, 2019)](https://www.gob.mx/cms/uploads/attachment/file/509173/Manual_de_calles_2019.pdf). En la página 178 del documento oficial, se establece la siguiente norma para el diseño de infraestructura:

> "Generales: Los tiempos de cruce de peatones en semáforo debe ser suficiente para cruzar el ancho de la calle. Se recomienda considerar una velocidad de marcha de **1.2 m/s** para determinar la longitud de la fase peatonal."

Como nuestro modelo asume un trayecto de transferencia (población económicamente activa en movimiento continuo dentro de un nodo de transbordo sin esperar semáforos), adoptamos el límite superior de **1.38 m/s (5 km/h)**, logrando un balance entre la norma urbana y los cálculos de isócronas globales.

<hr/>
## ⚠️ Limitante de Datos: Cobertura Incompleta de Cablebús (CBB)

El backend Go (`apimetro_db`) reporta únicamente **19 estaciones de Cablebús** en la tabla `lineas` (verificado 2026-04-18). El sistema real opera con más estaciones distribuidas en las Líneas 1 y 2.

- **Impacto en C (Cobertura):** el buffer de 800 m subestima el área cubierta por CBB.
- **Impacto en Fuerza Capilar:** los nodos masivos de CBB reciben menos conexiones de superficie de las reales.
- **Acción requerida:** verificar tabla `lineas` en `apimetro_db` filtrando `sistema = 'CBB'` y completar el registro de estaciones faltantes. Hasta entonces, los indicadores de CBB deben interpretarse como estimaciones conservadoras.

<hr/>
## 📐 Fundamento del Coeficiente de Fricción Vial (CF) — alpha por derecho de vía

El `FrictionCalculator` en `src/core/models/impedance.py` usa la siguiente tabla de `alpha` para calcular `CF = 1 + (alpha × BETA_SATURACION_CDMX)`:

| Derecho de Vía | alpha | Sistemas | Justificación |
|---|---|---|---|
| `exclusivo` | 0.0 | Metro, Sub, Interurbano, CBB | Infraestructura segregada; el tráfico vehicular no afecta la velocidad comercial |
| `confinado` | 0.2 | Metrobús, Trole elevado | Carril propio pero con interferencias en intersecciones |
| `compartido` | 0.5 | Trolebús convencional | Comparte vialidad pero tiene preferencia operativa |
| `mixto` | 1.0 | RTP, CC, Pumabus | Opera en tráfico abierto; absorbe la congestión total |

**Fuente del esquema de clasificación:** *Manual de Calles: Diseño Vial para Ciudades Mexicanas* (SEDATU, 2019). El manual establece la jerarquía funcional de los derechos de vía como criterio de diseño para infraestructura de transporte público (Capítulo 4, sección de carriles exclusivos y confinados).

**Fuente del BETA_SATURACION:** TomTom Traffic Index 2023 para Ciudad de México — `Average congestion level = 0.759` (76% de incremento en tiempo de viaje sobre flujo libre en hora pico).

**Nota metodológica:** Los `FALLBACK_VELOCIDAD` en `VFTImpedanceModel` representan **velocidad de flujo libre** (sin congestión). El CF aplica la penalización. Esta separación evita el double-counting que ocurriría si el fallback ya incorporara congestión y el CF la volviera a aplicar.

<hr/>
## 🔬 Observación de Semántica de Datos: Banqueta vs. Carril (Apimetro ↔ VFTModel)

### El problema

Los sistemas de transporte de superficie (MB, CC, RTP, TROLE) almacenan las coordenadas
de sus paradas en la **banqueta o cordón**, mientras que la geometría del trazo
(`ramals.geom` en Apimetro) sigue el **eje del carril central**. La diferencia típica
es de **5–15 metros**.

La migración `UPDATE.sql` (2026-04-17) usó `ST_LineLocatePoint(trazo, parada)` para
proyectar cada parada al punto más cercano del eje de carril y luego cortó el trazo
con `ST_LineSubstring`. Esto segmentó correctamente la geometría, pero los **endpoints
de cada sublínea quedaron sobre el carril**, no sobre la coordenada GPS original
de la parada.

```
Parada registrada (banqueta): (-99.18234, 19.42811)
Endpoint sublínea (carril):   (-99.18227, 19.42809)  ← ≈ 8 m de diferencia
```

Resultado medido (endpoint match por sistema, corrida 2026-04-17):

| Sistema | Match exacto (0 m) | Match < 1 m | Match < 10 m |
|---|---:|---:|---:|
| MEXICABLE | 100% | 100% | 100% |
| METRO | 0% | 97.3% | ~100% |
| TL | 0% | 100% | 100% |
| CBB | 0% | 71.7% | ~74% |
| MB | 0% | 7.9% | ~25% |
| CC | 0% | 3.1% | ~30% |
| RTP | 0% | 4.6% | ~34% |
| TROLE | 0% | 29.1% | ~45% |

### Por qué no se corrigió en el backend

Mover el endpoint al punto proyectado sobre el carril introduciría una inconsistencia
semántica: el nodo del grafo existiría en el asfalto, no en la posición GPS real de
la parada. La coordenada original de cada estación es el dato canónico; el trazo es
la geometría auxiliar.

### La solución adoptada: KDTree con 50 m de tolerancia (`SNAP_TOLERANCE_DEG`)

`_build_base_network` construye un `scipy.spatial.KDTree` sobre las coordenadas de
las estaciones registradas en Fase 1. Para cada punto del trazo, consulta la estación
más cercana dentro de `SNAP_TOLERANCE_DEG` (≈ 50 m). Esto resuelve:

- **Trampa 1 (float mismatch / desfase banqueta-carril):** 50 m absorbe el desfase
  de 5–15 m de los sistemas de superficie, y el drift de precisión < 1 m de los
  sistemas de infraestructura dedicada.
- **Trampa 2 (sublíneas a nivel de cuadra):** sistemas como MB o CC tienen sublíneas
  de ~50–200 m que no van de estación a estación. La caminata continua detecta
  waypoints a lo largo de toda la ruta sin importar la granularidad del GeoJSON.

El nodo del grafo siempre es la **coordenada GPS original de la estación** (registrada
en Fase 1 desde `geojsonEstacion`). Nunca se crean nodos huérfanos ni nodos en el
punto medio del carril.