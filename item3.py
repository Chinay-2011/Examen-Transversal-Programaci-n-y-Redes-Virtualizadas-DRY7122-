#!/usr/bin/env python3

import math
import os
import sys
import webbrowser

import requests

try:
    import folium
except ImportError:
    folium = None

GEOCODE_URL = "https://graphhopper.com/api/1/geocode"
ROUTE_URL = "https://graphhopper.com/api/1/route"

RADIO_TIERRA_KM = 6371.0
KM_A_MILLAS = 0.621371

# Perfiles de ruteo soportados por GraphHopper (plan gratuito) + "avion" especial
# nombre_visible -> (perfil_graphhopper o None, factor_de_tiempo)
TRANSPORTES = {
    "1": ("Avión", None, 800),          # se calcula con distancia recta, no usa ruteo
    "2": ("Automóvil", "car", 1.0),
    "3": ("Autobús", "car", 1.25),       # mismo perfil que auto, con paradas/demoras extra
    "4": ("Bicicleta", "bike", 1.0),
    "5": ("Caminata", "foot", 1.0),
}


def salir(texto: str) -> bool:
    """Devuelve True si el usuario escribió 's' (o 'S') para salir."""
    return texto.strip().lower() == "s"


def obtener_api_key() -> str:
    """Obtiene la API Key de GraphHopper desde variable de entorno o input."""
    api_key = os.environ.get("GRAPHHOPPER_API_KEY", "9509a6cc-6f7b-4428-a53a-b16309c24f55").strip()
    if api_key:
        return api_key

    print("No se encontró la variable de entorno GRAPHHOPPER_API_KEY.")
    while True:
        api_key = input("Ingresa tu API Key de GraphHopper (o 's' para salir): ").strip()
        if salir(api_key):
            sys.exit(0)
        if api_key:
            return api_key
        print("  ⚠ La API Key no puede estar vacía.")


