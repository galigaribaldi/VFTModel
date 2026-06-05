"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Configuración centralizada del cliente Go — fuente única de verdad para
              la URL base de APIMETRO. Se lee desde la variable de entorno APIMETRO_URL;
              si no está definida, cae a localhost (modo LOCAL por defecto).
@route: src/infrastructure/go_client/settings.py
"""

import os

APIMETRO_URL = os.getenv("APIMETRO_URL", "http://localhost:8080/movilidad")
