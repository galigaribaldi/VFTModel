"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Fachada del módulo Detour Factor para simplificar importaciones y acceso al orquestador.
@phase: 1
@route: src/core/algorithms/topological/detaurFactor/__init__.py
"""

from src.core.algorithms.topological.detaurFactor.orchestator import DetourFactorOrchestrator

# Definimos qué es lo único que se exporta al usar 'from detaurFactor import *'
__all__ = ["DetourFactorOrchestrator"]