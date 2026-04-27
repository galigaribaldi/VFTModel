# Patrón de Diseño: Indicadores Topológicos VFT

Este documento define la estructura estándar para todos los indicadores del Modelo VFT (Detour Factor, Impedancia, Fuerza Capilar, etc.). El objetivo es garantizar la **eficiencia de memoria**, la **separación de responsabilidades** y la **dualidad de consumo** (Jupyter vs Web).

## 1. Arquitectura de Tres Capas

Cada indicador debe residir en su propia carpeta y separarse en los siguientes archivos:

| Capa               | Archivo           | Responsabilidad                                        | Estado (State)                   |
| :----------------- | :---------------- | :----------------------------------------------------- | :------------------------------- |
| **Orquestador**    | `orchestrator.py` | Punto de entrada único. Maneja la referencia al Grafo. | **Con Estado** (Guarda el Grafo) |
| **Motor (Engine)** | `engine.py`       | Cálculos matemáticos y ruteo (Dijkstra, Haversine).    | **Sin Estado** (Funciones Puras) |
| **Geometría**      | `geometry.py`     | Mapeo de nodos a coordenadas y formato GeoJSON/Web.    | **Sin Estado** (Funciones Puras) |

## 2. Principios de Oro

1. **Inyección por Referencia:** El Grafo (`nx.DiGraph`) solo se carga una vez en memoria. El Orquestador lo recibe y lo "presta" a las capas de Engine y Geometry. **Nunca se copia el grafo.**
2. **Funciones Puras en el Engine:** Las funciones del motor no deben modificar el grafo original. Solo leen atributos.
3. **Dualidad de Salida:** El Orquestador debe proveer métodos para devolver un `pandas.DataFrame` (para análisis científico en Jupyter) y un `JSON/Dict` (para el visualizador web).

## 3. Flujo de Datos
1. El Usuario llama al **Orquestador**.
2. El Orquestador solicita datos crudos al **Engine**.
3. El Orquestador solicita el formato espacial al **Geometry**.
4. El Orquestador ensambla la respuesta final.