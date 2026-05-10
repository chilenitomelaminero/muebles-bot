"""
MUEBLES BOT — VERSION MEJORADA
EL CHILENITO MELAMINERO

MEJORAS:
✅ Formato vertical 1080x1350
✅ Fondo full screen
✅ PNG más grande
✅ Recorte automático transparencia PNG
✅ Sombra premium
✅ Halo de luz moderno
✅ Textos más limpios
✅ Captions cortos
✅ Mejor composición Facebook/Instagram
"""

import os
import io
import base64
import requests
import time
import hashlib

from datetime import datetime

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter
)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

META_TOKEN   = os.environ.get("META_TOKEN")
FB_PAGE_ID   = os.environ.get("META_PAGE_ID")
IG_USER_ID   = os.environ.get("META_INSTAGRAM_ID")
GH_TOKEN     = os.environ.get("GH_TOKEN")

GH_REPO = os.environ.get(
    "GITHUB_REPOSITORY",
    "chilenitomelaminero/muebles-bot"
)

RUTA_MUEBLES = "muebles_sin_fondo"

FUENTE_TITULO  = "fonts/BebasNeue-Regular.ttf"
FUENTE_CURSIVA = "fonts/GreatVibes-Regular.ttf"

WHATSAPP_NUMERO = "+51 903 427 486"

# ─────────────────────────────────────────────
# FONDOS
# ─────────────────────────────────────────────

FONDOS = [
    {"ruta": "plantilla/FD_AZUL.png", "tipo": "azul"},
    {"ruta": "plantilla/FD_BLANCO.png", "tipo": "blanco"},
]

# ─────────────────────────────────────────────
# COLORES
# ─────────────────────────────────────────────

COLORES_POR_FONDO = {
    "azul": {
        "titulo": (255,255,255),
        "cursiva": (255,220,0),
    },

    "blanco": {
        "titulo": (0,56,159),
        "cursiva": (0,56,159),
    }
}

# ─────────────────────────────────────────────
# MAPA TITULOS
# ─────────────────────────────────────────────

MAPA_TITULOS = {

    "mueble_espejo_tocador": "TOCADOR",
    "repisero_tocador": "TOCADOR",
    "repisero_tocador_con_espejo": "TOCADOR",

    "ropero": "ROPERO",
    "ropero_2": "ROPERO",

    "escritorio": "ESCRITORIO",

    "centro_de_tv": "CENTRO DE TV",

    "cajonera": "CAJONERA",
    "cajonera_2": "CAJONERA",

    "velador": "VELADOR",

    "repostero": "REPOSTERO",

    "cajonera_nina": "CAJONERA",
}

# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────

def cargar_fuente(ruta, tamano):
    try:
        return ImageFont.truetype(ruta, tamano)
    except:
        return ImageFont.load_default()

def ajustar_tamano_fuente(
    texto,
    ruta_fuente,
    tamano_maximo,
    ancho_maximo
):
    tamano = tamano_maximo

    while tamano > 20:

        fuente = cargar_fuente(
            ruta_fuente,
            tamano
        )

        img = Image.new("RGB", (1,1))
        draw = ImageDraw.Draw(img)

        bbox = draw.textbbox(
            (0,0),
            texto,
            font=fuente
        )

        ancho = bbox[2] - bbox[0]

        if ancho <= ancho_maximo:
            return fuente

        tamano -= 4

    return fuente

def nombre_a_titulo(nombre_archivo):

    nombre = os.path.splitext(
        nombre_archivo
    )[0].lower()

    nombre = (
        nombre
        .replace("ñ","n")
        .replace("á","a")
        .replace("é","e")
        .replace("í","i")
        .replace("ó","o")
        .replace("ú","u")
    )

    return MAPA_TITULOS.get(
        nombre,
        nombre.replace("_"," ").upper()
    )

# ─────────────────────────────────────────────
# GITHUB
# ─────────────────────────────────────────────

