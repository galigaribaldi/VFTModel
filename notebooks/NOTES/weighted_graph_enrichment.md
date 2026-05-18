# Enriquecimiento Ponderado del Grafo VFT

**Fecha:** 2026-04-28
**Estado:** Planificación — sin implementación aún
**Dependencias:** MV1 (afluencia por línea) + MV2 (AGEBs) de Apimetro

---

## 1. Contexto y motivación

El grafo VFT en su estado actual modela la red de transporte con dos tipos de atributos:

- **Aristas:** peso de enrutamiento (tiempo de viaje con fricción) — *ya implementado y validado*
- **Nodos:** atributos estructurales (modo, sistema, coordenadas) — *sin peso de demanda*

Los indicadores topológicos actuales (fuerza capilar, cobertura espacial, detour factor) miden propiedades **estructurales** de la red: cómo está construida, qué tan eficiente es geométricamente, qué tan bien cubre el territorio. Sin embargo, no incorporan **demanda real**: cuántas personas usan cada estación, cuánta población vive cerca, qué tan cargados están los flujos.

Este documento define la segunda capa de pesos del modelo VFT: el **Node Score**, un indicador compuesto que enriquece cada nodo del grafo con información de demanda observada y potencial.

---

## 2. Las dos fórmulas del modelo VFT

### Tipo A — Edge Weight (enrutamiento) ✅ Implementado

$$w(u,v) = \frac{D_{uv}}{V_{\text{modo}}} \cdot CF_{\text{vía}} + W_{\text{transbordo}}$$

Donde $D_{uv}$ es la distancia real del segmento, $V_{\text{modo}}$ la velocidad operacional, $CF_{\text{vía}}$ el coeficiente de fricción vial y $W_{\text{transbordo}}$ la penalización por transferencia. Sin dependencia de nuevos datos.

### Tipo B — Node Score (importancia de nodo) ⬅ Este documento

$$\text{VFT\_score}_i = \alpha_1 \hat{k}_i + \alpha_2 \hat{a}_i + \alpha_3 \hat{p}_i \quad \left[+ \; \alpha_4 \hat{d}_i \text{ — fase posterior}\right]$$

| Símbolo | Componente | Fuente |
|---|---|---|
| $\hat{k}_i$ | Fuerza capilar normalizada | VFT interno — ya calculado |
| $\hat{a}_i$ | Afluencia estimada por estación normalizada | MV1 Apimetro + desagregación VFT |
| $\hat{p}_i$ | Población captada en buffer 800m normalizada | MV2 Apimetro + intersección espacial VFT |
| $\hat{d}_i$ | Flujo OD asignado normalizado | Fase posterior — sin ETA |

---

## 3. Componente $\hat{a}_i$ — Afluencia estimada por estación

### 3.1 El problema

Apimetro entrega afluencia a nivel de **línea** ($A_\ell$: pasajeros/día por línea). El grafo requiere afluencia a nivel de **nodo** ($a_i$: pasajeros/día por estación). Esta desagregación la realiza VFT internamente.

### 3.2 Método de desagregación — Grado Topológico

Se distribuye la afluencia de cada línea entre sus estaciones en proporción al **grado topológico** de cada nodo en el grafo. El grado $g_i$ cuenta el número de aristas (conexiones) que inciden en el nodo $i$, independientemente de su peso.

$$a_i = A_\ell \cdot \frac{g_i}{\displaystyle\sum_{j \in \ell} g_j}$$

Donde:
- $A_\ell$ = afluencia diaria promedio de la línea $\ell$ (pasajeros/día)
- $g_i = \deg(i)$ = grado del nodo $i$ en el grafo NetworkX
- La suma $\sum_{j \in \ell}$ recorre todas las estaciones pertenecientes a la línea $\ell$

**¿Por qué grado topológico y no fuerza capilar ($k_{in}$)?**

La fuerza capilar $k_{in}$ es un indicador ya normalizado que entra al Node Score como componente independiente $\hat{k}_i$. Usar $k_{in}$ para desagregar $a_i$ crearía una dependencia circular:

