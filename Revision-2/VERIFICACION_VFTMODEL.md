# Verificación VFTModel — Revisión-2 Dr. Jairo
**Fecha de creación:** 2026-10-01  
**Estado:** Documento de trabajo para agente VFTModel  
**Generado desde:** análisis de `Nota-Cap-3-29-09-2026.md` y `Nota-Cap-5-29-09-2026.md`

---

## Documentos de referencia base (corrida original)

Antes de iniciar cualquier verificación, consultar:

| Documento | Ruta | Contenido clave |
|---|---|---|
| `ANALISIS_PRELIMINAR.md` | `Anexos/Notas_Correciones/Suposiciones/` | Valores exactos de la corrida baseline (T=108.92, Tacubaya B(v)=0.2179, DI=0.713, bandas Garibelt); tabla top-5 B(v) por escenario; distribución DI por categoría |
| `SUPOSICIONES_ANALITICAS.md` | `Anexos/Notas_Correciones/Suposiciones/` | 7 suposiciones S1–S7 derivadas computacionalmente; tareas de verificación pendientes por agente |

Los valores de `ANALISIS_PRELIMINAR.md` son la **fuente canónica** de la primera corrida. Si VFTModel produce resultados distintos en una nueva corrida, documentar la diferencia antes de actualizar la tesis.

---

## Sección A — Verificaciones críticas 🔴 (afectan validez de resultados)

---

### VFT-CHECK-1 — Parámetro α de Cablebús
**Indicador afectado:** Coeficiente de Fricción Vial ($CF$)  
**Observación Dr. Jairo (C6 Cap.3 + C6 Cap.5):**  
> "El Cap. 3 clasifica Cablebús como confinado con CF = 1.0. El Cuadro 5.9 le asigna CF = 1.152 (α = 0.2). Unifique la clasificación."

**Cómo se detectó:** Comparación directa entre §3.3.6.1 (Cap.3) y Cuadro 5.9/tabla `tab:aristas-por-sistema` (Cap.5). La tabla en `5-2-Grafo-Topologico.tex` línea 77 muestra `Cablebús → Confinado → 1.152`.

**Diagnóstico:** El Cablebús es un teleférico aéreo sin contacto con vialidades terrestres. Físicamente equivale al Metro (infraestructura segregada total). Asignarle α = 0.2 es un error de parametrización en la configuración de sistemas de VFTModel.

**Archivos afectados en la tesis:**
- `5-Analisis-Red-Actual/5-2-Grafo-Topologico.tex` — línea 77 (tabla CF por sistema)
- `5-Analisis-Red-Actual/5-4-Fase2/5-4-1-CoeficienteFriccion.tex` — línea 38 (tabla CF por categoría)
- `3-Conceptos-Indicadores/3-3-Indicadores/3-3-6-Friccion-Vial.tex` — §3.3.6.1

**Acción en VFTModel:**
```python
# Verificar en catálogo de sistemas (systems_config.py o equivalente):
# ¿Cablebús tiene alpha = 0.0 o alpha = 0.2?
# Si alpha = 0.2 → cambiar a alpha = 0.0 (categoría "exclusivo", igual que Metro)
# CF resultante: CF = 1 + 0.0 * 0.759 = 1.000

print(systems_config["Cablebús"]["alpha"])   # debe ser 0.0
print(systems_config["Cablebús"]["categoria"])  # debe ser "exclusivo"
```

**Impacto si se corrige:** Las aristas del Cablebús (30 aristas) pasarán de CF=1.152 a CF=1.000, reduciendo su tiempo de viaje. El impacto global en T es pequeño (30/25,197 = 0.1% de aristas) pero corrige un error conceptual.

---

### VFT-CHECK-2 — Normalización de B(v) y complejidad de Brandes
**Indicador afectado:** Centralidad de Intermediación ($B(v)$)  
**Observación Dr. Jairo (M12 Cap.5 + M12 Cap.3):**  
> "La ecuación (3.10) carece del factor de normalización 1/((N-1)(N-2)) para grafo dirigido, y los valores reportados (0.2179) están normalizados; agréguelo. La complejidad de Brandes en grafos ponderados es O(VE + V² log V), no O(VE)."

