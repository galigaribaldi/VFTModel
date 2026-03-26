"""
@author: Hernán Galileo Cabrera Garibaldi
@date: 2026-03-25
@description: Configurador central del sistema de bitácoras (Logs) del Modelo VFT.
@route: src/core/logger.py
"""

import logging
import sys

# Configuración del formato de salida en consola
formato = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Crear el manejador que escupe los logs a la consola estándar
manejador_consola = logging.StreamHandler(sys.stdout)
manejador_consola.setFormatter(formato)

# Crear el logger principal
vft_logger = logging.getLogger("VFT_Model")
vft_logger.setLevel(logging.INFO) # Nivel base: Captura INFO, WARNING y ERROR
vft_logger.addHandler(manejador_consola)