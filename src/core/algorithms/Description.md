# Patrón de Diseño: Indicadores Topológicos VFT

Este documento define la estructura estándar para todos los indicadores del Modelo VFT. El objetivo es garantizar la **eficiencia de memoria**, la **separación de responsabilidades** y la **dualidad de consumo** (Jupyter vs Web).

<hr/>

## 1. Arquitectura de Tres Capas

Cada indicador reside en su propia carpeta dentro de `topologicalIndicators/` y se divide en tres archivos con responsabilidades estrictas:

| Capa | Archivo | Responsabilidad | Estado |
|:---|:---|:---|:---|
| **Orquestador** | `orchestrator.py` | Punto de entrada único. Recibe y gestiona la referencia al grafo. Ensambla la respuesta final. | **Con Estado** (guarda el grafo) |
| **Motor** | `engine.py` | Cálculos matemáticos puros: ruteo Dijkstra, distancias, métricas de red. | **Sin Estado** (funciones puras) |
| **Geometría** | `geometry.py` | Convierte paths de nodos a GeoJSON. Formato para visualización web. | **Sin Estado** (funciones puras) |

### Estructura de carpetas

```
topologicalIndicators/
├── detaurFactor/            ← Referencia de implementación completa
│   ├── __init__.py
│   ├── engine.py
│   ├── geometry.py
│   └── orchestator.py
├── capillar_strength.py     ← Implementación legacy (pre-patrón, monolítica)
└── spatial_coverate.py      ← Implementación legacy (pre-patrón, monolítica)
```

> Los archivos `capillar_strength.py` y `spatial_coverate.py` son implementaciones anteriores al patrón de tres capas. No tienen que ser migradas de forma urgente, pero los indicadores nuevos (P3, P4, ΔE) deben seguir el patrón de carpeta con tres archivos.

<hr/>

## 2. Principios de Oro

1. **Inyección por Referencia:** El grafo (`nx.DiGraph`) solo se carga una vez en memoria. El Orquestador lo recibe como parámetro y lo pasa por referencia a Engine y Geometry. **Nunca se copia el grafo.**
2. **Funciones Puras en Engine:** Las funciones del motor no modifican el grafo original. Solo leen atributos de nodos y aristas.
3. **Dualidad de Salida:** El Orquestador expone métodos que devuelven `pandas.DataFrame` (análisis en Jupyter) y `dict/JSON` (API web). Misma lógica, dos formatos.
4. **`weight='weight'` como contrato:** Todos los algoritmos de ruteo y centralidad usan el atributo `weight` del grafo, que contiene el tiempo de viaje en minutos con fricción vial ya aplicada. Nunca usar `weight='length'` u otros atributos de distancia para el ruteo.

<hr/>

## 3. Flujo de Datos

```
Usuario / API
     │
     ▼
Orquestador (con estado, recibe G)
     ├──▶  Engine (funciones puras)   →  métricas, paths, distancias
     └──▶  Geometry (funciones puras) →  GeoJSON, coordenadas
     │
     ▼
DataFrame  o  JSON
```

<hr/>

## 4. Indicadores Implementados

### 4.1 Detour Factor — `detaurFactor/`

**¿Qué mide?** Qué tan tortuosa es la mejor ruta temporal que el sistema le ofrece al usuario.

```
DF = distancia_total_recorrida_m / distancia_euclidiana_m
```

- Routing con `weight='weight'` (Dijkstra temporal) → selecciona la ruta más rápida.
- Medición en metros usando `distancia_segmento_m` de cada arista → captura el trazo real de calle (crítico para CC/RTP).
- Incluye primera y última milla (caminata al/desde la estación más cercana).

Ver documentación completa: `notebooks/NOTES/detaur_factor.md`

---

### 4.2 Fuerza Capilar — `capillar_strength.py`

**¿Qué mide?** La importancia nodal de cada estación en la red, distinguiendo entre hubs de transporte masivo y alimentadores de superficie.

- Usa degree centrality ponderada con spatial grid hashing (celdas de 0.001°).
- Filtra nodos de trazo interno que no son estaciones funcionales.
- Clasifica nodos según jerarquía de transporte (masivo vs. superficie).

> Implementación pre-patrón. Funcional pero sin separación Engine/Geometry/Orchestrator.

---

### 4.3 Cobertura Espacial — `spatial_coverate.py`

**¿Qué mide?** El porcentaje del área de cada alcaldía o municipio cubierto por buffers de 800 m alrededor de las estaciones.

- Análisis puramente espacial con GeoPandas y Shapely.
- No depende del grafo NetworkX; opera directamente sobre coordenadas de estaciones y polígonos territoriales.

> Implementación pre-patrón. Funcional pero sin separación Engine/Geometry/Orchestrator.

<hr/>

## 5. Indicadores Pendientes (Referencia de Diseño)

Los siguientes indicadores deben implementarse siguiendo el patrón de tres capas.

### 5.1 Tiempo de Viaje Promedio (T) — Fase 3

```
T = (1 / N(N-1)) × Σ t(i,j)    →    nx.average_shortest_path_length(G, weight='weight')
```

- Prerequisito: extraer la componente fuertemente conexa (SCC) del DiGraph.
- Unidad de resultado: minutos.
- Valor esperado de referencia para CDMX: T ≈ 85 min.
- Advertencia de escala: con 11k+ nodos, el cálculo exhaustivo es O(N × Dijkstra). Evaluar muestreo O-D o `asyncio.to_thread`.

### 5.2 Centralidad de Intermediación (B) — Fase 3

```
B(v) = Σ (σ_st(v) / σ_st)    →    nx.betweenness_centrality(G, weight='weight', normalized=True)
```

- Prerequisito: misma SCC que T (compartir extracción en un módulo `networkEfficiency/`).
- Validación: Pantitlán y Pino Suárez deben aparecer con B ≈ 0.40.

### 5.3 Robustez y Vulnerabilidad (ΔE) — Fase 4

- Depende de B y T validados.
- Algoritmo: remover el nodo con mayor B → recalcular T → medir caída porcentual.
- Hipótesis: red actual ~35% de caída; con Anillo Periférico ~12%.