def listar_muebles_github():

    url = f"https://api.github.com/repos/{GH_REPO}/contents/{RUTA_MUEBLES}"

    headers = {
        "Authorization": f"Bearer {GH_TOKEN}"
    }

    r = requests.get(
        url,
        headers=headers
    ).json()

    if isinstance(r, list):

        return [
            f['name']
            for f in r
            if f['name'].lower().endswith('.png')
        ]

    return []

def descargar_mueble_github(nombre_archivo):

    url = (
        f"https://raw.githubusercontent.com/"
        f"{GH_REPO}/main/"
        f"{RUTA_MUEBLES}/{nombre_archivo}"
    )

    r = requests.get(url)

    if r.status_code == 200:

        return Image.open(
            io.BytesIO(r.content)
        )

    return None

# ─────────────────────────────────────────────
# FONDO DEL DIA
# ─────────────────────────────────────────────

def elegir_fondo_del_dia():

    hoy = datetime.now().strftime("%Y%m%d")

    semilla = int(
        hashlib.md5(
            hoy.encode()
        ).hexdigest(),
        16
    )

    indice = semilla % len(FONDOS)

    return FONDOS[indice]

# ─────────────────────────────────────────────
# IMAGEN DEL DIA
# ─────────────────────────────────────────────

def elegir_imagen_del_dia(lista_archivos):

    hoy = datetime.now().strftime("%Y%m%d")

    semilla = int(
        hashlib.md5(
            (hoy + "mueble").encode()
        ).hexdigest(),
        16
    )

    indice = semilla % len(lista_archivos)

    return lista_archivos[indice]

# ─────────────────────────────────────────────
# COMPOSICION
# ─────────────────────────────────────────────

