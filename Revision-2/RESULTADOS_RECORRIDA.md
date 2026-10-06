# Resultados Re-corrida VFTModel — Revisión-2
**Fecha de re-corrida:** 2026-10-03  
**Motivación:** Correcciones ACHECK-01 a ACHECK-04 aplicadas en Apimetro (ver `Notas-Revision-Apimetro.md`)  
**Escenarios verificados:** Baseline (:8000) ✅ | MB (:8001) ✅ | METRO (:8002) ✅

---

## 1. Indicadores Garibelt — Comparativa de escenarios

### Datos previos (corrida canónica 2026-09-02, pre-correcciones Apimetro)

> Fuente: `ANALISIS_PRELIMINAR.md` (valores canónicos baseline)

| Dimensión | Valor bruto | Normalizado | Banda |
|-----------|-------------|-------------|-------|
| C — Accesibilidad | 4.4% | 0.055 | Crítico |
| Cᵢ — Capilaridad | 7.0 (mediana grado) | 0.250 | Débil |
| DI — Eficiencia ruta | 1.545 (media) | 0.713 | Aceptable |
| T — Fluidez global | 108.92 min | 0.748 | Aceptable |
| Gini B(v) — Centralidad | 0.7891 | 0.2110 | Crítico |

Red: 11,115 nodos | 45,679 aristas totales  
SCC gigante: 10,561 nodos (95.02%) | Aislados: 554

### Datos nuevos (post-correcciones Apimetro, 2026-10-03)

| Dimensión | Baseline | MB (Anillo MB) | METRO (Anillo METRO) |
|-----------|----------|----------------|----------------------|
| **C — Accesibilidad** | 0.0552 — Crítico | 0.0557 — Crítico | 0.0557 — Crítico |
| **Cᵢ — Capilaridad** | 0.250 — Débil | 0.250 — Débil | 0.250 — Débil |
| **DI — Eficiencia** | 0.7133 — Aceptable | 0.720 — Aceptable | 0.6867 — Aceptable |
| **T — Fluidez** | 0.7507 — **Idóneo** | 0.7947 — **Idóneo** | **0.865 — Idóneo** |
| **Gini B(v)** | 0.7894 — Crítico | 0.7886 — Crítico | 0.7983 — Crítico |

#### Valores brutos nuevos

| Métrica | Baseline | MB | METRO |
|---------|----------|----|-------|
| T (min) | **108.6833** | **104.5003** | **97.8282** |
| T delta vs Baseline | — | −4.18 min | −10.85 min |
| DI mediana | 1.43 | 1.42 | 1.47 |
| DI media | 1.547 | 1.530 | 1.582 |
| DI mínimo | 0.78 ⚠️ | 0.80 ⚠️ | 0.80 ⚠️ |
| Gini B(v) | 0.7894 | 0.7886 | **0.7983** |
| C (%) | 4.4138 | 4.4596 | 4.4596 |
| Nodos | 11,115 | 11,209 | 11,209 |
| Aristas totales | 45,502 | 45,987 | 45,978 |

> **Hallazgo clave:** El escenario METRO produce la mayor reducción de T (−10.85 min vs Baseline, −6.67 min vs MB).  
> El DI mediana sube ligeramente en METRO (1.47 vs 1.42 MB) — el Anillo Metro mejora tiempos pero introduce rutas con mayor rodeo relativo.  
> Gini B(v) es mayor en METRO (0.7983) — la centralidad se concentra más que en Baseline o MB.

#### Cambio de banda: T Baseline

> ⚠️ La corrección de datos Apimetro movió T de 108.92 → 108.68 min.  
> El valor normalizado subió de 0.748 → **0.7507**, cruzando el umbral de banda **Aceptable → Idóneo**.  
> Esto afecta la narrativa del Espectro MJG en la tesis (Cuadro 5.9 / §5.6).

---

## 2. Comparativa de red por escenario