**Cómo se detectó:** Inconsistencia entre la ecuación sin normalizar en `3-3-7-Centralidad.tex` (ecuación 3.10) y los valores [0,1] reportados en Cuadro 5.10. Con N=10,561 nodos, un valor sin normalizar de Tacubaya sería del orden de millones, no 0.2179.

**Diagnóstico probable:** El código SÍ normaliza (los valores son correctos). La ecuación en el texto es incompleta. Es error de redacción, NO de cálculo. La corrección de complejidad (O(VE) → O(VE + V²logV)) también es solo de texto.

**Archivos afectados en la tesis:**
- `3-Conceptos-Indicadores/3-3-Indicadores/3-3-7-Centralidad.tex` — ecuación 3.10
- `5-Analisis-Red-Actual/5-5-Fase3/5-5-2-Centralidad.tex` — líneas 30-32

**Acción en VFTModel:**
```python
# Confirmar que se usa normalized=True en el cálculo de betweenness:
import networkx as nx
bv = nx.betweenness_centrality(G, normalized=True, weight='travel_time')
# O verificar si se normaliza manualmente:
# bv[v] = raw_bv[v] / ((N-1) * (N-2))  ← para grafo dirigido

# Verificar: max(bv.values()) debe ser ~0.2179 (Tacubaya)
print(f"Max B(v): {max(bv.values()):.4f}")
print(f"Tacubaya: {bv.get('Tacubaya', 'no encontrado'):.4f}")
```

---

### VFT-CHECK-3 — Discrepancia B(v) figura vs tabla
**Indicador afectado:** Centralidad de Intermediación ($B(v)$)  
**Observación Dr. Jairo (C8 Cap.5):**  
> "Los valores de la figura no coinciden con el Cuadro 5.10 (Tacubaya 0.3216 vs. 0.2179; Zapata 0.2565 vs. 0.1283; Chabacano 0.2602 no aparece en el cuadro). Aclare si la figura agrega por hub o suma sistemas."

**Cómo se detectó:** Comparación visual entre `Figures/Cap5/` (figura insertada en §5.5.2) y `tab:bv-top10` en `5-5-2-Centralidad.tex` línea 57.

**Diagnóstico probable:** La figura proviene de una corrida anterior (posiblemente de la corrida de Fase 2 o de un notebook exploratorio). Durante el proceso de integración del capítulo, se insertó la figura incorrecta. Los valores del Cuadro 5.10 (0.2179 para Tacubaya) corresponden a la corrida canónica 2026-09-02 del `ANALISIS_PRELIMINAR.md`.

**Archivos afectados en la tesis:**
- `5-Analisis-Red-Actual/5-5-Fase3/5-5-2-Centralidad.tex` — figura `fig:bv-ranking` y su referencia
- `Figures/Cap5/` — identificar cuál archivo de imagen tiene los valores incorrectos

**Acción en VFTModel:**
```python
# Regenerar la figura de ranking B(v) usando los datos de la corrida 2026-09-02:
# Fuente: tableau/exports/data/garibelt/escenario-base/b_ranking_baseline.csv
# Verificar que el top-10 coincide con el Cuadro 5.10:
# Tacubaya=0.2179, Mixcoac=0.173, Hidalgo=0.159, Balderas=0.143, Lázaro Cárdenas=0.138

import pandas as pd
df = pd.read_csv("tableau/exports/data/garibelt/escenario-base/b_ranking_baseline.csv")
print(df.head(10)[['nodo', 'betweenness_norm']])
# Exportar figura desde estos datos (no desde una corrida diferente)
```

---

### VFT-CHECK-4 — DI=0.97 geométricamente imposible
**Indicador afectado:** Factor de Desviación Indirecta ($DI$)  
**Observación Dr. Jairo (M7 Cap.5):**  
> "El DI = 0.97 es geométricamente imposible (DI ≥ 1 por definición, §3.3.3.2). La causa probable está en `graph_builder.py`: `dist_acumulada` se reinicia en cada vértice dentro del radio de tolerancia de una estación, y cada arista pierde hasta ~100 m frente al haversine. La media de 1.545 sería entonces una cota inferior."

**Cómo se detectó:** §3.3.3.2 de la tesis declara explícitamente DI ≥ 1. El Cuadro 5.7 reporta mínimo 0.97. Los datos de `ANALISIS_PRELIMINAR.md` confirman: DI mínimo = 0.97 en la corrida baseline (DI máximo = 4.32, media = 1.545).

