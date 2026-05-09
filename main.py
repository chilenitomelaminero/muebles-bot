"""
MUEBLES BOT - Chilenito Melaminero
Composición profesional tipo plantilla + publica en FB e IG
Versión: Anti-Sanitarios & Prompts Refinados
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
from PIL import Image, ImageDraw, ImageFont
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

# COLORES
COLOR_AZUL = (27, 58, 107)
COLOR_VERDE_WS = (37, 211, 102)
COLOR_BLANCO = (255, 255, 255)
COLOR_GRIS_CLARO = (245, 245, 245)
WHATSAPP_NUMERO = "+51 903 427 486"

# FUENTES
FUENTE_TITULO = "fonts/Montserrat-ExtraBold.ttf"
FUENTE_CURSIVA = "fonts/GreatVibes-Regular.ttf"
FUENTE_REGULAR = "fonts/Montserrat-Regular.ttf"


def toca_publicar_hoy():
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        print("   🖱️  Manual → publica siempre")
        return True
    ahora_utc = datetime.now(timezone.utc)
    lima = ahora_utc - timedelta(hours=5)
    semilla = int(lima.strftime("%Y%m%d"))
    random.seed(semilla)
    minuto_objetivo = random.randint(0, 59)
    print(f"   📅 Hora Lima: {lima.strftime('%H:%M')}")
    print(f"   🎯 Minuto objetivo: 9:{minuto_objetivo:02d}")
    if lima.hour == 9:
        if abs(lima.minute - minuto_objetivo) <= 4:
            print("   ✅ ¡Es la hora!")
            return True
    return False


def validar_credenciales():
    print("\n🔐 Validando credenciales...")
    faltan = [k for k, v in {
        "META_TOKEN": META_TOKEN, "META_PAGE_ID": FB_PAGE_ID,
        "META_INSTAGRAM_ID": IG_USER_ID, "GROQ_API_KEY": GROQ_API_KEY,
        "GH_TOKEN": GH_TOKEN
    }.items() if not v]
    if faltan:
        print(f"   ❌ FALTAN: {', '.join(faltan)}")
        sys.exit(1)
    print("   ✅ OK")


def conectar_drive():
    print("\n📁 Conectando a Drive...")
    creds_json = os.environ.get("GDRIVE_CREDENTIALS")
    if not creds_json:
        print("   ❌ Falta GDRIVE_CREDENTIALS")
        sys.exit(1)
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/drive'])
    print("   ✅ OK")
    return build('drive', 'v3', credentials=creds)


def descargar_logo(service):
    print("\n🎨 Descargando logo...")
    query = f"'{ID_CARPETA_LOGO}' in parents and name = 'logo_principal.webp'"
    res = service.files().list(q=query).execute()
    archivos = res.get('files', [])
    if not archivos:
        print("   ❌ No encontrado")
        return None
    request = service.files().get_media(fileId=archivos[0]['id'])
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    print("   ✅ OK")
    return Image.open(fh)


def decidir_mueble_y_titulo():
    print("\n🧠 Groq decidiendo mueble (Filtro Anti-Batería de Baño)...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Prompt mejorado para evitar errores de traducción (como commode = retrete)
    prompt = (
        "Eres el Director Creativo de 'Chilenito Melaminero', carpintería fina en SJL, Lima. "
        "Tu objetivo es vender muebles de melamina modernos y elegantes. "
        "Responde SOLO en JSON con esta estructura:\n"
        '{"titulo": "ROPERO", "descripcion_imagen": "PROMPT_EN_INGLES", "descripcion_mueble": "DESCRIPCION_VENDEDORA"}\n\n'
        "REGLAS CRÍTICAS:\n"
        "1. descripcion_imagen: Debe ser un prompt en INGLÉS detallado. NUNCA uses la palabra 'commode'. "
        "Si quieres una cómoda usa 'modern bedroom dresser chest of drawers'. "
        "Asegúrate de incluir: 'made of melamine wood', 'studio lighting', 'white background', 'high-end furniture'.\n"
        "2. TITULO: Máximo 2 palabras en MAYÚSCULAS (ej. COMODA DE DIARIO, ROPERO MODERNO).\n"
        "3. Evita cualquier término que pueda confundirse con artículos de baño o cocina si no es el tema."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 400,
        "response_format": {"type": "json_object"}
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        data = json.loads(response.json()['choices'][0]['message']['content'])
        titulo = data.get("titulo", "MUEBLE A MEDIDA").upper()
        desc_imagen = data.get("descripcion_imagen", "Modern melamine furniture, product photography, white background")
        desc_mueble = data.get("descripcion_mueble", titulo)
        print(f"   ✅ Título: {titulo}")
        return titulo, desc_imagen, desc_mueble
    return "MUEBLE A MEDIDA", "Modern melamine furniture", "Mueble a medida"


def generar_imagen_ia(descripcion_imagen):
    print(f"\n🎨 Generando imagen IA con Pollinations (Flux)...")
    # Refinamos el prompt final añadiendo modificadores de calidad
    prompt_final = (
        f"{descripcion_imagen}. Professional product photography, "
        f"clean melamine texture, realistic wood grain, studio setup, "
        f"pure white background, no people, no toilets, highly detailed, 8k"
    )
    prompt_encoded = urllib.parse.quote(prompt_final)
    url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1080&height=1080&model=flux&nologo=true"
    
    try:
        response = requests.get(url, timeout=120)
        if response.status_code == 200:
            print("   ✅ Imagen generada correctamente")
            return Image.open(io.BytesIO(response.content))
        print(f"   ❌ Status {response.status_code}")
        return None
    except Exception as e:
        print(f"   ❌ {e}")
        return None


def cargar_fuente(ruta, tamano):
    try:
        return ImageFont.truetype(ruta, tamano)
    except Exception as e:
        print(f"   ⚠️  Fuente fallback: {e}")
        return ImageFont.load_default()


def texto_centrado(draw, texto, fuente, y, ancho_canvas, color):
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    text_w = bbox[2] - bbox[0]
    x = (ancho_canvas - text_w) / 2
    draw.text((x, y), texto, font=fuente, fill=color)
    return bbox[3] - bbox[1]


def banda_redondeada(draw, x1, y1, x2, y2, radio, color):
    draw.rectangle([(x1, y1 + radio), (x2, y2)], fill=color)
    draw.rectangle([(x1 + radio, y1), (x2 - radio, y2)], fill=color)
    draw.ellipse([(x1, y1), (x1 + radio * 2, y1 + radio * 2)], fill=color)
    draw.ellipse([(x2 - radio * 2, y1), (x2, y1 + radio * 2)], fill=color)


def componer_pieza_grafica(foto_mueble, logo, titulo):
    print("\n🖼️  Armando la plantilla profesional...")
    W, H = 1080, 1080
    canvas = Image.new("RGB", (W, H), COLOR_BLANCO)
    draw = ImageDraw.Draw(canvas)
    
    HEADER_H = 220
    FOOTER_Y = 950
    FOOTER_H = H - FOOTER_Y
    
    # Foto: Redimensionamos para que encaje en el centro
    foto_zona_h = FOOTER_Y - HEADER_H
    foto_resized = foto_mueble.resize((W, foto_zona_h), Image.LANCZOS)
    canvas.paste(foto_resized, (0, HEADER_H))
    
    # Textos y Branding
    fuente_titulo = cargar_fuente(FUENTE_TITULO, 110)
    texto_centrado(draw, titulo, fuente_titulo, 35, W, COLOR_AZUL)
    
    fuente_cursiva = cargar_fuente(FUENTE_CURSIVA, 85)
    texto_centrado(draw, "a medida", fuente_cursiva, 145, W, COLOR_AZUL)
    
    fuente_regular = cargar_fuente(FUENTE_REGULAR, 34)
    draw.text((40, FOOTER_Y - 55), "Calidad Premium - SJL", font=fuente_regular, fill=COLOR_AZUL)
    
    # Logo
    logo_w = int(W * 0.22)
    logo_ratio = logo_w / logo.width
    logo_h = int(logo.height * logo_ratio)
    logo_resized = logo.convert("RGBA").resize((logo_w, logo_h), Image.LANCZOS)
    canvas.paste(logo_resized, (W - logo_w - 40, FOOTER_Y - logo_h - 20), logo_resized)
    
    # Footer Verde WhatsApp
    banda_redondeada(draw, 0, FOOTER_Y, W, H, 30, COLOR_VERDE_WS)
    fuente_ws = cargar_fuente(FUENTE_TITULO, 55)
    texto_ws = f"Pide tu cotización: {WHATSAPP_NUMERO}"
    texto_centrado(draw, texto_ws, fuente_ws, FOOTER_Y + 25, W, COLOR_BLANCO)
    
    ruta = "post_final.jpg"
    canvas.save(ruta, "JPEG", quality=95)
    return ruta


def subir_imagen_a_github(ruta_local):
    print("\n☁️  Subiendo imagen puente a GitHub...")
    ts = int(time.time())
    nombre_remoto = f"imagenes_publicadas/post_{ts}.jpg"
    with open(ruta_local, 'rb') as f:
        contenido_b64 = base64.b64encode(f.read()).decode('utf-8')
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{nombre_remoto}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}
    payload = {"message": f"Post {ts}", "content": contenido_b64, "branch": "main"}
    r = requests.put(url, headers=headers, json=payload, timeout=30)
    if r.status_code in (200, 201):
        return f"https://raw.githubusercontent.com/{GH_REPO}/main/{nombre_remoto}"
    return None


def generar_caption_groq(titulo, desc_mueble):
    print("\n✍️  Redactando caption...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    prompt = (
        f"Escribe un post de Facebook e Instagram para 'Chilenito Melaminero'. "
        f"Mueble: {titulo}. Detalles: {desc_mueble}. "
        f"Usa emojis, tono amable, menciona que estamos en SJL y cerramos con WhatsApp {WHATSAPP_NUMERO}."
    )
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8
    }
    r = requests.post(url, headers=headers, json=payload).json()
    return r['choices'][0]['message']['content']


def publicar_en_facebook(ruta_foto, texto):
    print("\n📘 Publicando en Facebook...")
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    payload = {'message': texto, 'access_token': META_TOKEN, 'published': 'true'}
    with open(ruta_foto, 'rb') as f:
        r = requests.post(url, data=payload, files={'source': f}, timeout=60)
    return 'id' in r.json()


def publicar_en_instagram(url_imagen, texto):
    print("\n📸 Publicando en Instagram...")
    res = requests.post(f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media", 
                         data={'image_url': url_imagen, 'caption': texto, 'access_token': META_TOKEN}).json()
    c_id = res.get('id')
    if c_id:
        time.sleep(10) # Espera para que Instagram procese la imagen
        res_pub = requests.post(f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish", 
                                 data={'creation_id': c_id, 'access_token': META_TOKEN}).json()
        return 'id' in res_pub
    return False


def main():
    print("🚀 BOT CHILENITO MELAMINERO - INICIANDO")
    if not toca_publicar_hoy():
        sys.exit(0)
    validar_credenciales()
    
    try:
        service = conectar_drive()
        logo = descargar_logo(service)
        titulo, desc_img, desc_mueble = decidir_mueble_y_titulo()
        foto = generar_imagen_ia(desc_img)
        
        if foto and logo:
            ruta_final = componer_pieza_grafica(foto, logo, titulo)
            url_pub = subir_imagen_a_github(ruta_final)
            caption = generar_caption_groq(titulo, desc_mueble)
            
            fb_status = publicar_en_facebook(ruta_final, caption)
            ig_status = publicar_en_instagram(url_pub, caption) if url_pub else False
            
            print(f"\n✅ RESULTADOS: FB: {fb_status} | IG: {ig_status}")
    except Exception as e:
        print(f"💥 Error crítico: {e}")

if __name__ == "__main__":
    main()
