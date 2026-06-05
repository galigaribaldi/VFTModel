"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Fachada del módulo Detour Factor para simplificar importaciones y acceso al orquestador.
@route: src/core/algorithms/topologicalIndicators/detaurFactor/__init__.py
"""

from src.core.algorithms.topologicalIndicators.detaurFactor.orchestator import DetourFactorOrchestrator

# Definimos qué es lo único que se exporta al usar 'from detaurFactor import *'
__all__ = ["DetourFactorOrchestrator"]