**Archivos afectados en la tesis:**
- `5-Analisis-Red-Actual/5-3-Fase1/5-3-4-DI.tex` — Cuadro 5.7, análisis de distribución
- `3-Conceptos-Indicadores/3-3-Indicadores/3-3-3-DI.tex` — §3.3.3.2
- `3-Conceptos-Indicadores/3-3-Indicadores/3-3-10-Clasificacion-Garibelt.tex` — normalización con techo DI=2.5

**Acción en VFTModel:**
```python
# Buscar en graph_builder.py cómo se calcula dist_acumulada:
# ¿Se reinicia al pasar por una estación dentro del radio de tolerancia?
# ¿Se usa haversine o dist_acumulada para el denominador de DI?

# DI = d_red(origen, destino) / d_haversine(origen, destino)
# Si d_red < d_haversine → DI < 1 → imposible
# → el cálculo de d_red está subestimado

# Verificar también:
# ¿Cuántos pares de la muestra (200 O-D) tienen DI < 1.0?
df = pd.read_csv("tableau/exports/data/garibelt/escenario-base/df_distribucion_baseline.csv")
print(f"Pares con DI < 1.0: {(df['factor_desviacion'] < 1.0).sum()}")
print(f"DI mínimo: {df['factor_desviacion'].min():.3f}")
print(f"DI media: {df['factor_desviacion'].mean():.3f}")
```

---

### VFT-CHECK-5 — Velocidad libre de Metrobús y Tabla 5.3
**Indicador afectado:** Coeficiente de Fricción Vial ($CF$) — tabla de validación  
**Observación Dr. Jairo (C4 Cap.5 + C4 Cap.3):**  
> "Metrobús (exclusivo, CF = 1.000) debería dar 16.3 km/h, no 14.1. Además, Cap. 3 declara 22 km/h para Metrobús. Use el mismo parámetro o justifique la diferencia."

**Cómo se detectó:** Con CF=1.000, velocidad post-fricción = velocidad libre. Si la tabla muestra 14.1 km/h para Metrobús → VFTModel usa 14.1 km/h como velocidad libre del Metrobús. Esto contradice los 22 km/h declarados en Cap.3 §3.1.1.8.

**Diagnóstico:** Hay tres valores en conflicto: 14.1 km/h (implícito en Tabla 5.3), 16.3 km/h (mencionado por Dr. Jairo), 22 km/h (declarado en Cap.3). El valor real del código es la fuente de verdad.

**Archivos afectados en la tesis:**
- `5-Analisis-Red-Actual/5-2-Grafo-Topologico.tex` — Tabla 5.3 (regenerar)
- `3-Conceptos-Indicadores/3-1-Definiciones/3-1-1-Glosario-Base.tex` — §3.1.1.8 (corredor anillar)

**Acción en VFTModel:**
```python
# Verificar velocidad libre (free_flow_speed) por sistema en el código:
for sistema, config in systems_config.items():
    print(f"{sistema}: {config.get('free_flow_speed', 'N/A')} km/h, alpha={config.get('alpha', 'N/A')}")

# Con la velocidad libre real, recalcular la Tabla 5.3:
# v_post_friccion = v_libre / CF
# Para Metrobús (CF=1.000): v_post = v_libre / 1.000 = v_libre exacta
# Para RTP (CF=1.759): v_post = v_libre / 1.759
```

---

### VFT-CHECK-6 — Manejo de pares desconectados en ΔE y remoción de macro-hub
**Indicador afectado:** Robustez Geométrica ($\Delta E$)  
**Observación Dr. Jairo (M13 Cap.5 + M11 Cap.3):**  
> "M13: (1) Remover un solo nodo subestima el efecto en CETRAMs co-localizados; remover el macro-hub completo (radio 100 m). (2) Reportar cuántos pares quedan desconectados. (3) El orden de ΔE no sigue al de B(v) — ese hallazgo es valioso y debe destacarse. M11: La eficiencia E = 1/T difiere del estándar Latora-Marchiori; con exclusión de pares desconectados, T_f puede bajar artificialmente."