| Métrica | Baseline | MB | METRO |
|---------|----------|----|-------|
| Nodos totales | 11,115 | 11,209 (+94) | 11,209 (+94) |
| Aristas totales | 45,502 | 45,987 (+485) | 45,978 (+476) |
| SCC gigante (nodos) | 10,561 (95.02%) | 10,658 (95.08%) | 10,658 (95.08%) |
| Nodos aislados | 554 | 551 | 551 |

> MB y METRO agregan los mismos 94 nodos nuevos (Anillo Periférico). El gigante crece +97 nodos en ambos escenarios vs Baseline.

### Fragmentación SCC por sistema

| Sistema | Baseline | MB | METRO | Nota |
|---------|----------|----|-------|------|
| METRO | 100.0% | 100.0% | **100.0%** | +94 nodos Anillo integrados |
| PUMABUS | 100.0% | 100.0% | 100.0% | — |
| TL | 100.0% | 100.0% | 100.0% | — |
| TROLE | 99.5% | 99.5% | 99.5% | — |
| MB | 96.0% | **97.5%** | 96.8% | Anillo MB suma en escenario MB |
| CC | 96.1% | 96.1% | 96.1% | — |
| RTP | 94.0% | 94.0% | 94.0% | — |
| MEXIBÚS | 80.9% | 80.9% | 80.9% | — |
| CBB | 73.7% | 73.7% | 73.7% | — |
| MEXICABLE | 7.1% | 7.1% | 7.1% | — |
| **SUB** | **0.0%** ❌ | **0.0%** ❌ | **0.0%** ❌ | Issue #23 |
| **INTERURBANO** | **0.0%** ❌ | **0.0%** ❌ | **0.0%** ❌ | aislado |

---

## 3. Distribución DI — Detour Factor

### Datos previos (corrida canónica 2026-09-02)

```
Muestra:     100 pares O-D (seed=42)
Min DI:      0.97   ← ya era < 1.0 (bug)
Media DI:    1.545
Max DI:      4.32
Pares < 1.0: 1/100

Distribución categórica:
  eficiente (DI < 1.3):  30.5%
  alto (DI > 2.0):       22.5%
```

### Datos nuevos (post-correcciones, muestra 500 pares)

| Métrica DI | Baseline | MB | METRO |
|------------|----------|----|-------|
| Muestra (pares O-D) | 500 | 500 | 500 |
| Mínimo | 0.78 ⚠️ | 0.80 ⚠️ | 0.80 ⚠️ |
| Media | 1.547 | 1.530 | 1.582 |
| Máximo | 4.20 | 5.36 | 5.36 |
| Pares < 1.0 | 4/500 | 5/500 | 5/500 |
| Valores < 1.0 | [0.78, 0.94, 0.98, 0.99] | [0.80, 0.92, 0.95, 0.97, 0.99] | [0.80, 0.92, 0.95, 0.97, 0.99] |

> ⚠️ El bug de DI < 1.0 se confirma en los **3 escenarios**. Ver Issue #22.  
> Los valores < 1.0 de MB y METRO son idénticos — posiblemente los mismos pares O-D problemáticos.

---

## 4. Bugs identificados en esta re-corrida

