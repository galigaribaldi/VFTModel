# Patrón de Diseño: Indicadores VFT

Este documento define la estructura estándar para todos los indicadores del Modelo VFT. El objetivo es garantizar la **eficiencia de memoria**, la **separación de responsabilidades** y la **dualidad de consumo** (Jupyter vs Web).

<hr/>

## 1. Organización por Dominio Analítico

Los indicadores se agrupan por el **tipo de análisis** que realizan, no por la fase del roadmap. La fase se indica con el header `@phase:` dentro de cada archivo.

```
algorithms/
├── topological/                 # Usan grafo NetworkX (DiGraph)
│   ├── capillar_strength.py     # @phase: 1 — Fuerza Capilar (k_in)
│   ├── detaurFactor/            # @phase: 1 — Detour Factor (DI)
│   │   ├── engine.py
│   │   ├── geometry.py
│   │   └── orchestator.py
│   ├── scc_analysis/            # @phase: 3 — Verificación SCC (gate)
│   │   ├── engine.py
│   │   ├── diagnostics.py
│   │   └── orchestator.py
│   ├── average_travel_time/     # @phase: 3 — Tiempo Promedio (T) [pendiente]
│   └── betweenness_centrality/  # @phase: 3 — Intermediación (B) [pendiente]
├── spatial/                     # Usan geometría (GeoPandas/Shapely), sin grafo
│   └── spatial_coverage.py      # @phase: 1 — Cobertura Espacial (C)
└── demand/                      # Usan datos de Apimetro Plutarco (afluencia, AGEBs)
    └── (vacío — futuro: Node Score, equidad territorial)
```

### Dominios