**Cómo se detectó (M13):** Cuadro 5.11 muestra ΔE de Tacubaya = 2.58%, pero Tacubaya tiene múltiples nodos co-localizados por ser CETRAM (intersección de varias líneas del Metro). Remover solo un nodo subestima el impacto real del fallo del hub completo.

**Cómo se detectó (M11):** `5-5-3-Vulnerabilidad.tex` línea 21 y `3-3-8-Robustez.tex` línea 43 definen explícitamente E₀ = 1/T. La definición estándar (Latora y Marchiori, 2001) es E = promedio(1/d_ij) sobre todos los pares del grafo.

**Archivos afectados en la tesis:**
- `5-Analisis-Red-Actual/5-5-Fase3/5-5-3-Vulnerabilidad.tex` — §5.5.3 completo
- `3-Conceptos-Indicadores/3-3-Indicadores/3-3-8-Robustez.tex` — §3.3.8.2 fórmula

**Acción en VFTModel:**
```python
# PARTE 1: Verificar manejo de pares desconectados
# ¿Cómo se calcula T_f después de remover un nodo?
# Opción A (correcta): usar infinity para pares desconectados → T_f sube → ΔE > 0
# Opción B (problemática): excluir pares desconectados → T_f puede bajar → ΔE negativo

# Verificar en el código de vulnerabilidad:
# tiempos_fallidos = dijkstra_all_pairs(G_sin_nodo_v)
# ¿Se incluyen los inf? → print(sum(1 for t in tiempos_fallidos.values() if t == float('inf')))

# PARTE 2: Contar pares desconectados al remover Tacubaya
# Este número debe reportarse en la tesis (Dr. Jairo lo pide explícitamente)
G_sin_tacubaya = G.copy()
G_sin_tacubaya.remove_node("Tacubaya")  # o el ID del nodo
pares_desconectados = sum(1 for u in G_sin_tacubaya.nodes()
                          for v in G_sin_tacubaya.nodes()
                          if u != v and not nx.has_path(G_sin_tacubaya, u, v))
print(f"Pares desconectados al remover Tacubaya: {pares_desconectados}")

# PARTE 3: Remoción de macro-hub completo
# Identificar todos los nodos de Tacubaya en radio 100m
# y removerlos simultáneamente (igual criterio que FC_H)
nodos_tacubaya = [n for n in G.nodes() if es_cercano(n, coords_tacubaya, radio=100)]
print(f"Nodos en macro-hub Tacubaya (r=100m): {len(nodos_tacubaya)}")
```

---

### VFT-CHECK-7 — Dominio territorial: 125 vs 76 municipios ZMVM
**Indicador afectado:** Accesibilidad / Cobertura Espacial ($C$) y $FC$  
**Observación Dr. Jairo (M3+M4 Cap.5):**  
> "La ZMVM (SEDATU-CONAPO-INEGI) comprende 16 alcaldías, 59 municipios EdoMex y 1 de Hidalgo = 76 demarcaciones. 125 es el total de municipios del Estado de México. Calimaya, Capulhuac y Donato Guerra no pertenecen a la ZMVM. Restrinja el dominio."

**Cómo se detectó:** §5.3.2 declara "125 municipios del EdoMex + 16 alcaldías = 141 demarcaciones". La ZMVM oficial tiene 59+16+1 = 76.

**Archivos afectados en la tesis:**
- `5-Analisis-Red-Actual/5-3-Fase1/5-3-2-Cobertura.tex` — §5.3.2 y Cuadro 5.6
- `tableau/exports/data/garibelt/escenario-base/cobertura_alcaldias_baseline.csv` — 141 filas

**Acción en VFTModel:**
```python
# Verificar el filtro de municipios en el cálculo de cobertura:
# ¿Cuántas demarcaciones tiene el dataset?
df_cob = pd.read_csv("tableau/exports/data/garibelt/escenario-base/cobertura_alcaldias_baseline.csv")
print(f"Demarcaciones en dataset: {len(df_cob)}")
print(f"Municipios EdoMex: {len(df_cob[df_cob['estado'] == 'Estado de México'])}")

# Municipios fuera de la ZMVM oficial (deben filtrarse):
# Buscar si existen en el dataset: Calimaya, Capulhuac, Donato Guerra
municipios_excluir = ['Calimaya', 'Capulhuac', 'Donato Guerra']
print(df_cob[df_cob['municipio'].isin(municipios_excluir)])

# Si el filtro ZMVM no está aplicado → añadir filtro por lista oficial SEDATU-CONAPO-INEGI
# La lista oficial de 76 municipios ZMVM está en el Decreto CONAPO 2018
```

