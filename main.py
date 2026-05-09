"""
MUEBLES BOT - Chilenito Melaminero
Versión: Buscador de Diseños Reales para SketchUp
"""

import os
import io
import json
import base64
import requests
import time
import sys
import random
import urllib.parse
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageOps
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# CONFIG
ID_CARPETA_LOGO = "1EKyQ0HCDd2gp89_0FAdGClZ9KO3fvcUN"
META_TOKEN = os.environ.get("META_TOKEN")
FB_PAGE_ID = os.environ.get("META_PAGE_ID")
IG_USER_ID = os.environ.get("META_INSTAGRAM_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GH_TOKEN = os.environ.get("GH_TOKEN")
GH_REPO = os.environ.get("GITHUB_REPOSITORY", "chilenitomelaminero/muebles-bot")

# CONFIG DE BÚSQUEDA (Necesitas estas variables en tus Secretos de GitHub)
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_ID = os.environ.get("GOOGLE_SEARCH_ID")

# RUTAS Y RECURSOS
RUTA_ICONOS = "icono"
FUENTE_TITULO = "fonts/Montserrat-ExtraBold.ttf"
FUENTE_CURSIVA = "fonts/GreatVibes-Regular.ttf"
FUENTE_REGULAR = "fonts/Montserrat-Regular.ttf"

# COLORES Y DATOS CONSTANTES
COLOR_AZUL = (27, 58, 107)
COLOR_VERDE_WS = (37, 211, 102)
COLOR_BLANCO = (255, 255, 255)
WHATSAPP_NUMERO = "+51 903 427 486"

def cargar_fuente(ruta, tamano):
    try: return ImageFont.truetype(ruta, tamano)
    except: return ImageFont.load_default()

def ajustar_tamano_fuente(texto, ruta_fuente, tamano_maximo, ancho_maximo):
    tamano = tamano_maximo
    fuente = cargar_fuente(ruta_fuente, tamano)
    temp_img = Image.new("RGB", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    while tamano > 20:
        bbox = temp_draw.textbbox((0, 0), texto, font=fuente)
        if (bbox[2] - bbox[0]) <= ancho_maximo: return fuente
        tamano -= 5
        fuente = cargar_fuente(ruta_fuente, tamano)
    return fuente

def conectar_drive():
    creds_json = os.environ.get("GDRIVE_CREDENTIALS")
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=creds)

def descargar_logo(service):
    query = f"'{ID_CARPETA_LOGO}' in parents and name = 'logo_principal.webp'"
    res = service.files().list(q=query).execute()
    archivos = res.get('files', [])
    if not archivos: return None
    request = service.files().get_media(fileId=archivos[0]['id'])
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done: _, done = downloader.next_chunk()
    fh.seek(0)
    return Image.open(fh)

def decidir_mueble_y_busqueda():
    """
    Usa Groq para decidir qué mueble de tendencia buscar hoy.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        "Eres el curador de 'Chilenito Melaminero'. Elige un mueble de melamina moderno que sea viral.\n"
        "Genera un JSON con:\n"
        '{"titulo": "NOMBRE_MUEBLE", "melamina": "TEXTURA_O_MARCA", "color_hex": "#HEX", "termino_busqueda": "QUERY_PARA_GOOGLE_IMAGES"}\n'
        "REGLA: El término de búsqueda debe ser en inglés para mejores resultados (ej: 'modern floating tv unit melamine minimal')."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.8,
        "response_format": {"type": "json_object"}
    }
    r = requests.post(url, headers=headers, json=payload).json()
    return json.loads(r['choices'][0]['message']['content'])

def buscar_imagen_real(query):
    """
    Busca una imagen real usando Google Custom Search API.
    """
    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_ID:
        print("💥 Error: Faltan credenciales de Google Search.")
        return None

    print(f"🔍 Buscando diseño real para SketchUp: {query}...")
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': f"{query} furniture catalog white background",
        'cx': GOOGLE_SEARCH_ID,
        'key': GOOGLE_SEARCH_API_KEY,
        'searchType': 'image',
        'imgSize': 'large',
        'num': 5
    }
    
    try:
        r = requests.get(url, params=params).json()
        items = r.get('items', [])
        if not items: return None
        
        # Elegimos una imagen al azar de los primeros resultados para no repetir
        url_img = random.choice(items)['link']
        res_img = requests.get(url_img, timeout=15)
        return Image.open(io.BytesIO(res_img.content))
    except Exception as e:
        print(f"💥 Error en búsqueda: {e}")
        return None

def componer_pieza_grafica(foto_mueble, logo, datos):
    W, H = 1080, 1080
    canvas = Image.new("RGB", (W, H), COLOR_BLANCO)
    draw = ImageDraw.Draw(canvas)
    
    # Redimensionar foto real manteniendo aspecto
    foto_mueble = ImageOps.exif_transpose(foto_mueble)
    foto_mueble.thumbnail((950, 600), Image.LANCZOS)
    canvas.paste(foto_mueble, ((W - foto_mueble.width) // 2, 300))
    
    f_tit = ajustar_tamano_fuente(datos['titulo'], FUENTE_TITULO, 85, W-150)
    bbox_t = draw.textbbox((0,0), datos['titulo'], font=f_tit)
    draw.text(((W-(bbox_t[2]-bbox_t[0]))/2, 60), datos['titulo'], font=f_tit, fill=COLOR_AZUL)
    
    f_cur = cargar_fuente(FUENTE_CURSIVA, 85)
    draw.text((W/2 - 30, 155), "a medida", font=f_cur, fill=COLOR_AZUL)

    # Melamina
    draw.rounded_rectangle([70, 245, 170, 345], radius=15, fill=datos.get('color_hex', '#8B4513'))
    draw.text((190, 255), "DISEÑO:", font=cargar_fuente(FUENTE_REGULAR, 26), fill=COLOR_AZUL)
    draw.text((190, 290), "Consultar Textura", font=cargar_fuente(FUENTE_TITULO, 40), fill=COLOR_AZUL)

    # Banda WhatsApp
    ws_h, ws_y, ws_w = 105, 925, 530  
    draw.rectangle([0, ws_y, ws_w - 60, ws_y + ws_h], fill=COLOR_VERDE_WS)
    draw.ellipse([ws_w - 120, ws_y, ws_w, ws_y + ws_h], fill=COLOR_VERDE_WS)
    
    try:
        path_ws = os.path.join(RUTA_ICONOS, "icon_whatsapp.png")
        icon_ws = Image.open(path_ws).convert("RGBA").resize((60, 60), Image.LANCZOS)
        canvas.paste(icon_ws, (30, ws_y + 22), icon_ws)
    except: pass
    
    draw.text((105, ws_y + 22), WHATSAPP_NUMERO, font=cargar_fuente(FUENTE_TITULO, 44), fill=COLOR_BLANCO)

    # Delivery
    try:
        path_truck = os.path.join(RUTA_ICONOS, "icon_truck.png")
        icon_truck = Image.open(path_truck).convert("RGBA").resize((48, 48), Image.LANCZOS)
        canvas.paste(icon_truck, (75, 870), icon_truck)
    except: pass
    draw.text((135, 872), "Entregas todo Lima", font=cargar_fuente(FUENTE_REGULAR, 33), fill=COLOR_AZUL)

    # Logo
    logo_w = 230
    logo_res = logo.convert("RGBA").resize((logo_w, int(logo.height * (logo_w/logo.width))), Image.LANCZOS)
    canvas.paste(logo_res, (W - logo_w - 60, H - logo_res.height - 60), logo_res)

    ruta = "post_final.jpg"
    canvas.save(ruta, "JPEG", quality=100) 
    return ruta

# --- FUNCIONES DE SUBIDA Y PUBLICACIÓN SE MANTIENEN IGUAL ---

def main():
    if not os.environ.get("GROQ_API_KEY"): return
    try:
        service = conectar_drive()
        logo = descargar_logo(service)
        # 1. Groq decide qué buscar
        datos = decidir_mueble_y_busqueda() 
        # 2. Buscamos la imagen real en la web
        foto = buscar_imagen_real(datos['termino_busqueda'])
        
        if foto and logo:
            ruta = componer_pieza_grafica(foto, logo, datos)
            # 3. Proceder con GitHub y Meta...
            print(f"✅ Post listo con imagen real para SketchUp: {datos['titulo']}")
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    main()
