"""
MUEBLES BOT - Chilenito Melaminero
Genera composición profesional tipo plantilla + publica en FB e IG
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

# COLORES Y ESTILO
COLOR_AZUL = (27, 58, 107)        # #1B3A6B - color principal
COLOR_VERDE_WS = (37, 211, 102)   # verde WhatsApp
COLOR_BLANCO = (255, 255, 255)
WHATSAPP_NUMERO = "+51 903 427 486"

# RUTAS DE FUENTES
FUENTE_TITULO = "fonts/Montserrat-ExtraBold.ttf"
FUENTE_CURSIVA = "fonts/GreatVibes-Regular.ttf"
FUENTE_REGULAR = "fonts/Montserrat-Regular.ttf"


def toca_publicar_hoy():
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        print("   🖱️  Ejecución manual → publica siempre")
        return True
    
    ahora_utc = datetime.now(timezone.utc)
    lima = ahora_utc - timedelta(hours=5)
    semilla = int(lima.strftime("%Y%m%d"))
    random.seed(semilla)
    minuto_objetivo = random.randint(0, 59)
    
    print(f"   📅 Hora Lima: {lima.strftime('%H:%M')}")
    print(f"   🎯 Minuto objetivo hoy: 9:{minuto_objetivo:02d}")
    
    if lima.hour == 9:
        diferencia = abs(lima.minute - minuto_objetivo)
        if diferencia <= 4:
            print(f"   ✅ ¡Es la hora!")
            return True
    return False


def validar_credenciales():
    print("\n🔐 Validando credenciales...")
    faltan = []
    if not META_TOKEN: faltan.append("META_TOKEN")
    if not FB_PAGE_ID: faltan.append("META_PAGE_ID")
    if not IG_USER_ID: faltan.append("META_INSTAGRAM_ID")
    if not GROQ_API_KEY: faltan.append("GROQ_API_KEY")
    if not GH_TOKEN: faltan.append("GH_TOKEN")
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
        info, scopes=['https://www.googleapis.com/auth/drive']
    )
    print("   ✅ Conectado")
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
        status, done = downloader.next_chunk()
    fh.seek(0)
    print("   ✅ Logo OK")
    return Image.open(fh)


def decidir_mueble_y_titulo():
    """Genera con Groq: descripción del mueble + título corto para la pieza."""
    print("\n🧠 Decidiendo mueble del día con Groq...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        "Eres asistente de marketing para 'Chilenito Melaminero', mueblista en SJL Lima Perú "
        "que hace muebles a medida en melamina. Sugiere UN mueble distinto cada vez. "
        "Responde SOLO en JSON sin markdown, con esta estructura exacta:\n"
        '{"titulo": "MUEBLE DE TV", "descripcion": "Mueble de TV moderno en melamina hickory natural con repisas y cajones"}\n\n'
        "El TITULO debe ser CORTO (máx 3 palabras) en MAYÚSCULAS, ej: LIBRERO, ROPERO, MUEBLE DE TV, COCINA, "
        "CLOSET, ESCRITORIO, COMODA, REPOSTERO, BAR, RECIBIDOR.\n"
        "La DESCRIPCION debe ser visual para una IA generadora de imágenes (color de melamina, estilo, características)."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 300,
        "response_format": {"type": "json_object"}
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        contenido = response.json()['choices'][0]['message']['content']
        data = json.loads(contenido)
        titulo = data.get("titulo", "MUEBLE A MEDIDA").upper()
        descripcion = data.get("descripcion", "Mueble moderno en melamina")
        print(f"   ✅ Título: {titulo}")
        print(f"   ✅ Descripción: {descripcion}")
        return titulo, descripcion
    
    print(f"   ❌ Error: {response.status_code}")
    return "MUEBLE A MEDIDA", "Mueble moderno de melamina con acabados premium"


def generar_imagen_ia(descripcion):
    print(f"\n🎨 Generando imagen IA...")
    prompt = (
        f"Beautiful interior design photo of a modern home with {descripcion}. "
        f"Real lifestyle photography, natural lighting, neutral wall colors, "
        f"styled with decorative items like books, plants, lamps. "
        f"Professional home decor magazine style, 8k, photorealistic, no people"
    )
    prompt_encoded = urllib.parse.quote(prompt)
    # Cuadrado 1080x1080 (formato Instagram)
    url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1080&height=1080&model=flux&nologo=true"
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
    """Carga una fuente del repo o usa la default si falla."""
    try:
        return ImageFont.truetype(ruta, tamano)
    except Exception as e:
        print(f"   ⚠️  No se pudo cargar {ruta}: {e}")
        return ImageFont.load_default()


def componer_pieza_grafica(foto_mueble, logo, titulo):
    """
    Compone la pieza profesional tipo plantilla:
    - Foto centrada con margen
    - Título grande arriba
    - Cursiva "a medida" debajo
    - Banda verde con WhatsApp abajo
    - Logo esquina inferior derecha
    """
    print("\n🖼️  Componiendo pieza gráfica profesional...")
    
    # Canvas final 1080x1080 (formato Instagram)
    W, H = 1080, 1080
    canvas = Image.new("RGB", (W, H), COLOR_BLANCO)
    draw = ImageDraw.Draw(canvas)
    
    # 1. Pegar foto del mueble (ocupando ~70% del centro)
    foto_resized = foto_mueble.resize((W, int(H * 0.75)), Image.LANCZOS)
    canvas.paste(foto_resized, (0, int(H * 0.13)))
    
    # 2. Banda blanca semi-transparente arriba para el título
    overlay = Image.new("RGBA", (W, int(H * 0.18)), (255, 255, 255, 230))
    canvas.paste(overlay, (0, 0), overlay)
    
    # 3. Título principal (ej: "LIBRERO")
    fuente_titulo = cargar_fuente(FUENTE_TITULO, 110)
    bbox = draw.textbbox((0, 0), titulo, font=fuente_titulo)
    text_w = bbox[2] - bbox[0]
    draw.text(((W - text_w) / 2, 30), titulo, font=fuente_titulo, fill=COLOR_AZUL)
    
    # 4. Cursiva "a medida"
    fuente_cursiva = cargar_fuente(FUENTE_CURSIVA, 75)
    cursiva = "a medida"
    bbox = draw.textbbox((0, 0), cursiva, font=fuente_cursiva)
    text_w = bbox[2] - bbox[0]
    draw.text(((W - text_w) / 2, 145), cursiva, font=fuente_cursiva, fill=COLOR_AZUL)
    
    # 5. Banda verde con WhatsApp abajo
    banda_y = int(H * 0.91)
    banda_h = int(H * 0.09)
    draw.rectangle([(0, banda_y), (W, H)], fill=COLOR_VERDE_WS)
    
    # Texto WhatsApp en la banda verde
    fuente_ws = cargar_fuente(FUENTE_TITULO, 50)
    texto_ws = f"📱 WhatsApp: {WHATSAPP_NUMERO}"
    # PIL no renderiza emoji bien — usamos texto simple
    texto_ws = f"WhatsApp: {WHATSAPP_NUMERO}"
    bbox = draw.textbbox((0, 0), texto_ws, font=fuente_ws)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(((W - text_w) / 2, banda_y + (banda_h - text_h) / 2 - 10),
              texto_ws, font=fuente_ws, fill=COLOR_BLANCO)
    
    # 6. Logo esquina inferior derecha (sobre la foto, antes de la banda)
    logo_w = int(W * 0.18)
    logo_ratio = logo_w / logo.width
    logo_h = int(logo.height * logo_ratio)
    logo_resized = logo.convert("RGBA").resize((logo_w, logo_h), Image.LANCZOS)
    pos_x = W - logo_w - 30
    pos_y = banda_y - logo_h - 20
    canvas.paste(logo_resized, (pos_x, pos_y), logo_resized)
    
    # 7. "Entregas todo Lima" abajo izquierda (encima de la banda verde)
    fuente_entrega = cargar_fuente(FUENTE_REGULAR, 32)
    texto_entrega = "🚚 Entregas todo Lima"
    texto_entrega = "Entregas todo Lima"  # Sin emoji
    draw.text((30, banda_y - 50), texto_entrega, font=fuente_entrega, fill=COLOR_AZUL)
    
    # Guardar
    ruta = "post_final.jpg"
    canvas.save(ruta, "JPEG", quality=95)
    print(f"   ✅ Pieza guardada: {ruta}")
    return ruta


def subir_imagen_a_github(ruta_local):
    print("\n☁️  Subiendo a GitHub...")
    timestamp = int(time.time())
    nombre_remoto = f"imagenes_publicadas/post_{timestamp}.jpg"
    with open(ruta_local, 'rb') as f:
        contenido_b64 = base64.b64encode(f.read()).decode('utf-8')
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{nombre_remoto}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}
    payload = {"message": f"Auto: imagen {timestamp}", "content": contenido_b64, "branch": "main"}
    response = requests.put(url, headers=headers, json=payload, timeout=30)
    if response.status_code in (200, 201):
        url_publica = f"https://raw.githubusercontent.com/{GH_REPO}/main/{nombre_remoto}"
        print(f"   ✅ {url_publica}")
        return url_publica
    print(f"   ❌ {response.status_code}")
    return None


def generar_caption_groq(titulo, descripcion):
    print("\n✍️  Generando caption...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = (
        f"Escribe un post CORTO de Instagram/Facebook para 'Chilenito Melaminero' (mueblista en SJL Lima). "
        f"Producto: {titulo} - {descripcion}. "
        f"Tono cercano. Máximo 50 palabras. "
        f"Estructura: 1 línea atractiva + 2 beneficios cortos + CTA. "
        f"Incluye al final: 📲 WhatsApp: {WHATSAPP_NUMERO}. "
        f"Después agrega 6 hashtags relevantes."
    )
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 500
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        caption = response.json()['choices'][0]['message']['content']
        print(f"   ✅ {len(caption)} caracteres")
        return caption
    print(f"   ❌ {response.status_code}")
    return None


def publicar_en_facebook(ruta_foto, texto):
    print("\n📘 Publicando en Facebook...")
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
    print("\n📸 Publicando en Instagram...")
    url_base = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media"
    payload = {'image_url': url_imagen, 'caption': texto, 'access_token': META_TOKEN}
    res = requests.post(url_base, data=payload, timeout=30).json()
    creation_id = res.get('id')
    if not creation_id:
        print(f"   ❌ {json.dumps(res, indent=2)}")
        return False
    print(f"   ✅ Contenedor: {creation_id}")
    time.sleep(7)
    url_pub = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish"
    res_pub = requests.post(url_pub, data={'creation_id': creation_id, 'access_token': META_TOKEN}, timeout=30).json()
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
        
        # Groq decide qué mueble + título
        titulo, descripcion = decidir_mueble_y_titulo()
        
        # IA genera la foto
        foto = generar_imagen_ia(descripcion)
        if not foto:
            sys.exit(1)
        
        # Componer pieza gráfica profesional
        ruta = componer_pieza_grafica(foto, logo, titulo)
        
        # Subir a GitHub para URL pública
        url_publica = subir_imagen_a_github(ruta)
        
        # Caption con Groq
        caption = generar_caption_groq(titulo, descripcion)
        if not caption:
            caption = f"🪑 {titulo} a medida\n\nMuebles de melamina con calidad y diseño.\n\n📲 WhatsApp: {WHATSAPP_NUMERO}\n\n#Muebles #Melamina #Lima #SJL #ChilenitoMelaminero #MueblesPeru"
        
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