---

### VFT-CHECK-8 — Tren Suburbano subrepresentado
**Indicador afectado:** Cobertura, $FC$, $DI$, $T$, $B(v)$ (todos los indicadores afectados por el grafo base)  
**Observación Dr. Jairo (C3 Cap.5):**  
> "Tres aristas para una línea de siete estaciones indica subrepresentación. Agreguelo a la nota ‡."

**Cómo se detectó:** Tabla en `5-2-Grafo-Topologico.tex` línea 79: `Tren Suburbano → 3 aristas`. Una línea de 7 estaciones debería tener al menos 6 aristas (segmentos entre estaciones consecutivas).

**Archivos afectados en la tesis:**
- `5-Analisis-Red-Actual/5-2-Grafo-Topologico.tex` — nota al pie de Tabla 5.2

**Acción en VFTModel:**
```python
# Verificar en el grafo construido cuántas aristas pertenecen al Tren Suburbano:
aristas_suburbano = [(u,v,d) for u,v,d in G.edges(data=True)
                     if d.get('sistema') == 'Tren Suburbano']
print(f"Aristas Tren Suburbano en el grafo: {len(aristas_suburbano)}")
# Esperado: ≥6 aristas (7 estaciones - 1)
# Si hay solo 3 → problema en el GTFS o en graph_builder al procesar la línea

# Verificar en Apímetro/GTFS:
# ¿Cuántas trips tiene el Tren Suburbano en stop_times.txt?
# ¿Cuántos stops únicos en la línea?
```

---

## Sección B — Verificaciones de consistencia interna 🟠

---

### VFT-CHECK-9 — β=0.759 TomTom: valor correcto, documentación incompleta
**Indicador afectado:** Coeficiente de Fricción Vial ($CF$)  
**Observación Dr. Jairo (M10 Cap.5):**  
> "El Manual de Calles SEDATU no establece los valores de α. Declárelos como supuestos del autor. Para β=0.759 indique año y métrica exacta del TomTom."

**Análisis de la fuente:** El sitio TomTom Traffic Index para Ciudad de México reporta **nivel de congestión = 75.9%** (datos 2024, publicados 2025). La derivación es: β = 75.9 / 100 = 0.759. El valor es correcto y verificable.

**No requiere cambio en VFTModel.** Solo corrección de redacción en la tesis:
1. Explicar explícitamente que β = TomTom Congestion Level / 100 = 75.9% / 100
2. Cambiar `\citep{tomtom2024}` para especificar: "TomTom Traffic Index, Ciudad de México, datos 2024"
3. Declarar los α = {0.0, 0.2, 0.5, 1.0} como "supuestos del autor basados en categorías de SEDATU (2019)"

**Archivos afectados en la tesis:**
- `5-Analisis-Red-Actual/5-4-Fase2/5-4-1-CoeficienteFriccion.tex` — líneas 18-46
- `referencias.bib` — entrada `tomtom2024`

---

### VFT-CHECK-10 — % distribución modal: 12% no cuadra
**Indicador afectado:** Descripción del grafo (sin indicador; afecta credibilidad general)  
**Observación Dr. Jairo (C2 Cap.5):**  
> "Metro + Metrobús + Tren Ligero + Cablebús + Suburbano suman 1,405 aristas = 5.6% de 25,197 (7.2% si se agregan Mexibús y Mexicable). Indique la base del 12%."

**Cálculo desde la tabla del texto** (`5-2-Grafo-Topologico.tex` líneas 72-79):

| Grupo | Sistemas | Aristas | % de 25,197 |
|---|---|---|---|
| Exclusivo | Metro(528)+MB(792)+TL(52)+Sub(3) | 1,375 | **5.46%** |
| Confinado | Mexibús(391)+Cablebús(30)+Mexicable(17) | 438 | **1.74%** |
| Exclusivo+Confinado | todos los anteriores | 1,813 | **7.19%** |

