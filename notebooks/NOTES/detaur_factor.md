# Notas del Módulo: Detour Factor

**¿Qué hace este indicador en resumen?**
Mide qué tan tortuosa es la mejor ruta que el sistema de transporte le ofrece al usuario. Compara la distancia real de red que debe recorrer un pasajero (siguiendo las líneas disponibles) contra la línea recta imaginaria entre su origen y destino. Un DF cercano a 1.0 indica una red muy directa; valores altos indican que la infraestructura obliga a dar rodeos significativos.

<hr/>

## 1. Definición Formal

```
DF = distancia_red_metros / distancia_euclidiana_metros
```

Donde:
- **distancia_euclidiana_metros**: Haversine directo entre el punto de origen y el punto de destino (línea recta sobre la superficie terrestre).
- **distancia_red_metros**: Suma de los trazos reales de cada segmento en la ruta óptima calculada por Dijkstra con `weight='weight'` (minutos).

> **Nota de diseño:** El DF clásico (Parthasarathi 2011, Boeing 2017) opera puramente en metros y mide la geometría de la infraestructura. La implementación VFT extiende esta definición: el routing usa `weight='weight'` (tiempo con fricción vial), de modo que la ruta analizada no es la más corta en distancia sino la más rápida en tiempo real. El DF resultante responde a la pregunta: **¿qué tan tortuosa es la mejor ruta que el sistema le puede ofrecer al usuario?**

<hr/>

## 2. Arquitectura del Módulo (Tres Capas)

El Detour Factor fue el primer indicador en implementar la arquitectura estándar VFT de tres capas. Sirve como referencia de diseño para todos los indicadores posteriores.

```
detaurFactor/
├── __init__.py        → Exporta DetourFactorOrchestrator (fachada pública)
├── engine.py          → Funciones puras: routing Dijkstra, cálculo de distancias
├── geometry.py        → Formato GeoJSON para visualización web
└── orchestator.py     → Orquestador con estado: recibe el grafo, ensambla respuestas
```

### Responsabilidades por capa

| Capa | Archivo | Qué hace |
|---|---|---|
| **Orquestador** | `orchestator.py` | Punto de entrada. Gestiona el grafo. Expone `calculate_custom_route()` y `calculate_sample_routes()`. |
| **Motor** | `engine.py` | `get_closest_node_and_walking_distance()` y `calculate_network_distance()`. Sin estado, sin efectos secundarios. |
| **Geometría** | `geometry.py` | `format_network_geometry()` y `format_imaginary_geometry()`. Convierte paths de nodos a GeoJSON. |

<hr/>

## 3. `engine.py` — Funciones Puras

### 3.1 `get_closest_node_and_walking_distance()`

Resuelve el problema de la **primera y última milla**: el usuario no siempre parte desde una estación exacta de la red.

Maneja dos escenarios:

```python
# Escenario A: El punto ya es un nodo conocido de la red (su nombre como string)
"Pantitlán"  →  distancia_caminata = 0 m

# Escenario B: El usuario provee coordenadas arbitrarias (tupla lon, lat)
(-99.1332, 19.4284)  →  busca el nodo más cercano + distancia de caminata
```

La búsqueda en el Escenario B itera sobre todos los nodos del grafo calculando haversines. Para redes grandes esto es O(N). Si el rendimiento se vuelve crítico, reemplazar con un KDTree sobre las coordenadas de los nodos.

### 3.2 `calculate_network_distance()`

Suma la distancia real del trazo entre estaciones consecutivas del path devuelto por Dijkstra.

```python
for i in range(len(path) - 1):
    segmento = G[path[i]][path[i+1]].get('distancia_segmento_m')
    # Fallback defensivo si la arista no tiene el atributo
    if segmento is None:
        segmento = haversine(nodo_i, nodo_i+1)
    dist_total += segmento
```

**Por qué no usar haversine directo entre nodos:**
`distancia_segmento_m` fue acumulada por el `graph_builder` vértice a vértice sobre el `MultiLineString` completo de cada ruta. Para sistemas de superficie (CC, RTP), que siguen la vialidad urbana con curvas y esquinas, la diferencia entre el trazo real y la cuerda directa entre paradas puede ser del 30-40%. Usar haversine subestimaría la distancia de red y haría que el DF aparente sea artificialmente bajo (red más "eficiente" de lo que es en realidad).

**Ejemplo concreto (Corredor Concesionado):**
```
Parada A → Parada B, ruta de superficie:

  distancia_segmento_m (trazo real de calle): 1,850 m
  haversine(A, B) directo:                    1,100 m
  Diferencia:                                   750 m  (40% de subestimación)

  Con 8 paradas en la ruta completa, el error acumulado
  puede distorsionar el DF hasta en un 44%.
```