| Dominio | Fuente de datos | Indicadores |
|:--------|:----------------|:------------|
| **topological/** | Grafo NetworkX (`nx.DiGraph`) con pesos de impedancia | k_in, DI, SCC, T, B, ΔE |
| **spatial/** | Coordenadas + polígonos territoriales (GeoPandas) | Cobertura (C) |
| **demand/** | Datos externos de Apimetro Plutarco (afluencia, AGEBs, censos) | Node Score, equidad territorial |

### Header `@phase:`

Cada archivo indica su fase en el docstring:

```python
"""
@author: Hernán Galileo Cabrera Garibaldi
@description: ...
@phase: 3
@route: src/core/algorithms/topological/scc_analysis/engine.py
"""
```

Fases del modelo: 1 (Arquitectura Base), 2 (Ponderación Dinámica), 3 (Evolución Global), 4 (Pruebas de Estrés).

<hr/>

## 2. Arquitectura de Tres Capas

Cada indicador complejo reside en su propia carpeta y se divide en archivos con responsabilidades estrictas:

| Capa | Archivo | Responsabilidad | Estado |
|:---|:---|:---|:---|
| **Orquestador** | `orchestator.py` | Punto de entrada único. Recibe y gestiona la referencia al grafo. Ensambla la respuesta final. | **Con Estado** (guarda el grafo) |
| **Motor** | `engine.py` | Cálculos matemáticos puros: ruteo Dijkstra, distancias, métricas de red. | **Sin Estado** (funciones puras) |
| **Geometría / Diagnósticos** | `geometry.py` o `diagnostics.py` | Convierte resultados crudos a formato consumible (GeoJSON, reportes). | **Sin Estado** (funciones puras) |

> Los archivos `capillar_strength.py` y `spatial_coverage.py` son implementaciones anteriores al patrón de tres capas. No requieren migración urgente, pero los indicadores nuevos deben seguir el patrón de carpeta con tres archivos.

<hr/>

## 3. Principios de Oro

1. **Inyección por Referencia:** El grafo (`nx.DiGraph`) solo se carga una vez en memoria. El Orquestador lo recibe como parámetro y lo pasa por referencia a Engine y Geometry. **Nunca se copia el grafo** (excepto la componente gigante en SCC, que es una copia intencionada para aislamiento de Fase 3).
2. **Funciones Puras en Engine:** Las funciones del motor no modifican el grafo original. Solo leen atributos de nodos y aristas.
3. **Dualidad de Salida:** El Orquestador expone métodos que devuelven `pandas.DataFrame` (análisis en Jupyter) y `dict/JSON` (API web). Misma lógica, dos formatos.
4. **`weight='weight'` como contrato:** Todos los algoritmos de ruteo y centralidad usan el atributo `weight` del grafo, que contiene el tiempo de viaje en minutos con fricción vial ya aplicada. Nunca usar `weight='length'` u otros atributos de distancia para el ruteo.

<hr/>

## 4. Flujo de Datos

```
Usuario / API
     │
     ▼
Orquestador (con estado, recibe G)
     ├──▶  Engine (funciones puras)        →  métricas, paths, distancias
     └──▶  Geometry / Diagnostics (puras)  →  GeoJSON, coordenadas, reportes
     │
     ▼
DataFrame  o  JSON
```

<hr/>

## 5. Indicadores Implementados

### 5.1 Detour Factor — `topological/detaurFactor/` — Fase 1

**¿Qué mide?** Qué tan tortuosa es la mejor ruta temporal que el sistema le ofrece al usuario.

```
DF = distancia_total_recorrida_m / distancia_euclidiana_m
```

- Routing con `weight='weight'` (Dijkstra temporal) → selecciona la ruta más rápida.
- Medición en metros usando `distancia_segmento_m` de cada arista → captura el trazo real de calle (crítico para CC/RTP).
- Incluye primera y última milla (caminata al/desde la estación más cercana).

Ver documentación completa: `notebooks/NOTES/detaur_factor.md`

---

### 5.2 Fuerza Capilar — `topological/capillar_strength.py` — Fase 1

**¿Qué mide?** La importancia nodal de cada estación en la red, distinguiendo entre hubs de transporte masivo y alimentadores de superficie.

- Usa degree centrality ponderada con spatial grid hashing (celdas de 0.001°).
- Filtra nodos de trazo interno que no son estaciones funcionales.
- Clasifica nodos según jerarquía de transporte (masivo vs. superficie).

> Implementación pre-patrón. Funcional pero sin separación Engine/Geometry/Orchestrator.

---

### 5.3 Cobertura Espacial — `spatial/spatial_coverage.py` — Fase 1

**¿Qué mide?** El porcentaje del área de cada alcaldía o municipio cubierto por buffers de 800 m alrededor de las estaciones.

- Análisis puramente espacial con GeoPandas y Shapely.
- No depende del grafo NetworkX; opera directamente sobre coordenadas de estaciones y polígonos territoriales.

> Implementación pre-patrón. Funcional pero sin separación Engine/Geometry/Orchestrator.

---

### 5.4 Análisis SCC — `topological/scc_analysis/` — Fase 3

**¿Qué mide?** La conectividad fuerte del grafo. Gate para Fase 3.

- Algoritmo de Tarjan (`nx.strongly_connected_components`).
- Extrae la componente gigante como subgrafo independiente para T y B.
- Resultado verificado: 95.02% de nodos en componente gigante → apto para Fase 3.

<hr/>

## 6. Indicadores Pendientes (Referencia de Diseño)

Los siguientes indicadores deben implementarse siguiendo el patrón de tres capas.

### 6.1 Tiempo de Viaje Promedio (T) — `topological/average_travel_time/` — Fase 3

```
T = (1 / N(N-1)) × Σ t(i,j)    →    nx.average_shortest_path_length(G, weight='weight')
```

- Prerequisito: componente gigante extraída por SCC (ya disponible en `SCC_CACHE`).
- Unidad de resultado: minutos.
- Valor esperado de referencia para CDMX: T ≈ 85 min.
- Advertencia de escala: con 10,561 nodos, el cálculo exhaustivo es O(N × Dijkstra). Usar `asyncio.to_thread`.

### 6.2 Centralidad de Intermediación (B) — `topological/betweenness_centrality/` — Fase 3

```
B(v) = Σ (σ_st(v) / σ_st)    →    nx.betweenness_centrality(G, weight='weight', normalized=True)
```

- Prerequisito: misma componente gigante que T.
- Validación: Pantitlán y Pino Suárez deben aparecer con B ≈ 0.40.

### 6.3 Robustez y Vulnerabilidad (ΔE) — `topological/robustness/` — Fase 4

- Depende de B y T validados.
- Algoritmo: remover el nodo con mayor B → recalcular T → medir caída porcentual.
- Hipótesis: red actual ~35% de caída; con Anillo Periférico ~12%.

### 6.4 Node Score (Tipo B) — `demand/node_score/` — Bloqueado

- Depende de datos de afluencia de Apimetro Plutarco (MV1+MV2).
- Combina grado topológico con flujo real de pasajeros.
- Issue #12 en GitHub.
