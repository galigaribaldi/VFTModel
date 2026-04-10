"""
@author: Hernán Galileo Cabrera Garibaldi
@date: 2026-03-29
@description: Contratos de datos y validación estricta usando Pydantic.
@route: src/api/schemas/scehmas.py
@notes: Este módulo asegura la pureza de los datos inyectados por la API en Go. 
        Aplica las taxonomías definidas en la tesis para evitar discrepancias 
        antes de construir el grafo topológico en NetworkX
"""
from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import List, Optional
from enum import Enum

## Enums para la taxonomía de nodos y aristas

class JerarquiaTransporte(str, Enum):
    """Define la jerarquía de transporte en 4 niveles para evitar cuellos de botella semánticos."""
    masivo_pesado = "masivo_pesado"
    masivo_medano = "masivo_mediano"
    superficie_convencional = "superficie_convencional"
    superficie_baja = "superficie_baja"

class DerechoVia(str, Enum):
    """Define el nivel de exclusividad del carril o vía para las rutas de transporte."""
    exclusivo = "exclusivo"
    compartido = "compartido"
    mixto = "mixto"
    confinado = "confinado"

class TipoEntidad(str, Enum):
    """Clasifica si la entidad espacial procesada corresponde a un nodo (estación) o arista (ruta)."""
    estacion = "estacion"
    ruta = "ruta"

class SistemaTransporte(str, Enum):
    """Catálogo cerrado a los sistemas de la CDMX y EDOMEX"""
    suburbano = "SUB"
    pumabus = "PUMABUS"
    mexibus = "MEXIBÚS"
    corredor_baja = "CBB"
    interurbano = "INTERURBANO"
    rtp = "RTP"
    corredor_concesionado = "CC"
    mexicable = "MEXICABLE"
    metro = "METRO"
    tren_ligero = "TL"
    trolebus = "TROLE"
    metrobus = "MB"    

## Esquemas de propiedades

class PropertiesSchema(BaseModel):
    """Valida los atributos operativos y topológicos inyectados desde Go."""
    
    model_config = ConfigDict(populate_by_name=True)

    sistema: SistemaTransporte=Field(...)
    nombre: Optional[str] = Field(default=None)
    tipo_entidad: TipoEntidad
    
    jerarquia_transporte: Optional[JerarquiaTransporte] = Field(default=None)
    es_cetram: Optional[bool] = False
    nombre_cetram: Optional[str] = None
    
    # Variables de Rutas (Aristas)
    capacidad_vehiculo: Optional[int] = Field(default=None)
    derecho_de_via: Optional[DerechoVia] = Field(default=None)
    distancia_metros: Optional[float] = Field(default=None)

    # Variables de Estaciones (Nodos)
    alcaldia_municipio: Optional[str] = Field(default=None)
    tipo_estacion: Optional[str] = Field(default=None, alias="tipo")
    
    # Añadimos la variable para capturar el sentido de la entidad
    sentido: Optional[int] = Field(default=None)
    
    ## Atributos para el motor de impedancia
    frecuencia_minutos: Optional[float] = Field(default=None)
    velocidad_promedio_kmh: Optional[float] = None
    distanica_metros: Optional[float] = None
    
    
    @model_validator(mode='after')
    def validar_y_reparar_entidades(self):
        """Validador dinámico y Motor de Imputación."""
        
        # 1. Reparación de nombres nulos
        if self.nombre is None:
            self.nombre = "Desconocido"

        # 2. Reparación de jerarquía huérfana
        if self.jerarquia_transporte is None:
            self.jerarquia_transporte = JerarquiaTransporte.superficie_convencional

        # 3. Imputación para RUTAS (Aristas fantasma)
        if self.tipo_entidad == TipoEntidad.ruta:
            if self.capacidad_vehiculo is None:
                self.capacidad_vehiculo = 60
            if self.derecho_de_via is None:
                self.derecho_de_via = DerechoVia.mixto

        # 4. Imputación/Validación para ESTACIONES (Nodos)
        elif self.tipo_entidad == TipoEntidad.estacion:
            if not self.alcaldia_municipio or self.alcaldia_municipio == "0.0":
                self.alcaldia_municipio = "Desconocida"
            if not self.tipo_estacion or self.tipo_estacion == "0.0":
                # Asumimos superficie por defecto si el dato viene corrupto
                self.tipo_estacion = "Superficie"
                
        return self
    
## Esquemas principales Geojson

class GeoJSONSchema(BaseModel):
    """Esquema principal para validar la estructura completa del GeoJSON inyectado por Go."""
    type: str
    coordinates: list

class FeatureSchema(BaseModel):
    """Define la estructura de un Feature integrando geometría y propiedades estrictas."""
    type: str = "Feature"
    geometry: GeoJSONSchema
    properties: PropertiesSchema

class GeoJSONTransportSchema(BaseModel):
    """Esquema principal de entrada para la Vía 2 (Motor Topológico) del Modelo VFT."""
    type: str = "FeatureCollection"
    features: List[FeatureSchema]
