"""
MUEBLES BOT - Chilenito Melaminero
Composición profesional tipo plantilla + publica en FB e IG
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
    print("\n🧠 Decidiendo mueble del día...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = (
        "Eres asistente de marketing para 'Chilenito Melaminero', mueblista en SJL Lima Perú. "
        "Sugiere UN mueble específico de melamina. "
        "Responde SOLO en JSON con esta estructura exacta (sin markdown):\n"
        '{"titulo": "ROPERO", "descripcion_imagen": "A single white melamine wardrobe with 6 doors and mirror, modern minimalist style, isolated on white background, product photography", "descripcion_mueble": "Ropero de 6 puertas en melamina blanca con espejo central"}\n\n'
        "TITULO: máximo 3 palabras en MAYÚSCULAS. Opciones: ROPERO, LIBRERO, MUEBLE DE TV, CLOSET, COCINA, ESCRITORIO, COMODA, REPOSTERO, CAMA, RECIBIDOR.\n"
        "descripcion_imagen: prompt en INGLÉS específico para generar SOLO ESE MUEBLE aislado, como foto de producto, fondo blanco o neutro, SIN personas, SIN habitación completa.\n"
        "descripcion_mueble: descripción en español del mueble para el caption."
    )
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
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
        print(f"   ✅ Prompt imagen: {desc_imagen[:80]}...")
        return titulo, desc_imagen, desc_mueble
    print(f"   ❌ Error: {response.status_code}")
    return "MUEBLE A MEDIDA", "Modern melamine furniture product photography white background", "Mueble a medida en melamina"


def generar_imagen_ia(descripcion_imagen):
    print(f"\n🎨 Generando imagen IA del mueble...")
    # Prompt muy específico para que genere SOLO el mueble
    prompt = (
        f"{descripcion_imagen}. "
        f"Product photography style, single furniture piece only, "
        f"plain white or very light gray background, no room context, "
        f"no people, professional lighting, centered, 8k"
    )
    prompt_encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1080&height=800&model=flux&nologo=true"
    print("   ⏳ Pollinations AI (20-40 seg)...")
    try:
        response = requests.get(url, timeout=120)
        if response.status_code == 200:
            print("   ✅ Imagen generada")
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
    """Dibuja texto perfectamente centrado en X."""
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    text_w = bbox[2] - bbox[0]
    x = (ancho_canvas - text_w) / 2
    draw.text((x, y), texto, font=fuente, fill=color)
    return bbox[3] - bbox[1]  # retorna altura del texto


def banda_redondeada(draw, x1, y1, x2, y2, radio, color):
    """Dibuja un rectángulo con bordes redondeados solo arriba."""
    # Rectángulo principal
    draw.rectangle([(x1, y1 + radio), (x2, y2)], fill=color)
    # Rectángulo horizontal para el medio
    draw.rectangle([(x1 + radio, y1), (x2 - radio, y2)], fill=color)
    # Círculos para las esquinas superiores
    draw.ellipse([(x1, y1), (x1 + radio * 2, y1 + radio * 2)], fill=color)
    draw.ellipse([(x2 - radio * 2, y1), (x2, y1 + radio * 2)], fill=color)


def componer_pieza_grafica(foto_mueble, logo, titulo):
    print("\n🖼️  Componiendo pieza gráfica...")
    
    W, H = 1080, 1080
    
    # Canvas base: fondo blanco limpio
    canvas = Image.new("RGB", (W, H), COLOR_BLANCO)
    draw = ImageDraw.Draw(canvas)
    
    # --- ZONA DE FOTO (entre header y footer) ---
    # Header: 220px arriba
    # Footer: 130px abajo (banda verde)
    # Foto: entre 220 y 950
    
    HEADER_H = 220       # altura del área de título
    FOOTER_Y = 950       # donde empieza la banda verde
    FOOTER_H = H - FOOTER_Y  # altura de la banda verde
    
    # 1. Foto del mueble centrada en la zona media
    foto_zona_h = FOOTER_Y - HEADER_H  # 730px disponibles
    foto_resized = foto_mueble.resize((W, foto_zona_h), Image.LANCZOS)
    canvas.paste(foto_resized, (0, HEADER_H))
    
    # 2. Degradado suave en la parte superior de la foto para que el título sea legible
    for i in range(60):
        alpha = int(255 * (1 - i / 60))
        draw.rectangle([(0, HEADER_H + i), (W, HEADER_H + i + 1)],
                       fill=(255, 255, 255, alpha) if False else (255, 255, 255))
    
    # 3. TÍTULO grande centrado en el header
    fuente_titulo = cargar_fuente(FUENTE_TITULO, 120)
    texto_centrado(draw, titulo, fuente_titulo, 25, W, COLOR_AZUL)
    
    # 4. Cursiva "a medida" centrada justo debajo del título
    fuente_cursiva = cargar_fuente(FUENTE_CURSIVA, 80)
    texto_centrado(draw, "a medida", fuente_cursiva, 155, W, COLOR_AZUL)
    
    # 5. "Entregas todo Lima" abajo izquierda, justo encima de la banda verde
    fuente_regular = cargar_fuente(FUENTE_REGULAR, 34)
    draw.text((35, FOOTER_Y - 52), "Entregas todo Lima", font=fuente_regular, fill=COLOR_AZUL)
    
    # 6. Logo Chilenito abajo derecha, justo encima de la banda verde
    logo_w = int(W * 0.20)
    logo_ratio = logo_w / logo.width
    logo_h = int(logo.height * logo_ratio)
    logo_resized = logo.convert("RGBA").resize((logo_w, logo_h), Image.LANCZOS)
    pos_x = W - logo_w - 30
    pos_y = FOOTER_Y - logo_h - 15
    canvas.paste(logo_resized, (pos_x, pos_y), logo_resized)
    
    # 7. BANDA VERDE con bordes redondeados arriba
    draw_rgba = ImageDraw.Draw(canvas)
    radio = 30
    banda_redondeada(draw_rgba, 0, FOOTER_Y, W, H, radio, COLOR_VERDE_WS)
    
    # 8. Texto WhatsApp centrado en la banda verde
    fuente_ws = cargar_fuente(FUENTE_TITULO, 55)
    texto_ws = f"WhatsApp: {WHATSAPP_NUMERO}"
    center_y = FOOTER_Y + (FOOTER_H - 55) // 2 - 5
    texto_centrado(draw_rgba, texto_ws, fuente_ws, center_y, W, COLOR_BLANCO)
    
    # Guardar
    ruta = "post_final.jpg"
    canvas.save(ruta, "JPEG", quality=95)
    print("   ✅ Pieza guardada")
    return ruta


def subir_imagen_a_github(ruta_local):
    print("\n☁️  Subiendo a GitHub...")
    timestamp = int(time.time())
    nombre_remoto = f"imagenes_publicadas/post_{timestamp}.jpg"
    with open(ruta_local, 'rb') as f:
        contenido_b64 = base64.b64encode(f.read()).decode('utf-8')
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{nombre_remoto}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}
    payload = {"message": f"Auto: {timestamp}", "content": contenido_b64, "branch": "main"}
    response = requests.put(url, headers=headers, json=payload, timeout=30)
    if response.status_code in (200, 201):
        url_pub = f"https://raw.githubusercontent.com/{GH_REPO}/main/{nombre_remoto}"
        print(f"   ✅ {url_pub}")
        return url_pub
    print(f"   ❌ {response.status_code}")
    return None


def generar_caption_groq(titulo, desc_mueble):
    print("\n✍️  Generando caption...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = (
        f"Post CORTO para Instagram/Facebook de 'Chilenito Melaminero' (mueblista SJL Lima). "
        f"Producto: {titulo} - {desc_mueble}. "
        f"Máximo 50 palabras. 1 línea atractiva + 2 beneficios + CTA. "
        f"Al final: 📲 WhatsApp: {WHATSAPP_NUMERO}. "
        f"Después 6 hashtags. Solo el texto del post, sin explicaciones."
    )
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 400
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        caption = response.json()['choices'][0]['message']['content']
        print(f"   ✅ {len(caption)} caracteres")
        return caption
    print(f"   ❌ {response.status_code}")
    return None


def publicar_en_facebook(ruta_foto, texto):
    print("\n📘 Facebook...")
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    payload = {'message': texto, 'access_token': META_TOKEN, 'published': 'true'}
    with open(ruta_foto, 'rb') as f:
        r = requests.post(url, data=payload, files={'source': f}, timeout=60)
    data = r.json()
    if 'id' in data:
        print(f"   ✅ ID: {data['id']}")
        return True
    print(f"   ❌ {json.dumps(data, indent=2)}")
    return False


def publicar_en_instagram(url_imagen, texto):
    print("\n📸 Instagram...")
    res = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media",
        data={'image_url': url_imagen, 'caption': texto, 'access_token': META_TOKEN},
        timeout=30
    ).json()
    creation_id = res.get('id')
    if not creation_id:
        print(f"   ❌ {json.dumps(res, indent=2)}")
        return False
    print(f"   ✅ Contenedor: {creation_id}")
    time.sleep(7)
    res_pub = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish",
        data={'creation_id': creation_id, 'access_token': META_TOKEN},
        timeout=30
    ).json()
    if 'id' in res_pub:
        print(f"   ✅ ID: {res_pub['id']}")
        return True
    print(f"   ❌ {json.dumps(res_pub, indent=2)}")
    return False


def main():
    print("=" * 60)
    print("  🚀 MUEBLES BOT - Chilenito Melaminero")
    print("=" * 60)
    
    print("\n⏰ Verificando horario...")
    if not toca_publicar_hoy():
        print("\n⏭️  No es la hora, saliendo.")
        sys.exit(0)
    
    validar_credenciales()
    
    try:
        service = conectar_drive()
        logo = descargar_logo(service)
        if not logo:
            sys.exit(1)
        
        # Groq decide mueble del día
        titulo, desc_imagen, desc_mueble = decidir_mueble_y_titulo()
        
        # IA genera foto del mueble específico
        foto = generar_imagen_ia(desc_imagen)
        if not foto:
            sys.exit(1)
        
        # Componer pieza profesional
        ruta = componer_pieza_grafica(foto, logo, titulo)
        
        # Subir a GitHub
        url_publica = subir_imagen_a_github(ruta)
        
        # Caption
        caption = generar_caption_groq(titulo, desc_mueble)
        if not caption:
            caption = (
                f"🪑 {titulo} a medida en melamina\n\n"
                f"✅ Diseño personalizado\n✅ Entregamos en Lima\n\n"
                f"📲 WhatsApp: {WHATSAPP_NUMERO}\n\n"
                f"#Muebles #Melamina #Lima #SJL #ChilenitoMelaminero #MueblesPeru"
            )
        
        fb_ok = publicar_en_facebook(ruta, caption)
        ig_ok = False
        if url_publica:
            ig_ok = publicar_en_instagram(url_publica, caption)
        
        print("\n" + "=" * 60)
        print(f"  Facebook:  {'✅' if fb_ok else '❌'}")
        print(f"  Instagram: {'✅' if ig_ok else '❌'}")
        print("=" * 60)
        
        if not fb_ok and not ig_ok:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
