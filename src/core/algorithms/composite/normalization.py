"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Funciones de normalización y clasificación para la Clasificación Garibelt —
              Tablero de Diagnóstico Topológico VFT.
@phase: composite
@route: src/core/algorithms/composite/normalization.py
"""


def normalize_scalar(value: float, low: float, high: float) -> float:
    """Min-max normalización a [0, 1]. Clamp a los límites si value está fuera del rango."""
    if high == low:
        return 0.5
    return max(0.0, min(1.0, (value - low) / (high - low)))


def gini_coefficient(values: list[float]) -> float:
    """
    Coeficiente de Gini sobre una lista de valores no negativos.
    0 = distribución perfectamente equitativa. 1 = máxima concentración.
    """
    n = len(values)
    if n == 0:
        return 0.0
    arr = sorted(values)
    total = sum(arr)
    if total == 0:
        return 0.0
    # Fórmula O(n log n) para valores no negativos ordenados
    weighted_sum = sum((i + 1) * v for i, v in enumerate(arr))
    return (2 * weighted_sum) / (n * total) - (n + 1) / n


def classify_band(x_norm: float) -> str:
    """
    Clasifica un valor normalizado [0, 1] en una banda de la Escala Garibelt.
    Los umbrales corresponden a Q1/Q2/Q3 de una distribución uniforme.
    """
    if x_norm < 0.25:
        return "critico"
    elif x_norm < 0.50:
        return "debil"
    elif x_norm < 0.75:
        return "aceptable"
    else:
        return "idoneo"
