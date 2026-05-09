"""
MUEBLES BOT - Chilenito Melaminero
Versión Mejorada: Prompts estructurados + Alta resolución + Reintentos
"""

import os
import io
import json
import base64
import requests
import time
import random
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
ID_CARPETA_LOGO = "1EKyQ0HCDd2gp89_0FAdGClZ9KO3fvcUN"
META_TOKEN       = os.environ.get("META_TOKEN")
FB_PAGE_ID       = os.environ.get("META_PAGE_ID")
IG_USER_ID       = os.environ.get("META_INSTAGRAM_ID")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY")
GH_TOKEN         = os.environ.get("GH_TOKEN")
GH_REPO          = os.environ.get("GITHUB_REPOSITORY", "chilenitomelaminero/muebles-bot")

# RUTAS Y RECURSOS
RUTA_ICONOS   = "icono"
FUENTE_TITULO = "fonts/Montserrat-ExtraBold.ttf"
FUENTE_CURSIVA = "fonts/GreatVibes-Regular.ttf"
FUENTE_REGULAR = "fonts/Montserrat-Regular.ttf"

# COLORES CONSTANTES
COLOR_AZUL      = (27, 58, 107)
COLOR_VERDE_WS  = (37, 211, 102)
COLOR_BLANCO    = (255, 255, 255)
WHATSAPP_NUMERO = "+51 903 427 486"

# ─────────────────────────────────────────────
# CATÁLOGOS — garantizan variedad y prompts correctos
# ─────────────────────────────────────────────
CATALOGO_MUEBLES = [
    ("Ropero 4 Puertas",      "modern wardrobe with 4 sliding doors, melamine finish"),
    ("Cómoda con Espejo",     "bedroom dresser with large rectangular mirror, melamine wood finish"),
    ("Mesa de Comedor",       "rectangular modern dining table with 6 chairs, melamine top"),
    ("Escritorio con Cajonera","office desk with integrated 3-drawer pedestal, melamine finish"),
    ("Rack para TV",          "modern TV stand unit with open shelves and cabinets, melamine finish"),
    ("Estante Flotante",      "minimalist wall-mounted floating shelves unit, melamine finish"),
    ("Velador 2 Cajones",     "compact bedside table with 2 drawers, melamine finish"),
    ("Zapatera 12 Pares",     "tall shoe cabinet rack for 12 pairs, melamine finish"),
    ("Librero 5 Niveles",     "tall 5-shelf open bookcase, melamine finish"),
    ("Cajonera 6 Cajones",    "wide 6-drawer chest of drawers, melamine finish"),
    ("Closet Empotrado",      "built-in walk-in closet with shelves and hanging rail, melamine finish"),
    ("Mesa de Centro",        "modern rectangular coffee table with lower shelf, melamine finish"),
    ("Mueble de Cocina",      "modern kitchen base cabinet with countertop and doors, melamine finish"),
    ("Auxiliar de Baño",      "bathroom storage cabinet with mirror door, melamine finish"),
    ("Escritorio Esquinero",  "L-shaped corner office desk with shelves, melamine finish"),
]

CATALOGO_MELAMINAS = [
    ("Roble Natural",   "#C19A6B"),
    ("Nogal Oscuro",    "#4A3728"),
    ("Blanco Polar",    "#F0EFE9"),
    ("Gris Antracita",  "#3D3D3D"),
    ("Hickory",         "#8B6F47"),
    ("Cerezo",          "#9B4444"),
    ("Wengué",          "#2C1810"),
    ("Pino Claro",      "#DEB887"),
    ("Arena",           "#C2B280"),
    ("Negro Mate",      "#2A2A2A"),
    ("Haya Natural",    "#D4A96A"),
    ("Ceniza",          "#8C8C8C"),
]

# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────
def cargar_fuente(ruta, tamano):
    try:
        return ImageFont.truetype(ruta, tamano)
    except:
        return ImageFont.load_default()