def componer_pieza(
    fondo_info,
    imagen_mueble,
    titulo
):

    # FORMATO VERTICAL
    W, H = 1080, 1350

    colores = COLORES_POR_FONDO.get(
        fondo_info["tipo"],
        COLORES_POR_FONDO["azul"]
    )

    COLOR_TITULO = colores["titulo"]
    COLOR_CURSIVA = colores["cursiva"]

    # ─────────────────────────
    # FONDO FULL SCREEN
    # ─────────────────────────

    fondo_original = Image.open(
        fondo_info["ruta"]
    ).convert("RGBA")

    ratio = max(
        W / fondo_original.width,
        H / fondo_original.height
    )

    new_size = (
        int(fondo_original.width * ratio),
        int(fondo_original.height * ratio)
    )

    fondo = fondo_original.resize(
        new_size,
        Image.LANCZOS
    )

    left = (fondo.width - W) // 2
    top = (fondo.height - H) // 2

    fondo = fondo.crop((
        left,
        top,
        left + W,
        top + H
    ))

    canvas = Image.new("RGBA", (W, H))

    canvas.paste(fondo, (0,0))

    # ─────────────────────────
    # OVERLAY SUAVE
    # ─────────────────────────

    overlay = Image.new(
        "RGBA",
        (W,H),
        (0,0,0,20)
    )

    canvas.paste(
        overlay,
        (0,0),
        overlay
    )

    # ─────────────────────────
    # MUEBLE
    # ─────────────────────────

    mueble = imagen_mueble.convert("RGBA")

    # RECORTE AUTOMATICO
    bbox = mueble.getbbox()

    if bbox:
        mueble = mueble.crop(bbox)

    ZONA_SUPERIOR = int(H * 0.18)
    ZONA_INFERIOR = int(H * 0.92)

    ZONA_H = (
        ZONA_INFERIOR -
        ZONA_SUPERIOR
    )

    # MÁS GRANDE
    MAX_W = int(W * 0.92)
    MAX_H = int(ZONA_H * 1.15)

    # Ajuste especial según mueble
    if "ROPERO" in titulo:
        MAX_W = int(W * 0.78)

    elif "VELADOR" in titulo:
        MAX_W = int(W * 0.62)

    ratio = min(
        MAX_W / mueble.width,
        MAX_H / mueble.height
    )

    new_w = int(mueble.width * ratio)
    new_h = int(mueble.height * ratio)

    mueble = mueble.resize(
        (new_w, new_h),
        Image.LANCZOS
    )

    mueble_x = (W - new_w) // 2

    mueble_y = (
        ZONA_SUPERIOR +
        (ZONA_H - new_h)//2 +
        40
    )

    # ─────────────────────────
    # HALO DE LUZ
    # ─────────────────────────

    halo_size = int(
        max(new_w, new_h) * 1.15
    )

    halo = Image.new(
        "RGBA",
        (halo_size, halo_size),
        (255,255,255,0)
    )

    halo_draw = ImageDraw.Draw(halo)

    halo_draw.ellipse(
        (0,0,halo_size,halo_size),
        fill=(255,255,255,60)
    )

    halo = halo.filter(
        ImageFilter.GaussianBlur(70)
    )

    halo_x = (
        mueble_x -
        (halo_size - new_w)//2
    )

    halo_y = (
        mueble_y -
        (halo_size - new_h)//2
    )

    canvas.paste(
        halo,
        (halo_x, halo_y),
        halo
    )

    # ─────────────────────────
    # SOMBRA
    # ─────────────────────────

    sombra = Image.new(
        "RGBA",
        mueble.size,
        (0,0,0,110)
    )

    sombra = sombra.filter(
        ImageFilter.GaussianBlur(20)
    )

    canvas.paste(
        sombra,
        (mueble_x + 18, mueble_y + 22),
        sombra
    )

    # ─────────────────────────
    # PEGAR MUEBLE
    # ─────────────────────────

    canvas.paste(
        mueble,
        (mueble_x, mueble_y),
        mueble
    )

    # ─────────────────────────
    # TEXTO
    # ─────────────────────────

    canvas_rgb = canvas.convert("RGB")

    draw = ImageDraw.Draw(canvas_rgb)

    f_tit = ajustar_tamano_fuente(
        titulo,
        FUENTE_TITULO,
        95,
        W - 80
    )

    bbox_t = draw.textbbox(
        (0,0),
        titulo,
        font=f_tit
    )

    tit_w = bbox_t[2] - bbox_t[0]

    tit_x = (W - tit_w)//2
    tit_y = 55

    # CONTORNO
    for ox in range(-2, 3):
        for oy in range(-2, 3):

            draw.text(
                (tit_x + ox, tit_y + oy),
                titulo,
                font=f_tit,
                fill=(0,0,0)
            )

    draw.text(
        (tit_x, tit_y),
        titulo,
        font=f_tit,
        fill=COLOR_TITULO
    )

    # ─────────────────────────
    # CURSIVA
    # ─────────────────────────

    f_cur = cargar_fuente(
        FUENTE_CURSIVA,
        58
    )

    bbox_c = draw.textbbox(
        (0,0),
        "a medida",
        font=f_cur
    )

    cur_w = bbox_c[2] - bbox_c[0]

    cur_x = tit_x + tit_w - cur_w + 8
    cur_y = tit_y + 85

    draw.text(
        (cur_x, cur_y),
        "a medida",
        font=f_cur,
        fill=COLOR_CURSIVA
    )

    # ─────────────────────────
    # GUARDAR
    # ─────────────────────────

    ruta = "post_final.jpg"

    canvas_rgb.save(
        ruta,
        "JPEG",
        quality=97,
        optimize=True,
        subsampling=0
    )

    return ruta

# ─────────────────────────────────────────────
# CAPTION CORTO
# ─────────────────────────────────────────────