| Issue | Título | Escenarios confirmados | Estado |
|-------|--------|------------------------|--------|
| [#22](https://github.com/galigaribaldi/VFTModel/issues/22) | DI < 1.0 geométricamente imposible | Baseline ✅ MB ✅ METRO ✅ | Abierto |
| [#23](https://github.com/galigaribaldi/VFTModel/issues/23) | Tren Suburbano aislado del gigante | Baseline ✅ MB ✅ METRO ✅ | Abierto |

---

## 5. Pendientes

- [x] Corregir bug #22 (DI < 1.0) en `graph_builder.py` — ✅ 2026-10-03, ver §6
- [x] Corregir bug #23 (SUB aislado) — ✅ 2026-10-03, ver §7 (causa real: filtro phantom + falta de transbordos)
- [ ] Actualizar `ANALISIS_PRELIMINAR.md` con valores canónicos nuevos (post-correcciones)
- [x] ~~Verificar cambio de banda T (Aceptable → Idóneo)~~ — revertido: T Baseline vuelve a Aceptable (§7)
- [x] VFT-CHECK-1 (Cablebús α) — verificado: CBB llega como `exclusivo`, CF = 1.0 en las 30 aristas. Solo corregir la tesis
- [ ] Regenerar figura B(v) (VFT-CHECK-3) — usar los datos de §7, no los de la corrida de la mañana

---

## 6. Re-corrida post Fix #22 (2026-10-03, tarde)

**Cambio:** `src/core/services/graph_builder.py` → `_build_base_network`. La distancia de arista ya no se reinicia dentro del radio de snapping; cada estación se proyecta sobre el trazo y se suman sus offsets perpendiculares (`d_seg = off_a + trazo(a→b) + off_b ≥ haversine(a,b)`). Topología sin cambios salvo 6 aristas CC/TROLE (~4.9–5.0 km) que ahora superan el filtro phantom de 5 km.

**Diagnóstico previo:** 13,761 / 25,020 aristas transit tenían `distancia_segmento_m` < haversine entre sus estaciones. Con el fix: 0.

| Métrica | Baseline | MB | METRO |
|---------|----------|----|-------|
| Aristas totales | 45,496 (−6) | 45,981 (−6) | 45,972 (−6) |
| SCC gigante | 10,561 (sin cambio) | 10,658 (sin cambio) | 10,658 (sin cambio) |
| DI mínimo (500 pares, seed=42) | 1.00 | 1.03 | 1.03 |
| DI mediana | 1.505 | 1.48 | 1.53 |
| DI media | 1.609 | 1.595 | 1.637 |
| DI normalizado | 0.663 — Aceptable | 0.680 — Aceptable | 0.647 — Aceptable |
| T (min) | 114.3543 | 109.4037 | 102.2995 |
| T normalizado | 0.691 — **Aceptable** | 0.743 — **Aceptable** | 0.818 — Idóneo |
| Pares DI < 1.0 | 0 | 0 | 0 |

> ⚠️ T Baseline y T MB regresan a banda **Aceptable**. El cambio de banda Aceptable→Idóneo reportado en §1 queda **revertido**.
> Delta T vs Baseline: MB −4.95 min, METRO −12.05 min (antes −4.18 y −10.85).
> Pendiente: Gini B(v) (pesos cambiaron), Issue #23 (filtro phantom elimina SUB Tlalnepantla–Fortuna y Fortuna–Buenavista).

**Tests:** 39/39 ✅. `tests/test_detour.py`: umbral DI se mantiene en 0.95 (error estadístico aceptable); tolerancia `dist_red ≥ dist_recta` reducida de 50 m a 10 m (solo redondeo).

### 6.1 Gini B(v) post Fix #22 (perfil Garibelt completo)

| Métrica | Baseline | MB | METRO |
|---------|----------|----|-------|
| Gini B(v) previo | 0.7894 | 0.7886 | 0.7983 |
| **Gini B(v) post Fix #22** | **0.8009** | **0.8014** | **0.8135** |
| B normalizado — banda | 0.1991 — Crítico | 0.1986 — Crítico | 0.1865 — Crítico |

> ⚠️ Se invierte el orden Baseline vs MB: MB ahora es ligeramente más concentrado que Baseline. Bandas sin cambio.

---

## 7. Re-corrida post Fix #23 (2026-10-03, noche) — valores vigentes

**Cambio:** `graph_builder.py`. (1) Filtro phantom: elimina aristas >5 km **solo si** su trazo cruza un salto >50 m entre sublíneas (rescata 16 tramos continuos: SUB Tlalnepantla–Fortuna–Buenavista, INTERURBANO, MB AGN–Pantitlán, MEXIBÚS León de los Aldama–Centro Cultural, TROLE Río Churubusco–Tepalcates). (2) Catálogo `SUB_OFFICIAL_TRANSFERS`, excepción exclusiva del Tren Suburbano: Buenavista↔Metro, Buenavista↔MB, Lechería↔Mexibús, Tlalnepantla↔CC "Suburbano". El resto de sistemas sigue solo con snapping Q1 (85 m).

| Métrica | Baseline | MB | METRO |
|---------|----------|----|-------|
| Aristas | 45,517 | 46,002 | 45,993 |
| SCC gigante | 10,610 (95.46%) | 10,707 (95.52%) | 10,707 (95.52%) |
| SUB en gigante | 7/7 (100%) ✅ | 7/7 ✅ | 7/7 ✅ |
| C norm | 0.0552 — Crítico | 0.0557 — Crítico | 0.0557 — Crítico |
| Cᵢ norm | 0.25 — Débil | 0.25 — Débil | 0.25 — Débil |
| DI mediana / norm | 1.52 / 0.6533 — Aceptable | 1.51 / 0.66 — Aceptable | 1.58 / 0.6133 — Aceptable |
| DI mínimo | 1.00 | 1.01 | 1.01 |
| T (min) / norm | 113.9087 / 0.6957 — Aceptable | 108.9857 / 0.7475 — Aceptable ⚠️ | 101.921 / 0.8219 — Idóneo |
| Gini B(v) / norm | 0.8007 / 0.1993 — Crítico | 0.8012 / 0.1988 — Crítico | 0.8134 / 0.1866 — Crítico |

> ⚠️ T MB = 0.7475 queda a 0.0025 del umbral Idóneo (0.75): banda frágil, conviene mencionarlo en la tesis.
> Delta T vs Baseline: MB −4.92 min, METRO −11.99 min.
> El gigante gana +49 nodos en Baseline: 7 SUB + 40 CC y 2 MB de Tlalnepantla que solo se conectan vía el transbordo SUB Tlalnepantla.
> Siguen aislados por datos de Apimetro (líneas de un solo sentido): INTERURBANO 0/5 y MEXICABLE 1/14.

**Tests:** 39/39 ✅.

---

## 8. Hallazgos nuevos y estado de la Revisión-2 (2026-10-04)

### 8.1 Hallazgos nuevos sin issue en GitHub

| ID | Hallazgo | Capa | Evidencia |
|----|----------|------|-----------|
| N-1 | INTERURBANO de un solo sentido: las rutas sentido 0 y 1 tienen la misma geometría orientada Zinacantepec → Santa Fe. Falta la estación Observatorio | Apimetro (ACHECK-05 propuesto) | 0/5 nodos en gigante |
| N-2 | MEXICABLE con tramos de un solo sentido entre estaciones | Apimetro (ACHECK-06 propuesto) | 1/14 nodos en gigante |
| N-3 | 9,352 aristas ≤ 5 km cruzan saltos > 500 m entre sublíneas → posibles adyacencias falsas que el filtro phantom no detecta (CC 4,424; RTP 3,674; MB 566; TROLE 244; METRO 188) | VFTModel `graph_builder.py` | Diagnóstico /tmp/vft22 |
| N-4 | Limitación de Q1 = 85 m: 309 pares homónimos intermodales a 85–600 m sin transbordo (Tacubaya Metro↔MB 88 m, Tasqueña Metro↔TL 100 m, Pantitlán, Indios Verdes…) | Metodología / tesis | Solo el SUB tiene excepción (§7) |
| N-5 | CC, RTP y PUMABUS llegan de Apimetro con `derecho_de_via = "compartido"` (CF = 1.38) y velocidades 11 / 11 / 14 km/h. El revisor y los comentarios del código asumen `mixto` (CF = 1.759) con 20 / 16 km/h | Apimetro + tesis (afecta VFT-CHECK-5, Cuadro 5.3) | Velocidad efectiva real CC/RTP ≈ 8.0 km/h |

### 8.2 Estado de las verificaciones VFT-CHECK

| Check | Tema | Estado |
|-------|------|--------|
| CHECK-1 | Cablebús α | ✅ Código correcto (CF = 1.0). Solo corregir tesis |
| CHECK-2 | Normalización B(v) | ⏳ Solo redacción |
| CHECK-3 | Figura B(v) | ⏳ Regenerar con datos §7 |
| CHECK-4 | DI < 1.0 | ✅ Resuelto (#22) |
| CHECK-5 | Velocidad Metrobús / Cuadro 5.3 | ⏳ MB = 16.3 km/h con CF = 1.0 confirmado. Regenerar cuadro y resolver N-5 |
| CHECK-6 | ΔE y desconexiones | ⏳ Bloqueado: ΔE no implementado (Issue #5) |
| CHECK-7 | 125 vs 76 municipios | ⏳ Sin tocar. Afecta C |
| CHECK-8 | SUB subrepresentado | ✅ Resuelto: 12 aristas SUB (antes 3) y 7/7 en gigante |
| CHECK-9 | β TomTom | ⏳ Solo redacción |
| CHECK-10 | 12% modal | ⏳ Redacción, recalcular con conteos post #23 |
| CHECK-11 | Espectro MJG | ⏳ Poblar con valores §7 (los de `ANALISIS_PRELIMINAR.md` están obsoletos) |

**Conteo de aristas de tránsito post #23 (Baseline):** METRO 528, MB 789, TL 52, SUB 12, CBB 30, MEXIBÚS 393, MEXICABLE 17, INTERURBANO 4, TROLE 1,489, CC 10,573, RTP 10,904, PUMABUS 234. Total tránsito 25,025, transbordos 20,492.

### 8.3 Otros pendientes
- [ ] Commit de `graph_builder.py` y `tests/test_detour.py`; comentarios de cierre en #22 y #23
- [ ] Regenerar exportaciones Tableau (CSV en disco son anteriores a los fixes)
- [ ] Issue #21 (normalización B(v) en perfil_nodos) sigue abierto

### 8.4 Issues registrados (2026-10-04)

| Issue | Hallazgo | Tema |
|-------|----------|------|
| [Apimetro#71](https://github.com/galigaribaldi/Apimetro/issues/71) | N-1, N-2 | Sentido 0 con orientación de sentido 1: INTERURBANO, MEXICABLE L1/L2, METRO L9, MEXIBÚS L3, CBB L3 |
| [#24](https://github.com/galigaribaldi/VFTModel/issues/24) | N-3 | Adyacencias falsas por discontinuidades entre sublíneas |
| [#25](https://github.com/galigaribaldi/VFTModel/issues/25) | N-4 | Limitación de Q1 = 85 m (309 transbordos) |
| [#26](https://github.com/galigaribaldi/VFTModel/issues/26) | CHECK-7 | Dominio de 76 demarcaciones ZMVM |
| [#27](https://github.com/galigaribaldi/VFTModel/issues/27) | N-5 | Derecho de vía y velocidades CC/RTP/PUMABUS |
| [#28](https://github.com/galigaribaldi/VFTModel/issues/28) | — | Pruebas de invariantes del grafo |
| [#29](https://github.com/galigaribaldi/VFTModel/issues/29) | — | Regenerar artefactos de la tesis |

---

## 9. Análisis Issue #26 — Dominio de 76 demarcaciones ZMVM (2026-10-04, pendiente de aprobación)

Lista construida con la delimitación SEDATU-CONAPO-INEGI (16 alcaldías + 59 municipios Edomex + Tizayuca, Hgo.). Los 76 nombres coinciden con polígonos de Apimetro y se filtran por CVEGEO. **Confirmar la edición de la delimitación que cita la tesis.**

| Escenario | C actual (141) | C ZMVM (76) | Norm actual → nuevo | Banda |
|-----------|----------------|-------------|---------------------|-------|
| Baseline | 4.4138% | 13.2870% | 0.0552 → 0.1661 | Crítico |
| MB | 4.4596% | 13.4260% | 0.0557 → 0.1678 | Crítico |
| METRO | 4.4596% | 13.4260% | 0.0557 → 0.1678 | Crítico |

- Área del dominio: 23,982 km² → 7,906 km². Área cubierta casi igual (1,058.5 → 1,050.5 km²).
- CDMX sola: C = 53.5% (0.669, Aceptable). 42 de los 76 municipios tienen 0% (incluye Atizapán de Zaragoza, Nicolás Romero, Texcoco, Tizayuca): el dataset no tiene rutas de superficie del Estado de México.
- Hallazgo lateral: consultar `entidad=México` en Apimetro devuelve 141 polígonos (coincide también con "Ciudad de México"). El default interno de `client_spatial.py` usaba "México".

### 9.1 Diseño acordado: opción 2 — C en ambos dominios en la misma respuesta (pendiente de aprobación)

- El cálculo por entidades (141) queda **intacto**: misma `data`, mismo orden, misma dimensión de accesibilidad y mismo `perfil_nodos` (verificado: idénticos al código actual).
- Se agrega `resumen_dominios` en `/spatial-coverage` y `cobertura_dominios` en `/network-profile` con `entidades` (141: C 4.4138%, 0.0552) y `zmvm_76` (C 13.287%, 0.1661).
- Tizayuca se calcula aparte: "Metepec" existe en Hidalgo y Edomex y el analizador fusiona por nombre.
- Hallazgo lateral (sin cambio): pedir `entidades=Hidalgo` junto con Edomex fusiona los dos Metepec (224 filas en vez de 225).

### 9.2 Verificación post #26 (2026-10-04, servidores en vivo con caché caliente)

Perfil Garibelt de los 3 escenarios idéntico a §7 en las 5 dimensiones; se agrega `cobertura_dominios`.

| Escenario | C 141 (norm) | C ZMVM 76 (norm) | DI | T | Gini B(v) |
|-----------|--------------|------------------|----|---|-----------|
| Baseline | 4.4138 (0.0552) | 13.287 (0.1661) | 1.52 | 113.9087 | 0.8007 |
| MB | 4.4596 (0.0557) | 13.426 (0.1678) | 1.51 | 108.9857 | 0.8012 |
| METRO | 4.4596 (0.0557) | 13.426 (0.1678) | 1.58 | 101.921 | 0.8134 |

---

## 10. Trazabilidad observaciones del revisor → issues (2026-10-04)

### 10.1 Con issue existente
| Observación | Issue |
|---|---|
| Cap5 M7 (DI < 1) | #22 ✅ |
| Cap5 C3 (SUB 3 aristas) | #23 ✅ |
| Cap5 C4 (Cuadro 5.3, CF CC/RTP) | #27 |
| Cap5 M4 / CHECK-7 (76 demarcaciones) | #26 (opción 2 aplicada) |
| Cap5 C2, C8, C9 / CHECK-3, -10, -11 | #29 |
| Cap5 M10 (β TomTom: año y métrica) | #6 |
| Cap5 M13, Cap3 M10, M11, C2, Cap5 C1 (ΔE) | #5 (comentar requisitos del revisor) |
| Cap5 M6 (definición Cᵢ = Σ A·w) | #8 |

### 10.2 Sin issue — requieren código o análisis (propuestos)
| ID | Observación | Tema |
|---|---|---|
| P-1 | Cap3 M7, Cap5 M10, Cap3 M2 | Sensibilidad de la Clasificación Garibelt: cortes 0.25/0.50/0.75, referencias de normalización (T 180 min, DI 2.5, C 80 %), α y β; Cᵢ relativa por construcción |
| P-2 | Cap5 M6 (segunda parte) | Transbordos entre paradas del mismo sistema: 10,104 de 20,492 aristas de transbordo (49.3 %), sobre todo RTP y CC. Inflan el grado capilar |
| P-3 | Cap3 C7, Cap5 M5 | Buffers de 800 m llamados isócronas (prometido: 15 min = 1,125 m por red) y cobertura sin población (AGEB, Censo 2020). Relacionado con #7 |
| P-4 | Cap5 M9 | DI por alcaldía sin cuadro ni n por demarcación (100 pares es muestra pequeña) |
| P-5 | Cap5 M11 | T ponderado por demanda (EOD 2017) — opcional |
| P-6 | Hallazgos de sesión | Deuda menor: dissolve por nombre fusiona homónimos (Metepec), P_CACHE ignora entidades/radio/muestra, default "México" en client_spatial, coma faltante en SISTEMAS_VALIDOS, ruta obsoleta en CLAUDE.md |

### 10.3 Solo redacción de tesis (sin código)
Cap3: C1 (nomenclatura Garibelt/MJG), C6 y CHECK-1 (Cablebús CF = 1.0), C8 (T_b sin calibración Google), C9 (Cap. 6 vacío), M8 (tabla T = 85 min hipotética), M9 (top B(v)), M12 (Lee et al. log-normal), M13 (Aldous y Barthélemy).
Cap5: M1 (describir lo que hace el código; 22,766 entidades), M2 (cita Lotero Vélez), C5 (el grafo tiene **12** sistemas, incluido INTERURBANO), C6 (528 / 25,197 = 2.1 %), M8 (casos de Milpa Alta), M12 y CHECK-2 (factor 1/((N−1)(N−2)), complejidad de Brandes), CHECK-9 (α como supuesto del autor).

### 10.4 Decisiones del autor (2026-10-05)
- **P-2 no se registra como bug.** Los transbordos entre paradas del mismo sistema (RTP, CC) se conservan a propósito: en superficie los transbordos son muy variables y conectar esas rutas es intencional. Justificarlo en la tesis (respuesta a Cap5 M6).
- **P-3 no se registra.** Es una decisión conceptual: se conservan los buffers de 800 m. Corregir el término "isócrona" y declararlo como limitación (respuesta a Cap3 C7 y Cap5 M5).
- **P-5 (T ponderado por demanda) queda fuera.**
- **Se registran:** P-1 (sensibilidad), P-4 (DI por alcaldía), P-6 (deuda técnica menor) y comentarios en #5 (ΔE) y #6 (β, α).
- Hallazgo agregado a P-6: la espera de transbordo usa `FALLBACK_FRECUENCIA` de `graph_builder.py` e ignora `frecuencia_minutos` de Apimetro; la tabla de `impedance.py` no se usa y difiere en 5 sistemas.

### 10.5 Issues registrados (2026-10-05)
| Issue | Tema |
|---|---|
| [#30](https://github.com/galigaribaldi/VFTModel/issues/30) | P-1: sensibilidad de la Clasificación Garibelt (cortes, referencias, α y β) |
| [#31](https://github.com/galigaribaldi/VFTModel/issues/31) | P-4: cuadro de DI por alcaldía con n |
| [#32](https://github.com/galigaribaldi/VFTModel/issues/32) | P-6: deuda técnica de la Revisión-2 (incluye frecuencias de transbordo) |
| [#5 comentario](https://github.com/galigaribaldi/VFTModel/issues/5#issuecomment-6008159340) | Requisitos del revisor para ΔE |
| [#6 comentario](https://github.com/galigaribaldi/VFTModel/issues/6#issuecomment-6008159547) | β TomTom, α como supuestos, sensibilidad en #30 |
