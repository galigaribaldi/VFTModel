# Modelo VFT — Documentación Técnica

**Motor analítico geoespacial y topológico para la evaluación de redes de transporte urbano en la Ciudad de México.**
Desarrollado como componente analítico de la tesis TAICMAM.

---

## ¿Qué es el Modelo VFT?

El **Modelo VFT (Vanishing Fig-Tree)** procesa, valida y analiza matemáticamente grafos de transporte urbano masivo. Recibe geometrías vectoriales desde el backend [apimetro](https://github.com/galigaribaldi/apimetro), construye un grafo dirigido ponderado con NetworkX y calcula indicadores topológicos sobre él.

El nombre obedece a una dualidad conceptual: la metáfora de la higuera (Sylvia Plath) como árbol de decisiones críticas de la red, y el punto de fuga (*vanishing point*) como convergencia analítica de variables independientes en una perspectiva unificada.

---

## Arquitectura en 3 Capas

```
FastAPI (src/api/)  →  Dominio (src/core/)  →  Infraestructura (src/infrastructure/)
```

**Capa 1 — Adquisición y Procesamiento Geométrico**
Consume las geometrías crudas (GeoJSON / MultiLineString) desde apimetro vía clientes httpx asincrónicos. Valida y normaliza el payload con esquemas Pydantic estrictos antes de pasarlo al dominio.

**Capa 2 — Modelado Topológico y Dinámico**
Construye el grafo dirigido $G = (V, E)$ con NetworkX. Aplica *snapping* con KDTree para resolver el float mismatch de coordenadas e inyecta la **impedancia temporal** por arista: tiempo de recorrido castigado por fricción vial y costo de abordaje.

**Capa 3 — Evaluación y Salida**
Corre los algoritmos de indicadores sobre el grafo y serializa los resultados como FeatureCollections GeoJSON a través de los endpoints GeoLayers, listos para consumo directo en QGIS o Transport-gis-zmvm-mjg.

---

## Indicadores Topológicos

El modelo evalúa la red en 4 fases progresivas. Las Fases 1 y 2 son prerequisito de las Fases 3 y 4.

| # | Indicador | Fórmula | Fase | Estado | Endpoint |
|---|---|---|---|---|---|
| 1 | Nivel de Cobertura ($C$) | $C = A_{cubierta} / A_{total}$ | 1 | ✅ Implementado | `/geolayers/coverage` |
| 2 | Fuerza Capilar ($k_{in}$) | $C_i = \sum A_{ij} \cdot w_{ij}$ | 1 | ✅ Implementado | `/geolayers/capillary` |
| 3 | Detour Factor ($DI$) | $DI = d_{red} / d_{recta}$ | 1 | ✅ Implementado | `/geolayers/detour` |
| 4 | Fricción Vial ($CF$) | $CF = 1 + \alpha \cdot \beta_{CDMX}$ | 2 | ✅ Implementado | _(peso en grafo)_ |
| 5 | Penalización Transferencia ($W$) | $W = T_{caminata} + T_{espera}$ | 2 | ✅ Parcial (estática) | _(arista peatonal)_ |
| 6 | Tiempo Promedio ($T$) | $T = \frac{1}{N(N-1)} \sum t(i,j)$ | 3 | ⬜ Pendiente | — |
| 7 | Intermediación ($B$) | $B(v) = \sum \sigma_{st}(v) / \sigma_{st}$ | 3 | ⬜ Pendiente | — |
| 8 | Robustez ($\Delta E$) | $\Delta E = (E_0 - E_k) / E_0$ | 4 | ⬜ Pendiente | — |

---

## Navegación

- **[Construcción del Grafo](NOTES/graph_builder)** — KDTree, snapping, modos de construcción, phantom edges
- **[Modelo de Impedancia](NOTES/impedance)** — fricción vial, velocidades, boarding cost
- **[Detour Factor](NOTES/detaur_factor)** — orquestador, muestreo O-D, fórmula
- **[Issues Abiertos](NOTES/issues)** — bugs conocidos y pendientes técnicos