$$\hat{k}_i \xrightarrow{\text{desagregación}} \hat{a}_i \xrightarrow{\text{VFT\_score}} \hat{k}_i + \hat{a}_i \approx 2\hat{k}_i$$

El grado topológico $g_i$ es una medida bruta de conectividad (número de aristas, sin ponderación) que está correlacionada con $k_{in}$ pero no es derivada de él, preservando la independencia entre componentes.

**Si una estación pertenece a más de una línea**, se acumula la afluencia de todas sus líneas:

$$a_i = \sum_{\ell \ni i} A_\ell \cdot \frac{g_i}{\displaystyle\sum_{j \in \ell} g_j}$$

### 3.3 Verificación de independencia

Antes de calcular los $\alpha$, se debe verificar la correlación entre componentes:

$$\rho(\hat{k}, \hat{a}) = \frac{\text{Cov}(\hat{k}, \hat{a})}{\sigma_{\hat{k}} \cdot \sigma_{\hat{a}}}$$

| Resultado | Acción |
|---|---|
| $\rho < 0.50$ | Componentes independientes → usar los 3 por separado |
| $0.50 \leq \rho < 0.75$ | Redundancia moderada → documentar y continuar |
| $\rho \geq 0.75$ | Redundancia alta → fusionar en $\delta_i = \beta \hat{k}_i + (1-\beta)\hat{a}_i$ |

---

## 4. Componente $\hat{p}_i$ — Población captada en buffer 800m

### 4.1 Definición

Para cada estación $i$ se traza un buffer de 800m (radio peatonal estándar ITDP/BID). La población captada es la suma de la población de los AGEBs que intersectan ese buffer, ponderada por la fracción de área de cada AGEB dentro del buffer.

$$p_i = \sum_{j \in \mathcal{A}_i} \text{pob}_j \cdot \frac{\text{área}(B_i \cap \text{AGEB}_j)}{\text{área}(\text{AGEB}_j)}$$

Donde:
- $B_i$ = buffer circular de 800m alrededor de la estación $i$ (en CRS proyectado EPSG:6372)
- $\mathcal{A}_i$ = conjunto de AGEBs que intersectan $B_i$
- $\text{pob}_j$ = población total del AGEB $j$ (Censo INEGI 2020)
- La fracción de área asume distribución uniforme de población dentro del AGEB

**Nota de implementación:** el cálculo de área debe realizarse en un CRS métrico proyectado (EPSG:6372 — México Centro) para que las áreas en m² sean correctas. Las coordenadas de estaciones se reproyectan antes del buffer.

### 4.2 Diferencia con el indicador de Cobertura Espacial (C)

| Indicador | Mide | Unidad | Uso |
|---|---|---|---|
| Cobertura Espacial $C$ | Fracción de territorio cubierto por buffers | % de área | Indicador Fase 1 — ya implementado |
| Población captada $p_i$ | Personas dentro del buffer de cada estación | Personas | Componente del Node Score |

$C$ responde "¿qué fracción del territorio tiene acceso?" mientras que $p_i$ responde "¿cuántas personas tiene acceso esta estación?". Son métricas complementarias, no redundantes.

---

## 5. Normalización

Todos los componentes se normalizan al rango $[0, 1]$ usando normalización min-max antes de calcular el Node Score:

$$\hat{x}_i = \frac{x_i - \min(\mathbf{x})}{\max(\mathbf{x}) - \min(\mathbf{x})}$$

Donde $\mathbf{x}$ es el vector de valores del componente sobre todos los nodos del grafo.

**Consideración sobre outliers:** si algún nodo tiene un valor extremo (ej. Pantitlán con afluencia o grado muy superior al resto), la normalización min-max comprimirá el resto de la distribución. En ese caso se puede usar normalización por percentil:

$$\hat{x}_i = \frac{x_i - P_5(\mathbf{x})}{P_{95}(\mathbf{x}) - P_5(\mathbf{x})}, \quad \text{acotado a } [0, 1]$$

---

## 6. Determinación de los $\alpha$ — tres fases

### Fase 1 — Baseline (tan pronto lleguen MV1 + MV2)

