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
RUTA_ICONOS    = "icono"
FUENTE_TITULO  = "fonts/Montserrat-ExtraBold.ttf"
FUENTE_CURSIVA = "fonts/GreatVibes-Regular.ttf"
FUENTE_REGULAR = "fonts/GlacialIndifference-Regular.otf"  # ← ACTUALIZADA

# COLORES CONSTANTES
COLOR_AZUL      = (0, 56, 159)      # ← #00389F
COLOR_VERDE_WS  = (94, 177, 7)
COLOR_BLANCO    = (255, 255, 255)
WHATSAPP_NUMERO = "+51 903 427 486"

# ─────────────────────────────────────────────
# CATÁLOGOS
# ─────────────────────────────────────────────
CATALOGO_MUEBLES = [
    ("Ropero 4 Puertas",       "ROPERO",        "modern wardrobe with 4 sliding doors, melamine finish"),
    ("Cómoda con Espejo",      "CÓMODA",        "bedroom dresser with large rectangular mirror, melamine wood finish"),
    ("Mesa de Comedor",        "MESA COMEDOR",  "rectangular modern dining table with 6 chairs, melamine top"),
    ("Escritorio con Cajonera","ESCRITORIO",    "office desk with integrated 3-drawer pedestal, melamine finish"),
    ("Rack para TV",           "RACK TV",       "modern TV stand unit with open shelves and cabinets, melamine finish"),
    ("Estante Flotante",       "ESTANTE",       "minimalist wall-mounted floating shelves unit, melamine finish"),
    ("Velador 2 Cajones",      "VELADOR",       "compact bedside table with 2 drawers, melamine finish"),
    ("Zapatera 12 Pares",      "ZAPATERA",      "tall shoe cabinet rack for 12 pairs, melamine finish"),
    ("Librero 5 Niveles",      "LIBRERO",       "tall 5-shelf open bookcase, melamine finish"),
    ("Cajonera 6 Cajones",     "CAJONERA",      "wide 6-drawer chest of drawers, melamine finish"),
    ("Closet Empotrado",       "CLOSET",        "built-in walk-in closet with shelves and hanging rail, melamine finish"),
    ("Mesa de Centro",         "MESA CENTRO",   "modern rectangular coffee table with lower shelf, melamine finish"),
    ("Mueble de Cocina",       "COCINA",        "modern kitchen base cabinet with countertop and doors, melamine finish"),
    ("Auxiliar de Baño",       "AUXILIAR BAÑO", "bathroom storage cabinet with mirror door, melamine finish"),
    ("Escritorio Esquinero",   "ESCRITORIO",    "L-shaped corner office desk with shelves, melamine finish"),
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
    mueble_es, titulo_corto, mueble_en = random.choice(CATALOGO_MUEBLES)
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
        "temperature": 0.4,
        "response_format": {"type": "json_object"}
    }

    r = requests.post(url, headers=headers, json=payload).json()
    datos = json.loads(r['choices'][0]['message']['content'])

    desc = datos.get('desc_img', '')
    if 'product photography' not in desc.lower():
        print("⚠️  Groq ignoró el formato. Aplicando fallback.")
        datos['desc_img'] = (
            f"Professional product photography of a {mueble_en}, "
            f"melamine finish in {melamina_nombre} tone, "
            "clean modern Scandinavian design, centered in frame, "
            "isolated on pure white background, no shadows, no floor, "
            "studio lighting, ultra sharp focus, photorealistic render, 8k resolution"
        )

    datos['color_hex'] = melamina_hex
    datos['melamina'] = melamina_nombre
    datos['titulo'] = titulo_corto
    datos['mueble_es'] = mueble_es

    print(f"🪵  Mueble: {titulo_corto} | Melamina: {melamina_nombre}")
    print(f"📝  Prompt imagen: {datos['desc_img'][:120]}...")
    return datos

# ─────────────────────────────────────────────
# IA — GENERACIÓN DE IMAGEN
# ─────────────────────────────────────────────
def generar_imagen_ia(desc, max_intentos=3):
    prompt_final = (
        f"{desc} "
        "sharp edges, no blur, crisp details, high-end furniture catalog photography, "
        "commercial product shot, DSLR quality"
    )

    for intento in range(max_intentos):
        try:
            seed = random.randint(1, 999999)
            url = (
                f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_final)}"
                f"?width=2160&height=2160&model=flux&nologo=true&seed={seed}&enhance=true"
            )

            print(f"🎨 Generando imagen {intento+1}/{max_intentos} (seed={seed}, 2160px)...")
            res = requests.get(url, timeout=240)

            if res.status_code != 200:
                print(f"⚠️  HTTP {res.status_code}, reintentando...")
                time.sleep(10)
                continue

            img = Image.open(io.BytesIO(res.content))
            img_rgb = img.convert("RGB")
            muestra = img_rgb.resize((100, 100))
            pixels = list(muestra.getdata())
            blancos = sum(1 for p in pixels if p[0] > 245 and p[1] > 245 and p[2] > 245)
            pct_blanco = blancos / len(pixels)

            if pct_blanco > 0.95:
                print(f"⚠️  Imagen casi vacía ({pct_blanco:.0%} blanco), reintentando...")
                time.sleep(8)
                continue

            img_hd = img.resize((1080, 1080), Image.LANCZOS)
            print(f"✅ Imagen válida ({pct_blanco:.0%} fondo blanco)")
            return img_hd

        except Exception as e:
            print(f"⚠️  Error intento {intento+1}: {e}")
            time.sleep(10)

    print("❌ No se pudo generar imagen válida")
    return None