def generar_caption(titulo):

    hashtags = (
        "#MueblesMelamina "
        "#MelaminaAMedida "
        "#MueblesLima "
        "#SJL"
    )

    mensajes = {

        "TOCADOR":
        "✨ Tocador moderno en melamina a medida.",

        "ROPERO":
        "🚪 Ropero moderno fabricado a medida.",

        "ESCRITORIO":
        "💻 Escritorio ideal para estudio o home office.",

        "CENTRO DE TV":
        "📺 Centro de TV moderno para tu sala.",

        "CAJONERA":
        "🗄️ Cajonera funcional y elegante.",

        "VELADOR":
        "🛏️ Velador moderno en melamina.",

        "REPOSTERO":
        "🍽️ Repostero práctico y moderno.",
    }

    descripcion = mensajes.get(
        titulo,
        f"✨ {titulo.title()} en melamina a medida."
    )

    return f"""
{descripcion}

✅ Diseño personalizado
✅ Colores a elección
✅ Material resistente

📲 Cotiza por WhatsApp {WHATSAPP_NUMERO}

{hashtags}
""".strip()

# ─────────────────────────────────────────────
# SUBIR GITHUB
# ─────────────────────────────────────────────

def subir_a_github(ruta):

    ts = int(time.time())

    with open(ruta, 'rb') as f:

        content = base64.b64encode(
            f.read()
        ).decode('utf-8')

    url = (
        f"https://api.github.com/repos/"
        f"{GH_REPO}/contents/"
        f"imagenes_publicadas/post_{ts}.jpg"
    )

    headers = {
        "Authorization": f"Bearer {GH_TOKEN}"
    }

    payload = {
        "message": f"Post {ts}",
        "content": content,
        "branch": "main"
    }

    r = requests.put(
        url,
        headers=headers,
        json=payload
    )

    if r.status_code in (200, 201):

        return (
            f"https://raw.githubusercontent.com/"
            f"{GH_REPO}/main/"
            f"imagenes_publicadas/post_{ts}.jpg"
        )

    return None

# ─────────────────────────────────────────────
# FACEBOOK
# ─────────────────────────────────────────────

def publicar_fb(ruta, texto):

    url = (
        f"https://graph.facebook.com/"
        f"v21.0/{FB_PAGE_ID}/photos"
    )

    with open(ruta, 'rb') as f:

        r = requests.post(
            url,
            data={
                'message': texto,
                'access_token': META_TOKEN
            },
            files={'source': f}
        )

    return 'id' in r.json()

# ─────────────────────────────────────────────
# INSTAGRAM
# ─────────────────────────────────────────────

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
        return False

    time.sleep(15)

    r2 = requests.post(

        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish",

        data={
            'creation_id': c_id,
            'access_token': META_TOKEN
        }

    ).json()

    return 'id' in r2

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():

    print("="*60)
    print("🚀 EL CHILENITO MELAMINERO BOT")
    print("="*60)

    fondo_info = elegir_fondo_del_dia()

    archivos = listar_muebles_github()

    if not archivos:
        print("❌ No hay muebles")
        return

    nombre_hoy = elegir_imagen_del_dia(archivos)

    titulo = nombre_a_titulo(nombre_hoy)

    print(f"🪑 {nombre_hoy}")
    print(f"🏷️ {titulo}")

    imagen_mueble = descargar_mueble_github(
        nombre_hoy
    )

    if not imagen_mueble:
        return

    ruta = componer_pieza(
        fondo_info,
        imagen_mueble,
        titulo
    )

    url_publica = subir_a_github(ruta)

    caption = generar_caption(titulo)

    print("\n📘 Publicando Facebook...")
    fb_ok = publicar_fb(ruta, caption)

    print("📸 Publicando Instagram...")
    ig_ok = publicar_ig(
        url_publica,
        caption
    ) if url_publica else False

    print("\n" + "="*60)

    print(
        f"Facebook: {'✅' if fb_ok else '❌'}"
    )

    print(
        f"Instagram: {'✅' if ig_ok else '❌'}"
    )

    print("="*60)

if __name__ == "__main__":
    main()