$$\alpha_1 = \alpha_2 = \alpha_3 = \frac{1}{3}$$

Objetivo: validar que el score corre correctamente. Verificar que nodos conocidos de alta importancia (Pantitlán, Insurgentes, Pino Suárez, Balderas) aparecen en el top-10. Si no lo hacen, el problema está en los datos de entrada, no en los pesos.

### Fase 2 — Pesos por Entropía / CRITIC (con los 3 componentes calculados)

Los pesos se derivan de la variabilidad observada de cada componente sobre todos los nodos:

$$\alpha_n = \frac{\sigma_n}{\displaystyle\sum_{m=1}^{3} \sigma_m}, \qquad \sigma_n = \text{std}(\hat{x}_n)$$

Un componente más discriminante (mayor dispersión entre nodos) recibe mayor peso. Esto penaliza automáticamente componentes redundantes o de baja varianza.

**Procedimiento:**

1. Calcular los 3 componentes normalizados para todos los nodos
2. Calcular $\text{corr}(\hat{k}, \hat{a})$ — si $\rho \geq 0.75$, fusionar antes de continuar
3. Calcular $\sigma_n$ para cada componente
4. Derivar los $\alpha_n$ y documentarlos como los pesos oficiales del modelo

### Fase 3 — Análisis de sensibilidad por escenarios

Con los $\alpha$ de entropía como referencia, correr 3 escenarios adicionales y comparar rankings:

| Escenario | $\alpha_1$ ($\hat{k}$) | $\alpha_2$ ($\hat{a}$) | $\alpha_3$ ($\hat{p}$) | Hipótesis |
|---|---|---|---|---|
| Estructural | 0.60 | 0.25 | 0.15 | La topología de la red determina la importancia |
| Demanda | 0.15 | 0.65 | 0.20 | Los flujos medidos de pasajeros mandan |
| Equidad | 0.15 | 0.20 | 0.65 | El acceso poblacional define la relevancia |
| Entropía | $\alpha^\star_1$ | $\alpha^\star_2$ | $\alpha^\star_3$ | Pesos emergentes de los datos |

**Métrica de robustez:** un nodo es **estructuralmente robusto** si aparece en el top-10 en los 4 escenarios. Un nodo es **sensible a la hipótesis** si varía más de 20 posiciones entre escenarios. Esta distinción alimenta directamente el análisis de vulnerabilidad $\Delta E$.

---

## 7. Fórmula completa del Node Score

$$\boxed{\text{VFT\_score}_i = \alpha_1 \hat{k}_i + \alpha_2 \hat{a}_i + \alpha_3 \hat{p}_i}$$

$$\hat{k}_i = \frac{k_i - \min(\mathbf{k})}{\max(\mathbf{k}) - \min(\mathbf{k})}, \quad \hat{a}_i = \frac{a_i - \min(\mathbf{a})}{\max(\mathbf{a}) - \min(\mathbf{a})}, \quad \hat{p}_i = \frac{p_i - \min(\mathbf{p})}{\max(\mathbf{p}) - \min(\mathbf{p})}$$

$$a_i = \sum_{\ell \ni i} A_\ell \cdot \frac{g_i}{\sum_{j \in \ell} g_j}, \qquad p_i = \sum_{j \in \mathcal{A}_i} \text{pob}_j \cdot \frac{\text{área}(B_i \cap \text{AGEB}_j)}{\text{área}(\text{AGEB}_j)}$$

---

## 8. Plan de implementación

```
BLOQUE 0 — Ya disponible (sin Apimetro)
├── k_in por nodo              ← capillar_strength.py
└── g_i por nodo               ← nx.degree(G) — disponible hoy

BLOQUE 1 — Infraestructura (antes de recibir datos reales)
├── src/core/services/node_scorer.py
│   ├── disaggregate_ridership(G, afluencia_df) → dict[node_id, float]
│   ├── compute_population_capture(stations_gdf, agebs_gdf) → dict[node_id, float]
│   ├── normalize_component(series) → series [0,1]
│   └── compute_vft_score(k, a, p, alphas) → DataFrame
│
└── src/infrastructure/go_client/client_agebs.py   ← nuevo cliente
    └── fetch_agebs() → GeoDataFrame  (patrón fan-out igual a client_spatial.py)

BLOQUE 2 — Con MV1 + MV2 de Apimetro
├── Validación Fase 1 (α igual) — notebook 05_Node_Score.ipynb
├── Diagnóstico de correlación ρ(k̂, â)
└── Validación Fase 2 (α entropía)

BLOQUE 3 — Análisis de sensibilidad
└── Notebook 05 sección 3: 4 escenarios + tabla de nodos robustos vs sensibles
```

