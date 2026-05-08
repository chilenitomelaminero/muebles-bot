"""
====================================================================
  MUEBLES BOT - Script de publicación automática
  Publica una imagen + caption en Facebook e Instagram
  
  Las credenciales se leen de variables de entorno (GitHub Secrets)
====================================================================
"""

import os
import requests
import time
import sys

# ====================================================================
# CONFIGURACIÓN - Lee desde variables de entorno (GitHub Secrets)
# ====================================================================

TOKEN = os.environ.get("META_TOKEN")
PAGE_ID_FACEBOOK = os.environ.get("META_PAGE_ID")
INSTAGRAM_BUSINESS_ID = os.environ.get("META_INSTAGRAM_ID")

# Versión del API de Meta
API_VERSION = "v21.0"

# ====================================================================
# QUÉ VAMOS A PUBLICAR (después usaremos un catálogo dinámico)
# ====================================================================

IMAGEN_URL = "https://picsum.photos/800/800"
CAPTION = "🪑 Prueba desde GitHub Actions! Muebles David."

# ====================================================================
# FUNCIONES
# ====================================================================

def publicar_en_facebook(token, page_id, imagen_url, caption):
    """Publica una imagen con caption en la página de Facebook."""
    print("\n📘 Publicando en Facebook...")

    url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/photos"
    params = {
        "url": imagen_url,
        "message": caption,
        "access_token": token
    }

    response = requests.post(url, params=params)
    data = response.json()

    if "id" in data:
        print(f"   ✅ ¡Publicado en Facebook! ID: {data['id']}")
        return True
    else:
        print(f"   ❌ Error en Facebook: {data}")
        return False


def publicar_en_instagram(token, ig_id, imagen_url, caption):
    """Publica una imagen con caption en Instagram (requiere 2 pasos)."""
    print("\n📸 Publicando en Instagram...")

    # PASO 1: Crear el contenedor
    print("   1/2 Creando contenedor...")
    url_container = f"https://graph.facebook.com/{API_VERSION}/{ig_id}/media"
    params_container = {
        "image_url": imagen_url,
        "caption": caption,
        "access_token": token
    }

    response = requests.post(url_container, params=params_container)
    data = response.json()

    if "id" not in data:
        print(f"   ❌ Error creando contenedor: {data}")
        return False

    container_id = data["id"]
    print(f"   ✅ Contenedor creado: {container_id}")

    # Esperar a que Meta procese
    print("   ⏳ Esperando que Meta procese la imagen (5 seg)...")
    time.sleep(5)

    # PASO 2: Publicar el contenedor
    print("   2/2 Publicando contenedor...")
    url_publicar = f"https://graph.facebook.com/{API_VERSION}/{ig_id}/media_publish"
    params_publicar = {
        "creation_id": container_id,
        "access_token": token
    }

    response = requests.post(url_publicar, params=params_publicar)
    data = response.json()

    if "id" in data:
        print(f"   ✅ ¡Publicado en Instagram! ID: {data['id']}")
        return True
    else:
        print(f"   ❌ Error publicando en Instagram: {data}")
        return False


# ====================================================================
# EJECUCIÓN PRINCIPAL
# ====================================================================

def main():
    print("=" * 60)
    print("  MUEBLES BOT - Iniciando publicación automática")
    print("=" * 60)

    # Validar que las variables de entorno existen
    if not TOKEN:
        print("\n❌ ERROR: Falta la variable de entorno META_TOKEN")
        sys.exit(1)
    if not PAGE_ID_FACEBOOK:
        print("\n❌ ERROR: Falta la variable de entorno META_PAGE_ID")
        sys.exit(1)
    if not INSTAGRAM_BUSINESS_ID:
        print("\n❌ ERROR: Falta la variable de entorno META_INSTAGRAM_ID")
        sys.exit(1)

    print(f"\n📷 Imagen: {IMAGEN_URL}")
    print(f"💬 Caption: {CAPTION}")

    # Publicar en ambas redes
    fb_ok = publicar_en_facebook(TOKEN, PAGE_ID_FACEBOOK, IMAGEN_URL, CAPTION)
    ig_ok = publicar_en_instagram(TOKEN, INSTAGRAM_BUSINESS_ID, IMAGEN_URL, CAPTION)

    # Resumen
    print("\n" + "=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    print(f"  Facebook:  {'✅ OK' if fb_ok else '❌ FALLÓ'}")
    print(f"  Instagram: {'✅ OK' if ig_ok else '❌ FALLÓ'}")
    print("=" * 60)

    # Si alguno falló, salir con error
    if not (fb_ok and ig_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