# ─────────────────────────────────────────────
# COMPOSICIÓN GRÁFICA
# ─────────────────────────────────────────────
def dibujar_pildora(draw, x1, y1, x2, y2, color):
    """Píldora ovalada solo en el extremo derecho (izquierdo pegado al borde)."""
    radio = (y2 - y1) // 2
    # Rectángulo principal
    draw.rectangle([x1, y1, x2 - radio, y2], fill=color)
    # Semicírculo solo en el extremo derecho
    draw.ellipse([x2 - radio * 2, y1, x2, y2], fill=color)


def componer_pieza_grafica(foto_mueble, logo, datos):
    W, H = 1080, 1080
    canvas = Image.new("RGB", (W, H), COLOR_BLANCO)
    draw = ImageDraw.Draw(canvas)

    # 1. Foto Mueble — centrada verticalmente en zona media
    foto_w = 950
    ratio = foto_w / foto_mueble.width
    foto_h = int(foto_mueble.height * ratio)
    if foto_h > 620:
        foto_h = 620
    foto_res = foto_mueble.resize((foto_w, foto_h), Image.LANCZOS)
    canvas.paste(foto_res, ((W - foto_w) // 2, 290))

    # 2. Título superior centrado
    f_tit = ajustar_tamano_fuente(datos['titulo'], FUENTE_TITULO, 100, W - 100)
    bbox_t = draw.textbbox((0, 0), datos['titulo'], font=f_tit)
    draw.text(((W - (bbox_t[2] - bbox_t[0])) / 2, 30), datos['titulo'], font=f_tit, fill=COLOR_AZUL)

    # 3. Cursiva "a medida" — pegada debajo del título, ligeramente a la derecha
    f_cur = cargar_fuente(FUENTE_CURSIVA, 80)
    bbox_c = draw.textbbox((0, 0), "a medida", font=f_cur)
    cur_w = bbox_c[2] - bbox_c[0]
    # Posición: centrada respecto al título pero ligeramente desplazada a la derecha
    tit_w = bbox_t[2] - bbox_t[0]
    tit_x = (W - tit_w) / 2
    draw.text((tit_x + tit_w - cur_w + 20, 128), "a medida", font=f_cur, fill=COLOR_AZUL)

    # 4. Muestra de color de melamina — arriba izquierda debajo del título
    color_mel = hex_a_rgb(datos.get('color_hex', '#8B4513'))
    draw.rounded_rectangle([60, 230, 160, 330], radius=15, fill=color_mel)
    draw.rounded_rectangle([60, 230, 160, 330], radius=15, outline=COLOR_AZUL, width=2)
    draw.text((175, 238), "MELAMINA:", font=cargar_fuente(FUENTE_REGULAR, 24), fill=COLOR_AZUL)
    draw.text((175, 268), datos['melamina'], font=cargar_fuente(FUENTE_TITULO, 42), fill=COLOR_AZUL)

    # 5. Logo Chilenito — esquina inferior derecha, ENCIMA de la banda verde
    logo_w = 260
    logo_h = int(logo.height * (logo_w / logo.width))
    logo_res = logo.convert("RGBA").resize((logo_w, logo_h), Image.LANCZOS)
    logo_x = W - logo_w - 20
    logo_y = H - logo_h - 20
    canvas.paste(logo_res, (logo_x, logo_y), logo_res)

    # ─────────────────────────────────────────────────────────────
    # 6. BANDA WHATSAPP
    # Como en la imagen 2:
    # - Empieza desde el borde izquierdo (x=0)
    # - Termina antes del logo (deja espacio para el logo a la derecha)
    # - Ovalada solo en el extremo derecho
    # - Pegada al borde inferior
    # ─────────────────────────────────────────────────────────────
    WS_H  = 120          # alto de la banda
    WS_Y  = H - WS_H    # pegada al borde inferior (Y = 960)
    WS_X1 = 0            # empieza desde el borde izquierdo
    WS_X2 = W - logo_w - 10  # termina antes del logo

    dibujar_pildora(draw, WS_X1, WS_Y, WS_X2, WS_Y + WS_H, COLOR_VERDE_WS)

    # Ícono WhatsApp — izquierda dentro de la banda
    ICONO_W = 72
    icono_x = 25
    icono_y = WS_Y + (WS_H - ICONO_W) // 2
    try:
        path_ws = os.path.join(RUTA_ICONOS, "icon_whatsapp.png")
        icon_ws = Image.open(path_ws).convert("RGBA").resize((ICONO_W, ICONO_W), Image.LANCZOS)
        canvas.paste(icon_ws, (icono_x, icono_y), icon_ws)
    except:
        pass

    # Número WhatsApp — grande, centrado en la banda (considerando espacio del ícono)
    f_ws = cargar_fuente(FUENTE_TITULO, 58)  # más grande que antes
    texto_ws = WHATSAPP_NUMERO
    bbox_ws = draw.textbbox((0, 0), texto_ws, font=f_ws)
    texto_w  = bbox_ws[2] - bbox_ws[0]
    texto_h  = bbox_ws[3] - bbox_ws[1]

    # Zona disponible para el texto (después del ícono, antes del extremo derecho de la banda)
    zona_inicio = icono_x + ICONO_W + 15
    zona_ancho  = (WS_X2 - WS_H // 2) - zona_inicio  # restamos el radio derecho
    texto_x = zona_inicio + (zona_ancho - texto_w) // 2
    texto_y = WS_Y + (WS_H - texto_h) // 2 - 3
    draw.text((texto_x, texto_y), texto_ws, font=f_ws, fill=COLOR_BLANCO)

    # 7. "Entregas todo Lima" — justo encima de la banda verde, izquierda
    try:
        path_truck = os.path.join(RUTA_ICONOS, "icon_truck.png")
        icon_truck = Image.open(path_truck).convert("RGBA").resize((36, 36), Image.LANCZOS)
        canvas.paste(icon_truck, (25, WS_Y - 48), icon_truck)
        txt_x = 68
    except:
        txt_x = 25
    draw.text((txt_x, WS_Y - 46), "Entregas todo Lima",
              font=cargar_fuente(FUENTE_REGULAR, 26), fill=COLOR_AZUL)

    ruta = "post_final.jpg"
    canvas.save(ruta, "JPEG", quality=97, subsampling=0)
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
# CAPTION — ESTILO CHILENITO MELAMINERO
# ─────────────────────────────────────────────
def generar_caption(titulo, melamina, mueble_es=""):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

    titulo_limpio = titulo.title().replace(" ", "")
    hashtags = (
        f"#{titulo_limpio} #{titulo_limpio}AMedida "
        f"#MueblesMelamina #MelaminaAMedida #MueblesSJL #MueblesLima "
        f"#ElChilenitoMelaminero #OrganizacionHogar"
    )

    prompt = (
        f"Eres el community manager de 'El Chilenito Melaminero', mueblista en SJL, Lima Perú. "
        f"Escribe un post de Facebook e Instagram para: {mueble_es or titulo} en melamina {melamina}.\n\n"
        f"Sigue EXACTAMENTE esta estructura, respetando los saltos de línea:\n\n"
        f"[LÍNEA 1] Una frase gancho atractiva sobre el {titulo} a medida. (sin emoji al inicio)\n\n"
        f"[LÍNEA 2] Describe en 1-2 oraciones el beneficio principal de tener este mueble personalizado.\n\n"
        f"[LÍNEA 3] Escribe EXACTAMENTE: 'En El Chilenito Melaminero creamos soluciones que combinan orden, diseño y buen precio 🏡'\n\n"
        f"[CARACTERÍSTICAS] Lista estas 6 características con emoji ✅ al inicio, una por línea:\n"
        f"✅ Diseño personalizado según tu espacio\n"
        f"✅ [característica interna específica del {titulo}]\n"
        f"✅ Colores disponibles a elección (melamina {melamina} y más)\n"
        f"✅ Material resistente y duradero\n"
        f"✅ Precios accesibles\n"
        f"✅ Entregas a domicilio en SJL y todo Lima\n\n"
        f"[LÍNEA MOTIVADORA] Una oración que motive al cliente a dar el paso.\n\n"
        f"[CTA] Escribe EXACTAMENTE: '📲 Cotiza por WhatsApp {WHATSAPP_NUMERO} y recibe asesoría personalizada'\n\n"
        f"[HASHTAGS] Escribe EXACTAMENTE estos hashtags:\n"
        f"{hashtags}\n\n"
        f"IMPORTANTE: Solo el texto del post, sin explicaciones, sin corchetes, en español peruano natural."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 900
    }

    r = requests.post(url, headers=headers, json=payload).json()
    caption = r['choices'][0]['message']['content']
    print(f"✅ Caption generado ({len(caption)} caracteres)")
    return caption

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
        caption = generar_caption(
            datos['titulo'],
            datos['melamina'],
            datos.get('mueble_es', datos['titulo'])
        )

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
