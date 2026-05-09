"""
MUEBLES BOT - Chilenito Melaminero
Versión Restaurada: Prompt Técnico Estricto de Melamina (Diseño Limpio)
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

def decidir_mueble_y_referencia():
    """
    Usa Groq para decidir un mueble y generar una descripción TÉCNICA Y ESTRICTA
    para asegurar un diseño de melamina industrial limpio y profesional.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # --- PROMPT TÉCNICO RESTAURADO ---
    prompt = (
        "Eres el Director de Arte de 'Chilenito Melaminero', expertos en muebles de melamina industrial. Genera un JSON con:\n"
        '{"titulo": "NOMBRE_MUEBLE", "melamina": "MARCA_REAL", "color_hex": "#HEX", "desc_img": "PROMPT_TECNICO_INGLES"}\n'
        "REGLAS CRÍTICAS DE DISEÑO PARA EL PROMPT:\n"
        "1. Material: La imagen DEBE mostrar claramente paneles llanos de melamina. NO madera maciza rústica.\n"
        "2. Construcción: Paneles rectos con tapa-cantos visibles (sharp edge-banding). Nada redondeado ni tallado.\n"
        "3. Acabado: Textura mate o satín industrial. Si es amaderada, veteado de melamina impreso y plano.\n"
        "4. Detalles: Mueble único, moderno, modular, sin artefactos extraños, iluminación de estudio comercial.\n"
        "5. Escena: Fondo blanco puro, SIN PISO, SIN SOMBRAS, photorealistic."
    )
    # ---------------------------------
    
    payload = {
        "model": "llama-3.3-70b-versatile", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.7, # Temperatura más baja para mayor control técnico
        "response_format": {"type": "json_object"}
    }
    r = requests.post(url, headers=headers, json=payload).json()
    return json.loads(r['choices'][0]['message']['content'])

def generar_imagen_ia(desc):
    # La IA recibe el prompt técnico estricto
    prompt_final = f"{desc}. Sharp edges, modular melamine boards, professional furniture catalog photography, pure white background, no floor, no shadows, 8k resolution, photorealistic."
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_final)}?width=1080&height=1080&model=flux&nologo=true"
    res = requests.get(url, timeout=120)
    return Image.open(io.BytesIO(res.content)) if res.status_code == 200 else None

def mejorar_calidad_ia(ruta_original):
    # Proceso de refinamiento simualdo antes de publicar
    print(f"✨ Optimizando acabado de melamina en {ruta_original}...")
    return ruta_original

def componer_pieza_grafica(foto_mueble, logo, datos):
    W, H = 1080, 1080
    canvas = Image.new("RGB", (W, H), COLOR_BLANCO)
    draw = ImageDraw.Draw(canvas)
    
    # 1. Foto Mueble
    foto_w = 950
    ratio = foto_w / foto_mueble.width
    foto_h = int(foto_mueble.height * ratio)
    if foto_h > 600: foto_h = 600
    foto_res = foto_mueble.resize((foto_w, foto_h), Image.LANCZOS)
    canvas.paste(foto_res, ((W - foto_w) // 2, 300))
    
    # 2. Títulos superiores
    f_tit = ajustar_tamano_fuente(datos['titulo'], FUENTE_TITULO, 90, W-150)
    bbox_t = draw.textbbox((0,0), datos['titulo'], font=f_tit)
    draw.text(((W-(bbox_t[2]-bbox_t[0]))/2, 60), datos['titulo'], font=f_tit, fill=COLOR_AZUL)
    
    f_cur = cargar_fuente(FUENTE_CURSIVA, 85)
    draw.text((W/2 - 30, 155), "a medida", font=f_cur, fill=COLOR_AZUL)

    # 3. Muestra Melamina Dinámica
    draw.rounded_rectangle([70, 245, 170, 345], radius=15, fill=datos.get('color_hex', '#8B4513'))
    draw.text((190, 255), "MELAMINA:", font=cargar_fuente(FUENTE_REGULAR, 26), fill=COLOR_AZUL)
    draw.text((190, 290), datos['melamina'], font=cargar_fuente(FUENTE_TITULO, 40), fill=COLOR_AZUL)

    # 4. BANDA WHATSAPP (Ajustada para que el número descanse tranquilo sin tocar el borde)
    ws_h, ws_y, ws_w = 105, 925, 530  
    draw.rectangle([0, ws_y, ws_w - 60, ws_y + ws_h], fill=COLOR_VERDE_WS)
    draw.ellipse([ws_w - 120, ws_y, ws_w, ws_y + ws_h], fill=COLOR_VERDE_WS)
    
    try:
        path_ws = os.path.join(RUTA_ICONOS, "icon_whatsapp.png")
        icon_ws = Image.open(path_ws).convert("RGBA").resize((60, 60), Image.LANCZOS)
        canvas.paste(icon_ws, (30, ws_y + 22), icon_ws)
    except: pass
    
    f_ws = cargar_fuente(FUENTE_TITULO, 44) # Reducido un poco para mayor seguridad
    draw.text((105, ws_y + 22), WHATSAPP_NUMERO, font=f_ws, fill=COLOR_BLANCO)

    # 5. DELIVERY
    try:
        path_truck = os.path.join(RUTA_ICONOS, "icon_truck.png")
        icon_truck = Image.open(path_truck).convert("RGBA").resize((48, 48), Image.LANCZOS)
        canvas.paste(icon_truck, (75, 870), icon_truck)
    except: pass
    draw.text((135, 872), "Entregas todo Lima", font=cargar_fuente(FUENTE_REGULAR, 33), fill=COLOR_AZUL)

    # 6. Logo
    logo_w = 230
    logo_h = int(logo.height * (logo_w / logo.width))
    logo_res = logo.convert("RGBA").resize((logo_w, logo_h), Image.LANCZOS)
    canvas.paste(logo_res, (W - logo_w - 60, H - logo_h - 60), logo_res)

    ruta = "post_final.jpg"
    canvas.save(ruta, "JPEG", quality=100) 
    return mejorar_calidad_ia(ruta)

# ... (El resto de las funciones de subida y publicación se mantienen igual)
