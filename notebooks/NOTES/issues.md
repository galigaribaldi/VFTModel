# Issues y Correcciones — VFT Model

## Sesión 2026-04-16 / 2026-04-17

### Correcciones Aplicadas

| # | Archivo | Cambio | Estado |
|---|---|---|---|
| 1 | `src/core/models/impedance.py` | `FALLBACK_VELOCIDAD["INTERURBANO"]`: 160 km/h → **70 km/h** (velocidad comercial real) | ✅ RESUELTO |
| 2 | `src/core/services/graph_builder.py` | `FALLBACK_FRECUENCIA["CBB"]`: 1.0 min → **10.0 min** (alineado con `impedance.py`) | ✅ RESUELTO |
| 3 | `notebooks/01_Analisis_Impedancia_VFT.ipynb` | Separación de `df_edges` (servicio real) vs `df_transfers` (transbordo peatonal). Antes se mezclaban, contaminando el análisis. | ✅ RESUELTO |
| 4 | `apimetro_db` (docker-dev, puerto 5433) | `historico_operacion.velocidad_promedio_kmh` para ramal Interurbano corregida a 70.0 km/h vía UPDATE directo. | ✅ RESUELTO |

---

### Issues Abiertos (pendientes)

#### P1 — Double-counting de fricción en RTP y CC ⚠️ Metodológico
- **Descripción:** Los valores de `FALLBACK_VELOCIDAD['RTP']` (14 km/h) y `FALLBACK_VELOCIDAD['CC']` (11 km/h) ya incorporan condiciones de tráfico moderado. Al aplicarles el $C_f$ adicional (1.76 para mixto), la velocidad efectiva cae a ~8 km/h — posiblemente subestimada.
- **Impacto:** Sobrepenalización del tiempo de viaje en los dos sistemas con mayor cobertura (~74,265 segmentos, 78% del total).
- **Acción recomendada:** Calibrar fallbacks con velocidades de flujo libre (~20 km/h RTP, ~16 km/h CC) y dejar que el $C_f$ introduzca toda la penalización dinámica.
- **Archivo:** `src/core/models/impedance.py` — `FALLBACK_VELOCIDAD`

#### P2 — Cobertura de CBB en GeoJSON ⚠️ Integridad de datos
- **Descripción:** `SistemaTransporte.corredor_baja` (Cablebús) tiene solo **37 segmentos** en el grafo actual, contra 93 de Mexicable. Cablebús opera 3 líneas en CDMX — parece subrepresentado.
- **Acción recomendada:** Verificar que el backend de Apimetro tiene las tres líneas del Cablebús completas en el GeoJSON. Revisar tabla `lineas` en `apimetro_db` filtrando por sistema CBB.
- **Archivo:** Backend Apimetro / `src/infrastructure/go_client/client.py`

#### P3 — Indicador $T$ promedio (Dijkstra) 🔲 Pendiente de cálculo
- **Descripción:** La tesis estima $T \approx 85$ min. La estimación orientativa del notebook 01 (85–100 min) es coherente, pero el valor real requiere Dijkstra sobre pares O-D muestreados.
- **Acción recomendada:** Muestrear ~500–1000 pares O-D sobre nodos de estación (`tipo != 'trazo'`) y ejecutar `nx.single_source_dijkstra(grafo_vft, source, weight='weight')`. Agregar en notebook 01 o crear notebook 03 dedicado.
- **Referencia tesis:** Tabla 3.4, Capítulo 3

#### P4 — Indicador $DI$ para pares O-D de la tesis 🔲 Pendiente de cálculo
- **Descripción:** Los pares Xochimilco→Santa Fe ($DI=1.87$), Perisur→Naucalpan ($DI=2.33$) e Iztapalapa→Tlalnepantla ($DI=2.50$) son valores teóricos de la tesis, no calculados sobre el grafo real.
- **Acción recomendada:** Notebook 03 (`DetourFactorAnalyzer`).
- **Referencia tesis:** Tabla 3.3, Capítulo 3

#### P5 — Fuente de coeficientes alpha ($C_f$) 📖 Documentación
- **Descripción:** Los valores `alpha = {0.0, 0.2, 0.5, 1.0}` para los cuatro tipos de derecho de vía requieren cita exacta del Manual de Calles SEDATU 2019 (tabla y párrafo).
- **Archivo:** `src/core/models/impedance.py` — `FrictionCalculator.alpha_map`; `notebooks/NOTES/impedance.md` — Sección 1

---

### Contexto de corrida (2026-04-16)

- **Grafo:** 102,055 nodos — 115,083 aristas (94,601 servicio + 20,482 transbordos peatonales)
- **Modo:** `REALISTIC_INTEGRATION`, tolerancia Q1 = 85 m
- **Distribución:** 12% masiva estructurada (Metro+MB+TL+CBB+SUB) / 88% superficie (RTP+CC+TROLE+MEXIBÚS+Mexicable)
- **$C_f$ validados:** exclusivo=1.00, confinado=1.152, compartido=1.380, mixto=1.759
- **Velocidades OK:** METRO (36), MB (16.3), TL (22), CBB (20), SUB (65) km/h
- **Velocidades REVISAR:** TROLE (13 post-Cf, −7% del límite inferior), RTP (8), CC (8) — ver P1