El 12% declarado en §5.2 no corresponde a ninguna combinación posible. Además, el texto pone a Mexibús y Mexicable en "vía compartida o mixta" pero la tabla los clasifica como "Confinado" — inconsistencia interna.

**No requiere cambio en VFTModel.** Corregir el porcentaje en el texto usando los datos de la tabla existente.

**Archivos afectados:**
- `5-Analisis-Red-Actual/5-2-Grafo-Topologico.tex` — líneas 44-48

---

### VFT-CHECK-11 — Espectro MJG: sección vacía con datos disponibles
**Indicador afectado:** Clasificación Garibelt / Espectro MJG (todos los indicadores)  
**Observación Dr. Jairo (C9 Cap.5):**  
> "La sección del Espectro está vacía: solo contiene encabezados. Presente una tabla con valor bruto, regla de agregación, valor normalizado y banda para cada dimensión."

**Los datos YA EXISTEN.** En `ANALISIS_PRELIMINAR.md` (Espectro Garibelt por escenario):

| Dimensión | Valor normalizado baseline | Banda |
|---|---|---|
| Accesibilidad C | 0.055 | Crítico |
| Capilaridad Cᵢ | 0.250 | Débil |
| Eficiencia DI | 0.713 | Aceptable |
| Fluidez T | 0.748 | Aceptable |
| Centralidad B | 0.211 | Crítico |

**No requiere re-corrida de VFTModel.** Los CSVs de referencia están en:
`tableau/exports/data/garibelt/escenario-base/garibelt_perfil_baseline.csv`

**Archivos afectados en la tesis:**
- `5-Analisis-Red-Actual/5-6-Espectro-MJG/5-6-2-Espectro.tex` — tabla del Espectro a completar
- Fuente de datos: `garibelt_perfil_baseline.csv`

**Acción:** Leer el CSV y popular la tabla LaTeX con: dimensión, valor bruto, método normalización, valor [0,1], banda asignada. Sin correr VFTModel de nuevo.

---

## Sección C — Datos de contexto de la primera corrida

Para todas las verificaciones anteriores, los valores de referencia de la corrida canónica son:

```
Corrida: 2026-09-02 (componente gigante, 10,561 nodos)
Semilla aleatoria DI: seed=42, n=100 pares O-D

Indicadores baseline:
  T  = 108.92 min (tiempo de viaje promedio)
  DI media = 1.545 | min = 0.97 | max = 4.32
  B(v) Tacubaya = 0.2179 (top-1 de 10,561 nodos)
  Gini B(v) = 0.7891
  C  = 0.055 (accesibilidad, banda Crítico)
  Cᵢ = 0.250 (capilaridad, banda Débil)

Top-5 B(v) baseline:
  #1 Tacubaya     0.2179
  #2 Mixcoac      0.1730
  #3 Hidalgo      0.1590
  #4 Balderas     0.1430
  #5 Lázaro Cárdenas 0.1380

Distribución DI:
  eficiente (DI<1.3): 30.5%
  alto (DI>2.0): 22.5%

Nodos en red: 11,115 | Aristas totales: 45,679
Aristas servicio real: 25,197 | Aristas transbordo: 20,482
```

---

## Orden de ejecución recomendado

1. **VFT-CHECK-1** (Cablebús α) — cambio de parámetro, impacto en CF y T
2. **VFT-CHECK-4** (DI < 1.0) — bug en `dist_acumulada`, investiga `graph_builder.py`
3. **VFT-CHECK-5** (velocidad libre Metrobús) — definir el valor canónico
4. **VFT-CHECK-7** (dominio territorial ZMVM) — filtrar 125→76 municipios
5. **VFT-CHECK-8** (Tren Suburbano) — verificar ingesta GTFS
6. **VFT-CHECK-6** (ΔE y desconexiones) — análisis adicional sobre resultados existentes
7. **VFT-CHECK-2** (B(v) normalización) — confirmar `normalized=True`, solo redacción
8. **VFT-CHECK-3** (figura B(v)) — regenerar figura con datos del CSV canónico
9. **VFT-CHECK-9** (β TomTom) — solo redacción, sin código
10. **VFT-CHECK-10** (12% modal) — solo redacción, sin código
11. **VFT-CHECK-11** (Espectro vacío) — poblar tabla desde CSV existente