def geocodificar_ciudad(nombre: str, pais_esperado: str, api_key: str):
    """
    Consulta la API de Geocoding de GraphHopper y retorna (lat, lng, nombre_resuelto)
    para la primera coincidencia cuyo país sea el esperado. Retorna None si no hay match.
    """
    params = {
        "q": f"{nombre}, {pais_esperado}",
        "locale": "es",
        "limit": 5,
        "key": api_key,
    }
    try:
        resp = requests.get(GEOCODE_URL, params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Error de conexión con GraphHopper: {e}")
        return None

    if resp.status_code != 200:
        try:
            mensaje = resp.json().get("message", resp.text)
        except ValueError:
            mensaje = resp.text
        print(f"  ⚠ Error de la API de Geocoding ({resp.status_code}): {mensaje}")
        return None

    datos = resp.json()
    hits = datos.get("hits", [])
    if not hits:
        return None

    for hit in hits:
        pais_hit = (hit.get("country") or "").lower()
        if pais_hit == pais_esperado.lower():
            lat = hit["point"]["lat"]
            lng = hit["point"]["lng"]
            nombre_resuelto = hit.get("name", nombre.title())
            return lat, lng, nombre_resuelto

    return None


def elegir_ciudad(mensaje: str, pais_esperado: str, api_key: str):
    """
    Pide al usuario una ciudad y la geocodifica validando el país.
    Retorna (lat, lng, nombre_resuelto, salir_bool).
    """
    while True:
        entrada = input(mensaje)
        if salir(entrada):
            return None, None, None, True

        if not entrada.strip():
            print("  ⚠ Debes ingresar un nombre de ciudad.")
            continue

        resultado = geocodificar_ciudad(entrada, pais_esperado, api_key)
        if resultado is None:
            print(f"  ⚠ No se encontró '{entrada}' en {pais_esperado}. Intenta con otro nombre "
                  f"(ej. incluye la región, o revisa la ortografía).")
            continue

        lat, lng, nombre_resuelto = resultado
        return lat, lng, nombre_resuelto, False


def elegir_transporte():
    """Pide al usuario que elija un medio de transporte. Retorna (datos, salir_bool)."""
    print("\nMedios de transporte disponibles:")
    for num, (nombre, _perfil, _factor) in TRANSPORTES.items():
        print(f"  {num}. {nombre}")

    while True:
        entrada = input("Elige el medio de transporte (número) o 's' para salir: ")
        if salir(entrada):
            return None, True
        opcion = entrada.strip()
        if opcion in TRANSPORTES:
            return TRANSPORTES[opcion], False
        print("  ⚠ Opción inválida, intenta nuevamente.")


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Distancia en línea recta (km) entre dos coordenadas, usada para 'Avión'."""
    lat1_r, lon1_r, lat2_r, lon2_r = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return RADIO_TIERRA_KM * c


def calcular_ruta(lat1, lng1, lat2, lng2, perfil: str, api_key: str):
    """
    Consulta la API de Routing de GraphHopper pidiendo geometría e instrucciones.
    Retorna un dict con distancia_km, duracion_horas, puntos (lista de [lat, lng])
    e instrucciones (lista de pasos), o None si falla.
    """
    params = {
        "point": [f"{lat1},{lng1}", f"{lat2},{lng2}"],
        "profile": perfil,
        "locale": "es",
        "instructions": "true",
        "calc_points": "true",
        "points_encoded": "false",
        "key": api_key,
    }
    try:
        resp = requests.get(ROUTE_URL, params=params, timeout=20)
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Error de conexión con GraphHopper: {e}")
        return None

    if resp.status_code != 200:
        try:
            mensaje = resp.json().get("message", resp.text)
        except ValueError:
            mensaje = resp.text

        if "cannot find point" in mensaje.lower():
            print(f"  ⚠ GraphHopper no pudo conectar esa ciudad a una carretera cercana "
                  f"(suele pasar en zonas muy remotas o poco mapeadas).")
            print("    Prueba con una ciudad más grande o cercana a rutas principales.")
        else:
            print(f"  ⚠ Error de la API de Routing ({resp.status_code}): {mensaje}")
        return None

    datos = resp.json()
    paths = datos.get("paths", [])
    if not paths:
        print("  ⚠ GraphHopper no encontró una ruta terrestre entre esos puntos.")
        return None

    path = paths[0]
    distancia_km = path["distance"] / 1000.0
    duracion_horas = path["time"] / (1000.0 * 60 * 60)

    # points viene como GeoJSON LineString: coordinates en [lng, lat]
    coords_lnglat = path.get("points", {}).get("coordinates", [])
    puntos_latlng = [[lat, lng] for lng, lat in coords_lnglat]

    instrucciones = []
    for paso in path.get("instructions", []):
        instrucciones.append({
            "texto": paso.get("text", ""),
            "distancia_km": paso.get("distance", 0) / 1000.0,
        })

    return {
        "distancia_km": distancia_km,
        "duracion_horas": duracion_horas,
        "puntos": puntos_latlng,
        "instrucciones": instrucciones,
    }


def formatear_duracion(horas: float) -> str:
    """Convierte horas decimales en un texto legible (días, horas, minutos)."""
    total_minutos = round(horas * 60)
    dias, resto_min = divmod(total_minutos, 24 * 60)
    horas_enteras, minutos = divmod(resto_min, 60)

    partes = []
    if dias > 0:
        partes.append(f"{dias} día{'s' if dias != 1 else ''}")
    if horas_enteras > 0:
        partes.append(f"{horas_enteras} hora{'s' if horas_enteras != 1 else ''}")
    if minutos > 0 or not partes:
        partes.append(f"{minutos} minuto{'s' if minutos != 1 else ''}")
    return ", ".join(partes)


def mostrar_instrucciones(instrucciones):
    """Imprime las indicaciones paso a paso, similar a Google Maps."""
    if not instrucciones:
        return
    print("-" * 60)
    print("  Indicaciones del trayecto:")
    for i, paso in enumerate(instrucciones, start=1):
        texto = paso["texto"] or "Continuar"
        dist = paso["distancia_km"]
        if dist > 0:
            print(f"   {i:>2}. {texto} ({dist:,.1f} km)")
        else:
            print(f"   {i:>2}. {texto}")


def generar_mapa(origen_nombre, destino_nombre, lat1, lng1, lat2, lng2, puntos, nombre_transporte):
    """
    Genera un mapa HTML interactivo (estilo Google Maps) con la ruta dibujada
    y lo abre en el navegador predeterminado. Retorna la ruta del archivo o None.
    """
    if folium is None:
        print("  ⚠ La librería 'folium' no está instalada, no se puede generar el mapa.")
        print("    Instálala con: pip install folium")
        return None

    centro_lat = (lat1 + lat2) / 2
    centro_lng = (lng1 + lng2) / 2

    mapa = folium.Map(location=[centro_lat, centro_lng], zoom_start=5, tiles="OpenStreetMap")

    folium.Marker(
        location=[lat1, lng1],
        popup=f"Origen: {origen_nombre}",
        tooltip=origen_nombre,
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(mapa)

    folium.Marker(
        location=[lat2, lng2],
        popup=f"Destino: {destino_nombre}",
        tooltip=destino_nombre,
        icon=folium.Icon(color="red", icon="flag"),
    ).add_to(mapa)

    if puntos:
        folium.PolyLine(
            locations=puntos,
            color="#1a73e8",  # azul estilo Google Maps
            weight=5,
            opacity=0.85,
            tooltip=f"Ruta en {nombre_transporte}",
        ).add_to(mapa)
        mapa.fit_bounds(puntos)
    else:
        # Sin geometría de ruta (caso Avión): línea recta entre origen y destino
        folium.PolyLine(
            locations=[[lat1, lng1], [lat2, lng2]],
            color="#1a73e8",
            weight=3,
            opacity=0.7,
            dash_array="10",
            tooltip=f"Trayecto en {nombre_transporte} (línea recta)",
        ).add_to(mapa)
        mapa.fit_bounds([[lat1, lng1], [lat2, lng2]])

    nombre_archivo = f"ruta_{origen_nombre}_{destino_nombre}.html".replace(" ", "_")
    ruta_archivo = os.path.join(os.getcwd(), nombre_archivo)
    mapa.save(ruta_archivo)

    try:
        webbrowser.open(f"file://{ruta_archivo}")
    except Exception:
        pass

    return ruta_archivo


def mostrar_resultado(origen_nombre, destino_nombre, transporte_nombre, distancia_km, horas):
    distancia_millas = distancia_km * KM_A_MILLAS
    duracion_txt = formatear_duracion(horas)

    print("\n" + "=" * 60)
    print(f"  Ciudad de origen:  {origen_nombre} (Chile)")
    print(f"  Ciudad de destino: {destino_nombre} (Argentina)")
    print(f"  Medio de transporte: {transporte_nombre}")
    print("-" * 60)
    print(f"  Distancia: {distancia_km:,.2f} km  /  {distancia_millas:,.2f} millas")
    print(f"  Duración estimada del viaje: {duracion_txt}")


def main():
    print("=" * 60)
    print(" CALCULADORA DE VIAJES: CHILE -> ARGENTINA (con GraphHopper)")
    print(" (Escribe 's' en cualquier momento para salir)")
    print("=" * 60)

    api_key = obtener_api_key()

    while True:
        lat1, lng1, origen_nombre, sale = elegir_ciudad(
            "\nIngresa la Ciudad de Origen (debe ser de Chile): ", "Chile", api_key
        )
        if sale:
            break

        lat2, lng2, destino_nombre, sale = elegir_ciudad(
            "Ingresa la Ciudad de Destino (debe ser de Argentina): ", "Argentina", api_key
        )
        if sale:
            break

        transporte_datos, sale = elegir_transporte()
        if sale:
            break
        nombre_transporte, perfil, factor = transporte_datos

        puntos_ruta = []
        instrucciones = []

        if perfil is None:
            # Avión: distancia recta (GraphHopper no rutea vuelos)
            distancia_km = haversine_km(lat1, lng1, lat2, lng2)
            horas = distancia_km / factor  # factor aquí es la velocidad km/h
        else:
            resultado_ruta = calcular_ruta(lat1, lng1, lat2, lng2, perfil, api_key)
            if resultado_ruta is None:
                print("  No se pudo calcular la ruta con esas ciudades. Intenta con otras.\n")
                continue
            distancia_km = resultado_ruta["distancia_km"]
            horas = resultado_ruta["duracion_horas"] * factor
            puntos_ruta = resultado_ruta["puntos"]
            instrucciones = resultado_ruta["instrucciones"]

        mostrar_resultado(origen_nombre, destino_nombre, nombre_transporte, distancia_km, horas)
        mostrar_instrucciones(instrucciones)

        ruta_mapa = generar_mapa(
            origen_nombre, destino_nombre, lat1, lng1, lat2, lng2, puntos_ruta, nombre_transporte
        )
        if ruta_mapa:
            print("-" * 60)
            print(f"  🗺️  Mapa de la ruta generado y abierto en el navegador:")
            print(f"      {ruta_mapa}")
        print("=" * 60 + "\n")

        continuar = input("¿Deseas calcular otro viaje? (Enter para sí / 's' para salir): ")
        if salir(continuar):
            break

    print("\n¡Gracias por usar la calculadora de viajes! Hasta pronto.")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nPrograma interrumpido por el usuario. ¡Hasta pronto!")
        sys.exit(0)