---

---

## 9. Enriquecimiento opcional de indicadores topológicos existentes

Los indicadores de Fases 1 y 2 fueron diseñados y validados como métricas **estructurales** de la red. No requieren los pesos ponderados para funcionar correctamente. Esta sección documenta extensiones **opcionales** que incorporan demanda real una vez que el Node Score esté validado.

> **Regla de implementación:** ninguna extensión de esta sección modifica el código existente.
> Se implementan como variantes paralelas con sufijo `_dem` (demand-weighted) en los mismos módulos o notebooks, sin reemplazar las versiones estructurales.

---

### 9.1 Cobertura Espacial — variante demográfica

**Versión actual (estructural):**

$$C = \frac{\text{Área}\left(\bigcup_i B_i\right)}{\text{Área}_{\text{zona}}}$$

Responde: *¿qué fracción del territorio está dentro de 800m de alguna estación?*

**Variante ponderada por demanda:**

$$C_{\text{dem}} = \frac{\displaystyle\sum_{j \in \mathcal{A}} \text{pob}_j \cdot \mathbb{1}\left[\text{AGEB}_j \cap \bigcup_i B_i \neq \emptyset\right] \cdot \frac{\text{área}(\text{AGEB}_j \cap \bigcup_i B_i)}{\text{área}(\text{AGEB}_j)}}{\displaystyle\sum_{j \in \mathcal{A}} \text{pob}_j}$$

Responde: *¿qué fracción de la **población** está dentro de 800m de alguna estación?*

**Requiere:** MV2 (AGEBs) — mismos datos que $\hat{p}_i$.
**Prioridad:** media. Mejora significativamente la narrativa de equidad del modelo.

---

### 9.2 Detour Factor — variante por pares de alta demanda

**Versión actual:**

$$\text{DF} = \frac{1}{|S|} \sum_{(o,d) \in S} \frac{d_{\text{red}}(o,d)}{d_{\text{euclídea}}(o,d)}$$

Donde $S$ es una muestra aleatoria de pares O-D del grafo.

**Variante ponderada por demanda:**

$$\text{DF}_{\text{dem}} = \frac{\displaystyle\sum_{(o,d) \in S} \hat{a}_o \cdot \hat{a}_d \cdot \frac{d_{\text{red}}(o,d)}{d_{\text{euclídea}}(o,d)}}{\displaystyle\sum_{(o,d) \in S} \hat{a}_o \cdot \hat{a}_d}$$

El muestreo de pares O-D se pondera por la afluencia de los nodos: los pares entre nodos de alta demanda tienen mayor probabilidad de ser seleccionados.

**Interpretación:** en lugar de medir la ineficiencia promedio de cualquier ruta, mide la ineficiencia de las rutas **que más gente usa**. Un DF estructural bajo con DF_dem alto indicaría que las rutas de mayor demanda son las más ineficientes — dato crítico para política de infraestructura.

**Requiere:** $\hat{a}_i$ (Bloque 2).
**Prioridad:** baja. El DF actual ya es válido; esta variante es análisis de segunda capa.

---

### 9.3 Tiempo de Viaje Promedio — variante ponderada por demanda

**Versión P3 (topológica):**

$$T = \frac{1}{N(N-1)} \sum_{i \neq j} t(i,j)$$

Promedio simple sobre todos los pares de nodos alcanzables.

**Variante ponderada por demanda:**

$$T_{\text{dem}} = \frac{\displaystyle\sum_{i \neq j} \hat{a}_i \cdot \hat{a}_j \cdot t(i,j)}{\displaystyle\sum_{i \neq j} \hat{a}_i \cdot \hat{a}_j}$$

