"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Utilidades de visualización geoespacial para el indicador Detour Factor.
@route: src/core/utils/utils_detaur_factor.py
"""

import folium
from typing import Tuple, Dict, Any

def render_vft_detour_map(result_json: Dict[str, Any], title: str = "Análisis de Ruta") -> Tuple[folium.Map, str, str, float, float, float]:
    """
    Renderiza un mapa interactivo y extrae métricas clave de forma robusta.
    
    Args:
        result_json: Diccionario con llaves 'metrics' y 'map_data'.
        title: Título descriptivo para la consola.
        
    Returns:
        Tuple conteniendo:
        - m: Objeto folium.Map
        - estacion_inicio: Nombre del punto de origen
        - estacion_fin: Nombre del punto de destino
        - factor: Valor del Detour Factor
        - dist_haversine: Distancia en línea recta (km)
        - dist_red: Distancia real en red (km)
    """
    if not result_json or 'metrics' not in result_json or 'map_data' not in result_json:
        raise ValueError("El formato del JSON de entrada es inválido o está vacío.")

    metrics = result_json['metrics']
    map_data = result_json['map_data']
    
    # --- Extracción de métricas para el retorno ---
    estacion_inicio = metrics.get('Origen', 'N/A')
    estacion_fin = metrics.get('Destino', 'N/A')
    factor = metrics.get('Factor_Desviacion', 0.0)
    dist_haversine = metrics.get('Distancia_Recta_km', 0.0)
    dist_red = metrics.get('Distancia_Red_km', 0.0)
    sistemas = metrics.get('Sistemas_Involucrados', [])

    # --- Lógica de Visualización ---
    try:
        # Centrar el mapa en el primer nodo de la ruta
        route = map_data.get('network_route', [])
        if not route:
            raise ValueError("No hay datos de ruta (network_route) para graficar.")
            
        start_node = route[0]
        m = folium.Map(location=[start_node['lat'], start_node['lon']], zoom_start=13, tiles='cartodbpositron')

        # 1. Línea Haversine (Teórica) - Rojo Punteado
        straight_coords = [(p['lat'], p['lon']) for p in map_data.get('haversine_line', [])]
        if straight_coords:
            folium.PolyLine(
                straight_coords, color="#E74C3C", weight=2, dash_array='5', opacity=0.7, 
                tooltip=f"Distancia Directa: {dist_haversine} km"
            ).add_to(m)

        # 2. Ruta en Red (Real) - Azul Sólido
        network_coords = [(p['lat'], p['lon']) for p in route]
        folium.PolyLine(
            network_coords, color="#2E86C1", weight=5, 
            tooltip=f"Distancia en Red: {dist_red} km"
        ).add_to(m)

        # 3. Marcadores de estaciones con lógica de color por sistema
        for point in route:
            # Metro usa azul oscuro, otros sistemas usan naranja
            sys_color = "#1A5276" if point.get('sistema') == "Metro" else "orange"
            
            folium.CircleMarker(
                location=[point['lat'], point['lon']],
                radius=5, color=sys_color, fill=True,
                popup=f"<b>{point.get('nombre', 'Punto')}</b><br>Sistema: {point.get('sistema', 'N/A')}"
            ).add_to(m)

        # Feedback en consola
        print(f"🗺️ {title}")
        print(f"📍 {estacion_inicio} ➡️ {estacion_fin}")
        print(f"📊 DF: {factor} | Red: {dist_red}km vs Teórica: {dist_haversine}km")
        
        return m, estacion_inicio, estacion_fin, factor, dist_haversine, dist_red

    except Exception as e:
        print(f"❌ Error al renderizar el mapa: {e}")
        # Retorno de emergencia en caso de fallo crítico en geometría
        return folium.Map(), estacion_inicio, estacion_fin, factor, dist_haversine, dist_red