<hr/>

## 4. `orchestator.py` — Orquestador

### 4.1 `calculate_custom_route(origen, destino)`

Flujo de cálculo:

```
1. get_closest_node_and_walking_distance(origen)  →  nodo_u, dist_caminata_o
2. get_closest_node_and_walking_distance(destino) →  nodo_v, dist_caminata_d
3. haversine(origen, destino)                     →  distancia_euclidiana
4. nx.shortest_path(G, u, v, weight='weight')     →  path (ruta más rápida en tiempo)
5. calculate_network_distance(G, path)            →  distancia_red_m
6. dist_total = dist_caminata_o + dist_red_m + dist_caminata_d
7. DF = dist_total / distancia_euclidiana
```

Atributos en la respuesta:

| Campo | Descripción |
|---|---|
| `Factor_Desviacion` | DF calculado (distancia total / haversine O-D) |
| `Distancia_Recta_km` | Haversine entre origen y destino |
| `Distancia_Red_km` | Distancia total recorrida (caminata + red + caminata) |
| `Saltos_Topologicos` | Número de aristas en el path |
| `Sistemas_Involucrados` | Lista ordenada de sistemas usados en la ruta |
| `Ruta_Estaciones` | Nombres de estaciones en el path |
| `Consideraciones_Reales` | Desglose de caminata primera y última milla |

### 4.2 `calculate_sample_routes(sample_size, seed)`

Muestreo estadístico masivo para obtener el DF promedio de la red.

- Filtra pares O-D con distancia euclidiana < 100 m (distancias triviales no aportan información).
- Usa `nx.descendants()` para garantizar que solo se muestreen pares con ruta existente.
- Acepta `seed` para reproducibilidad de experimentos.

> **Advertencia:** El bucle interno no tiene límite de intentos máximos. Si la fracción de pares alcanzables es muy baja (grafo muy desconectado), puede quedar en loop indefinido. Agregar un guard de `max_intentos = sample_size * 10` como mejora futura.

<hr/>

## 5. Decisiones de Diseño Explícitas

### Routing temporal vs. distancia geométrica

El path se calcula con `weight='weight'` (minutos con fricción vial), no con distancia en metros. Esto significa que Dijkstra elige la ruta más rápida para el pasajero real, no la más corta en línea recta de red.

Consecuencia: el DF mide la tortuosidad de la mejor opción temporal disponible, no de cualquier camino. Es una métrica más exigente y más honesta con la experiencia del usuario.

### Primera y última milla incluida

La distancia de caminata desde el origen hasta la primera estación, y desde la última estación hasta el destino, se suma al numerador del DF. Esto refleja la experiencia completa del viaje, no solo el tramo en transporte público.

### Fricción vial en el routing, no en la medición

La fricción (Cf) está horneada en el `weight` de cada arista desde la construcción del grafo. El routing es consciente de ella (prefiere Metro sobre CC cuando corresponde). Sin embargo, la medición final del DF es siempre en **metros**, no en minutos penalizados. La fricción influye en qué ruta se elige, pero el DF reporta la geometría de esa ruta.

<hr/>

## 6. Bugs Corregidos

| Fecha | Bug | Descripción | Fix |
|---|---|---|---|
| 2026-04-26 | `weight='length'` | `orchestator.py` usaba un atributo inexistente. NetworkX caía en routing sin peso (mínimo número de saltos), ignorando impedancia. | Corregido a `weight='weight'`. |
| 2026-04-26 | `calculate_network_distance` con haversine nodo-nodo | Subestimaba la distancia de red hasta un 40% en rutas CC/RTP al usar cuerdas directas entre paradas en lugar del trazo acumulado. | Corregido a leer `distancia_segmento_m` de la arista. |

<hr/>

## 7. Issues Abiertos

1. **Guard de intentos en `calculate_sample_routes`:** El bucle `while len(resultados) < sample_size` no tiene máximo de iteraciones. Agregar `max_intentos = sample_size * 10` con excepción informativa.
2. **Búsqueda O(N) en `get_closest_node_and_walking_distance`:** Para coordenadas arbitrarias, itera sobre todos los nodos. Reemplazar con KDTree sobre coordenadas de nodos si el rendimiento se vuelve crítico.
3. **DF simétrico no garantizado:** En un DiGraph, el DF de A→B puede diferir del de B→A. El muestreo estadístico promedia esto implícitamente, pero `calculate_custom_route` no lo advierte.