def ajustar_tamano_fuente(texto, ruta_fuente, tamano_maximo, ancho_maximo):
    tamano = tamano_maximo
    fuente = cargar_fuente(ruta_fuente, tamano)
    temp_img = Image.new("RGB", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    while tamano > 20:
        bbox = temp_draw.textbbox((0, 0), texto, font=fuente)
        if (bbox[2] - bbox[0]) <= ancho_maximo:
            return fuente
        tamano -= 5
        fuente = cargar_fuente(ruta_fuente, tamano)
    return fuente

def hex_a_rgb(hex_color):
    """Convierte '#RRGGBB' a tupla (R, G, B)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# ─────────────────────────────────────────────
# GOOGLE DRIVE
# ─────────────────────────────────────────────
def conectar_drive():
    creds_json = os.environ.get("GDRIVE_CREDENTIALS")
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def descargar_logo(service):
    query = f"'{ID_CARPETA_LOGO}' in parents and name = 'logo_principal.webp'"
    res = service.files().list(q=query).execute()
    archivos = res.get('files', [])
    if not archivos:
        return None
    request = service.files().get_media(fileId=archivos[0]['id'])
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return Image.open(fh)

# ─────────────────────────────────────────────
# IA — DECISIÓN DE MUEBLE
# ─────────────────────────────────────────────
def decidir_mueble_y_titulo():
    # Selección aleatoria del catálogo — nunca deja al LLM "inventar" el mueble
    mueble_es, mueble_en = random.choice(CATALOGO_MUEBLES)
    melamina_nombre, melamina_hex = random.choice(CATALOGO_MELAMINAS)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

    prompt = (
        f"Eres copywriter de muebles a medida. El mueble es: '{mueble_es}' en melamina '{melamina_nombre}'.\n"
        f"Responde SOLO con este JSON exacto, sin texto extra ni markdown:\n"
        '{{'
        '"titulo": "TITULO_EN_MAYUSCULAS_MAX_3_PALABRAS", '
        '"melamina": "NOMBRE_MELAMINA", '
        f'"color_hex": "{melamina_hex}", '
        '"desc_img": "PROMPT_EN_INGLES_PARA_FLUX", '
        '"desc_mueble": "DESCRIPCION_CORTA_EN_ESPANOL"'
        '}}\n\n'
        "REGLAS ESTRICTAS para desc_img:\n"
        f"- DEBE empezar con: 'Professional product photography of a {mueble_en}'\n"
        f"- DEBE incluir: 'melamine finish in {melamina_nombre} tone'\n"
        "- DEBE terminar con: 'isolated on pure white background, no shadows, no floor, "
        "studio lighting, ultra sharp focus, photorealistic render, 8k resolution'\n"
        "- NO menciones personas, plantas, decoración, habitaciones ni ambientes.\n"
        "- El mueble debe estar centrado y ocupar al menos 80% del encuadre."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,   # Bajo = más predecible y estructurado
        "response_format": {"type": "json_object"}
    }

    r = requests.post(url, headers=headers, json=payload).json()
    datos = json.loads(r['choices'][0]['message']['content'])

    # Fallback de seguridad: si Groq ignoró las reglas, reconstruimos el prompt
    desc = datos.get('desc_img', '')
    if 'product photography' not in desc.lower():
        print("⚠️  Groq ignoró el formato del prompt. Aplicando fallback.")
        datos['desc_img'] = (
            f"Professional product photography of a {mueble_en}, "
            f"melamine finish in {melamina_nombre} tone, "
            "clean modern Scandinavian design, centered in frame, "
            "isolated on pure white background, no shadows, no floor, "
            "studio lighting, ultra sharp focus, photorealistic render, 8k resolution"
        )

    # Garantizamos que el hex siempre sea del catálogo, no inventado por Groq
    datos['color_hex'] = melamina_hex
    datos['melamina'] = melamina_nombre

    print(f"🪵  Mueble: {datos['titulo']} | Melamina: {melamina_nombre}")
    print(f"📝  Prompt imagen: {datos['desc_img'][:120]}...")
    return datos

# ─────────────────────────────────────────────
# IA — GENERACIÓN DE IMAGEN (ALTA RESOLUCIÓN)
# ─────────────────────────────────────────────
def generar_imagen_ia(desc, max_intentos=3):
    """
    Genera imagen en 2160x2160 (2K) con Flux y la escala a 1080x1080 para el post.
    Escalar desde resolución mayor = imagen nítida, sin pixelado.
    """
    # Prompt reforzado con keywords de calidad para Flux
    prompt_final = (
        f"{desc} "
        "sharp edges, no blur, crisp details, high-end furniture catalog photography, "
        "commercial product shot, DSLR quality"
    )

    for intento in range(max_intentos):
        try:
            seed = random.randint(1, 999999)
            
            # ✅ RESOLUCIÓN ALTA: pedimos 2160x2160 y luego la reducimos a 1080x1080
            # Esto elimina el pixelado y da textura de madera/melamina nítida
            url = (
                f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_final)}"
                f"?width=2160&height=2160&model=flux&nologo=true&seed={seed}&enhance=true"
            )

            print(f"🎨 Generando imagen {intento+1}/{max_intentos} (seed={seed}, 2160px)...")
            res = requests.get(url, timeout=240)  # Más tiempo por la resolución mayor

            if res.status_code != 200:
                print(f"⚠️  HTTP {res.status_code}, reintentando...")
                time.sleep(10)
                continue

            img = Image.open(io.BytesIO(res.content))

            # ─── Validación: rechaza imágenes casi completamente blancas (error silencioso) ───
            img_rgb = img.convert("RGB")
            muestra = img_rgb.resize((100, 100))  # Muestra pequeña para calcular rápido
            pixels = list(muestra.getdata())
            blancos = sum(1 for p in pixels if p[0] > 245 and p[1] > 245 and p[2] > 245)
            pct_blanco = blancos / len(pixels)

            if pct_blanco > 0.95:
                print(f"⚠️  Imagen casi vacía ({pct_blanco:.0%} blanco), reintentando...")
                time.sleep(8)
                continue

            # ─── Escalar de 2160 → 1080 con LANCZOS (máxima calidad de downscaling) ───
            img_hd = img.resize((1080, 1080), Image.LANCZOS)
            print(f"✅ Imagen válida y escalada a 1080px ({pct_blanco:.0%} fondo blanco)")
            return img_hd

        except Exception as e:
            print(f"⚠️  Error intento {intento+1}: {e}")
            time.sleep(10)

    print("❌ No se pudo generar una imagen válida tras todos los intentos")
    return None

# ─────────────────────────────────────────────
# COMPOSICIÓN GRÁFICA
# ─────────────────────────────────────────────
def componer_pieza_grafica(foto_mueble, logo, datos):
    W, H = 1080, 1080
    canvas = Image.new("RGB", (W, H), COLOR_BLANCO)
    draw = ImageDraw.Draw(canvas)

    # 1. Foto Mueble
    foto_w = 950
    ratio = foto_w / foto_mueble.width
    foto_h = int(foto_mueble.height * ratio)
    if foto_h > 600:
        foto_h = 600
    foto_res = foto_mueble.resize((foto_w, foto_h), Image.LANCZOS)
    canvas.paste(foto_res, ((W - foto_w) // 2, 300))

    # 2. Títulos superiores
    f_tit = ajustar_tamano_fuente(datos['titulo'], FUENTE_TITULO, 90, W - 150)
    bbox_t = draw.textbbox((0, 0), datos['titulo'], font=f_tit)
    draw.text(((W - (bbox_t[2] - bbox_t[0])) / 2, 60), datos['titulo'], font=f_tit, fill=COLOR_AZUL)

    f_cur = cargar_fuente(FUENTE_CURSIVA, 85)
    draw.text((W / 2 - 30, 155), "a medida", font=f_cur, fill=COLOR_AZUL)

    # 3. Muestra de color de melamina dinámica
    color_mel = hex_a_rgb(datos.get('color_hex', '#8B4513'))
    draw.rounded_rectangle([70, 245, 170, 345], radius=15, fill=color_mel)
    # Borde sutil para melaminas muy claras
    draw.rounded_rectangle([70, 245, 170, 345], radius=15, outline=COLOR_AZUL, width=2)
    draw.text((190, 255), "MELAMINA:", font=cargar_fuente(FUENTE_REGULAR, 26), fill=COLOR_AZUL)
    draw.text((190, 290), datos['melamina'], font=cargar_fuente(FUENTE_TITULO, 40), fill=COLOR_AZUL)

    # 4. Banda WhatsApp (recta izquierda, curva derecha)
    ws_h, ws_y, ws_w = 105, 925, 490
    draw.rectangle([0, ws_y, ws_w - 55, ws_y + ws_h], fill=COLOR_VERDE_WS)
    draw.ellipse([ws_w - 110, ws_y, ws_w, ws_y + ws_h], fill=COLOR_VERDE_WS)

    try:
        path_ws = os.path.join(RUTA_ICONOS, "icon_whatsapp.png")
        icon_ws = Image.open(path_ws).convert("RGBA").resize((60, 60), Image.LANCZOS)
        canvas.paste(icon_ws, (30, ws_y + 22), icon_ws)
    except:
        pass

    f_ws = cargar_fuente(FUENTE_TITULO, 46)
    draw.text((105, ws_y + 22), WHATSAPP_NUMERO, font=f_ws, fill=COLOR_BLANCO)

    # 5. Delivery con ícono
    try:
        path_truck = os.path.join(RUTA_ICONOS, "icon_truck.png")
        icon_truck = Image.open(path_truck).convert("RGBA").resize((48, 48), Image.LANCZOS)
        canvas.paste(icon_truck, (75, 870), icon_truck)
    except:
        pass
    draw.text((135, 872), "Entregas todo Lima", font=cargar_fuente(FUENTE_REGULAR, 33), fill=COLOR_AZUL)

    # 6. Logo
    logo_w = 230
    logo_h = int(logo.height * (logo_w / logo.width))
    logo_res = logo.convert("RGBA").resize((logo_w, logo_h), Image.LANCZOS)
    canvas.paste(logo_res, (W - logo_w - 60, H - logo_h - 60), logo_res)

    # Guardar en máxima calidad
    ruta = "post_final.jpg"
    canvas.save(ruta, "JPEG", quality=97, subsampling=0)  # subsampling=0 = máxima nitidez JPEG
    return ruta

# ─────────────────────────────────────────────
# GITHUB
# ─────────────────────────────────────────────
def subir_a_github(ruta):
    ts = int(time.time())
    with open(ruta, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')
    url = f"https://api.github.com/repos/{GH_REPO}/contents/imagenes_publicadas/post_{ts}.jpg"
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}
    payload = {"message": f"Post {ts}", "content": content, "branch": "main"}
    r = requests.put(url, headers=headers, json=payload)
    if r.status_code in (200, 201):
        return f"https://raw.githubusercontent.com/{GH_REPO}/main/imagenes_publicadas/post_{ts}.jpg"
    print(f"⚠️  GitHub upload falló: {r.status_code} {r.text[:200]}")
    return None

# ─────────────────────────────────────────────
# CAPTION
# ─────────────────────────────────────────────
def generar_caption(titulo, melamina):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    prompt = (
        f"Escribe un caption para Instagram/Facebook de un mueble a medida: '{titulo}' "
        f"en melamina {melamina}. Fabricado en SJL, Lima, Perú. "
        f"Incluye el número de WhatsApp {WHATSAPP_NUMERO}. "
        "Máximo 5 líneas. Usa emojis relevantes. Cierra con 3 hashtags populares de muebles Perú."
    )
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    r = requests.post(url, headers=headers, json=payload).json()
    return r['choices'][0]['message']['content']

# ─────────────────────────────────────────────
# PUBLICACIÓN META
# ─────────────────────────────────────────────
def publicar_fb(ruta, texto):
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    with open(ruta, 'rb') as f:
        r = requests.post(
            url,
            data={'message': texto, 'access_token': META_TOKEN},
            files={'source': f}
        )
    ok = 'id' in r.json()
    if not ok:
        print(f"⚠️  Facebook error: {r.text[:300]}")
    return ok

def publicar_ig(url_imagen, texto):
    # Paso 1: Crear contenedor
    r1 = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media",
        data={
            'image_url': url_imagen,
            'caption': texto,
            'access_token': META_TOKEN
        }
    ).json()

    c_id = r1.get('id')
    if not c_id:
        print(f"⚠️  Instagram container error: {r1}")
        return False

    # Paso 2: Esperar y publicar
    time.sleep(15)
    r2 = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish",
        data={'creation_id': c_id, 'access_token': META_TOKEN}
    ).json()

    ok = 'id' in r2
    if not ok:
        print(f"⚠️  Instagram publish error: {r2}")
    return ok

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY no configurada")
        return

    try:
        print("🔌 Conectando a Google Drive...")
        service = conectar_drive()
        logo = descargar_logo(service)
        if not logo:
            print("❌ No se encontró logo_principal.webp en Drive")
            return

        print("🤖 Decidiendo mueble con IA...")
        datos = decidir_mueble_y_titulo()

        print("🖼️  Generando imagen en alta resolución...")
        foto = generar_imagen_ia(datos['desc_img'])

        if not foto:
            print("❌ No se pudo generar imagen. Abortando.")
            return

        print("🎨 Componiendo pieza gráfica...")
        ruta = componer_pieza_grafica(foto, logo, datos)

        print("📤 Subiendo a GitHub...")
        url_p = subir_a_github(ruta)

        print("✍️  Generando caption...")
        caption = generar_caption(datos['titulo'], datos['melamina'])

        print("📘 Publicando en Facebook...")
        f_ok = publicar_fb(ruta, caption)

        print("📸 Publicando en Instagram...")
        i_ok = publicar_ig(url_p, caption) if url_p else False

        print(f"\n🏁 Finalizado → Facebook: {'✅' if f_ok else '❌'} | Instagram: {'✅' if i_ok else '❌'}")

    except Exception as e:
        print(f"💥 Error crítico: {e}")
        raise

if __name__ == "__main__":
    main()
