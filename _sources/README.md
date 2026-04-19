# Vanishing Fig-Tree Model (VFT Model) / Modelo del Punto de Higuera (MPH)

> Motor analítico geoespacial y topológico para la evaluación de redes de transporte anillares y alimentadoras en la Ciudad de México. Desarrollado como parte de la tesis **TAICMAM**.

## 📖 Sobre el Proyecto

El **Modelo VFT (Modelo del Punto de Higuera)** es una arquitectura de software diseñada para procesar, validar y analizar matemáticamente grafos de transporte urbano masivo. 

El nombre obedece a una dualidad conceptual:
* **La Higuera (The Fig Tree):** Inspirado en la metáfora literaria de Sylvia Plath, el grafo de transporte representa un árbol de decisiones críticas. Si la red capilar no se optimiza temporal y espacialmente, las opciones convergen en la saturación sistémica.
* **El Punto de Fuga (The Vanishing Point):** Arquitectónicamente, el sistema actúa como el punto donde múltiples variables independientes (coordenadas 2D, fricción vial, capacidades) convergen en una perspectiva analítica unificada.

## 🏗️ Arquitectura del Sistema

El proyecto utiliza una adaptación de la **Arquitectura Hexagonal Pragmática**, optimizada para flujos de Data Science y Sistemas de Información Geográfica (SIG).

* **Adaptadores de Entrada (API):** Construidos con `FastAPI`, reciben peticiones asíncronas de servicios externos.
* **Dominio Matemático (Core):** Utiliza `GeoPandas`, `NetworkX` y `Momepy` para transformar geometrías vectoriales (`GeoJSON`, `MultiLineString`) en topologías ruteables evaluando métricas como la Fuerza Nodal y el Grado Capilar.
* **Adaptadores de Salida (Infraestructura):** Clientes asíncronos (`httpx`) para consumo de APIs en Go y futuros conectores para bases de datos relacionales espaciales.

## 📂 Estructura del Repositorio

```text
VFTModel/
├── src/
│   ├── api/            # Endpoints de FastAPI y esquemas de Pydantic
│   ├── core/           # Motor matemático, algoritmos de grafos y logs
│   └── infrastructure/ # Clientes externos (Go API) y persistencia
├── notebooks/          # Entornos interactivos de validación
├── requirements.txt    # Dependencias del proyecto
└── README.md
```