Las rutas entre nodos de alta demanda pesan más en el promedio. Si dos nodos tienen $\hat{a}_i \approx 0$ (estaciones de baja afluencia), su par O-D contribuye marginalmente al promedio.

**Interpretación:** $T$ mide el tiempo promedio de la red como sistema físico. $T_{\text{dem}}$ mide el tiempo promedio que experimenta el **pasajero promedio**. Para política pública, $T_{\text{dem}}$ es más informativo.

**Requiere:** $\hat{a}_i$ (Bloque 2) + P3 implementado.
**Prioridad:** media-alta. La diferencia $T_{\text{dem}} - T$ cuantifica el sesgo de la red: si $T_{\text{dem}} > T$, las rutas más demandadas son más lentas que el promedio estructural.

---

### 9.4 Centralidad de Intermediación — variante ponderada por OD

**Versión P4 (topológica):**

$$B(v) = \frac{1}{(N-1)(N-2)} \sum_{s \neq v \neq t} \frac{\sigma_{st}(v)}{\sigma_{st}}$$

Donde $\sigma_{st}$ es el número de caminos más cortos entre $s$ y $t$, y $\sigma_{st}(v)$ los que pasan por $v$.

**Variante ponderada por demanda (demand-weighted betweenness):**

$$B_{\text{dem}}(v) = \frac{\displaystyle\sum_{s \neq v \neq t} \hat{a}_s \cdot \hat{a}_t \cdot \frac{\sigma_{st}(v)}{\sigma_{st}}}{\displaystyle\sum_{s \neq t} \hat{a}_s \cdot \hat{a}_t}$$

Los pares O-D con alta demanda en ambos extremos pesan más. Un nodo que está en el camino mínimo entre dos terminales de alta afluencia tiene $B_{\text{dem}}$ alto aunque su $B$ topológico sea moderado.

**Interpretación:** $B$ identifica nodos críticos para la conectividad estructural de la red. $B_{\text{dem}}$ identifica nodos críticos para los **pasajeros reales**. El análisis de vulnerabilidad $\Delta E$ debería usar $B_{\text{dem}}$ en lugar de $B$ para que la hipótesis del Anillo Periférico sea válida empíricamente.

**Requiere:** $\hat{a}_i$ (Bloque 2) + P4 implementado. Con OD matrix disponible, $\hat{a}_s \cdot \hat{a}_t$ se reemplaza por el flujo OD real $f_{st}$.
**Prioridad:** alta. Es la extensión de mayor impacto analítico — cambia directamente la conclusión sobre qué nodo es más vulnerable.

---

## 10. Resumen de dependencias y prioridades

```
Disponible hoy:
├── k_in ────────────────────────────────── k̂_i  ✅
└── nx.degree(G) ──────── para desagregar â_i  ✅ (lógica, sin datos aún)

Con MV1 (afluencia por línea):
└── a_i (desagregación) ──────────────────  â_i  ✅ → habilita 9.2 DF_dem

Con MV2 (AGEBs):
└── p_i (intersección espacial) ──────────  p̂_i  ✅ → habilita 9.1 C_dem

Con MV1 + MV2 + P3 implementado:
└── T_dem (ponderado por afluencia) ────────────── 9.3

Con MV1 + MV2 + P4 implementado:
└── B_dem (intermediación ponderada) ───────────── 9.4  ← mayor impacto

Con Matriz OD (sin ETA):
└── ôd_i + B_dem mejorado ──────────────────────── fase 4
```

| Extensión | Requiere | Impacto | Prioridad |
|---|---|---|---|
| $C_{\text{dem}}$ | MV2 | Narrativa de equidad | Media |
| $\text{DF}_{\text{dem}}$ | MV1 | Análisis de segunda capa | Baja |
| $T_{\text{dem}}$ | MV1 + P3 | Experiencia del pasajero promedio | Media-alta |
| $B_{\text{dem}}$ | MV1 + P4 | Vulnerabilidad empíricamente válida | **Alta** |
