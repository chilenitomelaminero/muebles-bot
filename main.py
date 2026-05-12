MUEBLES BOT - Chilenito Melaminero
Sistema con fondo plantilla + PNG sin fondo desde GitHub
- Fondo AZUL → letras BLANCAS
- Fondo BLANCO → letras AZULES
"""

import os
import io
import json
import base64
import requests
import time
import hashlib
import pytz
from datetime import datetime, time as dt_time
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
META_TOKEN   = os.environ.get("META_TOKEN")
FB_PAGE_ID   = os.environ.get("META_PAGE_ID")
IG_USER_ID   = os.environ.get("META_INSTAGRAM_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GH_TOKEN     = os.environ.get("GH_TOKEN")
GH_REPO      = os.environ.get("GITHUB_REPOSITORY", "chilenitomelaminero/muebles-bot")

# FONDOS DISPONIBLES
FONDOS = [
    {"ruta": "plantilla/FD_AZUL.png",         "tipo": "azul"},
    {"ruta": "plantilla/FD_BLANCO.png",        "tipo": "blanco"},
]

RUTA_MUEBLES   = "muebles_sin_fondo"
FUENTE_TITULO  = "fonts/Montserrat-ExtraBold.ttf"
FUENTE_CURSIVA = "fonts/GreatVibes-Regular.ttf"

# COLORES según tipo de fondo
COLORES_POR_FONDO = {
    "azul":         {"titulo": (255, 255, 255), "cursiva": (255, 220, 0),  "sombra": (0, 0, 0)},
    "blanco":       {"titulo": (0, 56, 159),    "cursiva": (0, 56, 159),   "sombra": (200, 200, 200)},
}

WHATSAPP_NUMERO = "+51 903 427 486"

# ─────────────────────────────────────────────
# MAPEO nombres → títulos display
# ─────────────────────────────────────────────
MAPA_TITULOS = {
    "cajonera":                          "CAJONERA",
    "cajonera_2":                        "CAJONERA",
    "cajonera_blanca":                   "CAJONERA",
    "cajonera_con_estante_y_espejo":     "CAJONERA",
    "cajonera_con_una_puerta":           "CAJONERA",
    "cajonera_moderna":                  "CAJONERA",
    "centro_de_tv":                      "CENTRO DE TV",
    "cocina_pequena":                    "COCINA",
    "cojonera_nina":                     "CAJONERA",
    "despensa_multiuso":                 "DESPENSA",
    "despensa_multiuso_2":               "DESPENSA",
    "despensa_multiuso_3":               "DESPENSA",
    "escritorio":                        "ESCRITORIO",
    "estante_oficina":                   "ESTANTE",
    "horno_y_microondas":                "MUEBLE HORNO",
    "librero":                           "LIBRERO",
    "librero_estante":                   "LIBRERO",
    "mesa_centro_melamina":              "MESA DE CENTRO",
    "mesa_de_centro":                    "MESA DE CENTRO",
    "mini_centro_entretenimiento":       "CENTRO TV",
    "mueble_de_bano":                    "AUXILIAR BAÑO",
    "mueble_lavaplatos":                 "MUEBLE COCINA",
    "mueble_cocina":                     "MUEBLE COCINA",
    "mueble_espejo_tocador":             "TOCADOR",
    "mueble_multifuncional":             "MULTIFUNCIONAL",
    "mueble_organizador_multifuncional": "ORGANIZADOR",
    "mueble_repostero_blanco":           "REPOSTERO",
    "organizadores_dormitorio":          "ORGANIZADOR",
    "repisero_repostero":                "REPOSTERO",
    "repisero_tocador":                  "TOCADOR",
    "repisero_tocador_con_espejo":       "TOCADOR",
    "repisero_tocador_moderno":          "TOCADOR",
    "repostero":                         "REPOSTERO",
    "ropero":                            "ROPERO",
    "ropero_2":                          "ROPERO",
    "ropero_moderno_blanco":             "ROPERO",
    "ropero_2_puertas":                  "ROPERO",
    "ropero_3_puertas_y_dos_cajones":    "ROPERO",
    "ropero_bebe":                       "ROPERO BEBÉ",
    "ropero_con_espejo":                 "ROPERO",
    "ropero_con_espejo_y_cajones":       "ROPERO",
    "ropero_con_repisa":                 "ROPERO",
    "ropero_con_repisas_y_cajones":      "ROPERO",
    "ropero_dos_puertas_oscuro":         "ROPERO",
    "ropero_moderno":                    "ROPERO",
    "ropero_organizador":                "ROPERO",
    "ropero_tocador":                    "ROPERO TOCADOR",
    "ropero_tres_puertas":               "ROPERO",
    "velador":                           "VELADOR",
}

# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────
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
        if (bbox[2] - bbox[0]) <= ancho_maximo:
            return fuente, tamano
        tamano -= 5
        fuente = cargar_fuente(ruta_fuente, tamano)
    return fuente, tamano

def nombre_a_titulo(nombre_archivo):
    nombre = os.path.splitext(nombre_archivo)[0].lower()
    nombre = (nombre
        .replace("ñ","n").replace("á","a").replace("é","e")
        .replace("í","i").replace("ó","o").replace("ú","u"))
    if nombre in MAPA_TITULOS:
        return MAPA_TITULOS[nombre]
    return nombre.replace("_", " ").upper()

def elegir_fondo_del_dia():
    """Rota entre los fondos disponibles día a día."""
    hoy = datetime.now().strftime("%Y%m%d")
    semilla = int(hashlib.md5(hoy.encode()).hexdigest(), 16)
    indice = semilla % len(FONDOS)
    fondo = FONDOS[indice]
    print(f"   🎨 Fondo del día: {fondo['ruta']} (tipo: {fondo['tipo']})")
    return fondo

def elegir_imagen_del_dia(lista_archivos):
    """Imagen diferente cada día."""
    hoy = datetime.now().strftime("%Y%m%d")
    # Semilla diferente a la del fondo para que no siempre coincidan igual
    semilla = int(hashlib.md5((hoy + "mueble").encode()).hexdigest(), 16)
    indice = semilla % len(lista_archivos)
    return lista_archivos[indice]

def listar_muebles_github():
    """Lista todos los PNG en muebles_sin_fondo del repo."""
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{RUTA_MUEBLES}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}
    r = requests.get(url, headers=headers).json()
    if isinstance(r, list):
        archivos = [f['name'] for f in r if f['name'].lower().endswith('.png')]
        print(f"   ✅ {len(archivos)} muebles encontrados")
        return archivos
    print(f"   ❌ Error listando: {r}")
    return []

def descargar_mueble_github(nombre_archivo):
    """Descarga imagen PNG del repo."""
    url = f"https://raw.githubusercontent.com/{GH_REPO}/main/{RUTA_MUEBLES}/{nombre_archivo}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return Image.open(io.BytesIO(r.content))
    print(f"   ❌ Error {r.status_code} descargando {nombre_archivo}")
    return None

# ─────────────────────────────────────────────
# COMPOSICIÓN GRÁFICA (MODIFICADA SEGÚN TUS INDICACIONES)
# ─────────────────────────────────────────────
def componer_pieza(fondo_info, imagen_mueble, titulo):
    W, H = 1080, 1080

    # Colores según tipo de fondo
    colores = COLORES_POR_FONDO.get(fondo_info["tipo"], COLORES_POR_FONDO["azul"])
    COLOR_TITULO  = colores["titulo"]
    COLOR_CURSIVA = colores["cursiva"]
    COLOR_SOMBRA  = colores["sombra"]

    # 1. Cargar fondo (SIN CAMBIOS, se mantiene tal cual)
    print("   🖼️  Cargando fondo...")
    fondo = Image.open(fondo_info["ruta"]).convert("RGBA").resize((W, H), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H))
    canvas.paste(fondo, (0, 0))

    # 2. Imagen PNG del mueble → AJUSTADA PARA NO TAPAR LOGO NI WHATSAPP
    print("   🪑 Posicionando mueble...")
    mueble = imagen_mueble.convert("RGBA")
    ancho_original, alto_original = mueble.size
    proporcion = ancho_original / alto_original  # >1 = ancha ; <1 = alta

    # 📏 ZONAS DEFINIDAS (LÍMITES QUE NO SE PUEDEN PASAR)
    ZONA_SUPERIOR = int(H * 0.18)   # Espacio para título arriba
    ZONA_INFERIOR = int(H * 0.82)   # 🚫 LÍMITE: hasta aquí llega el mueble (abajo queda 18% libre para logo y WhatsApp)
    ZONA_ALTO_DISPONIBLE = ZONA_INFERIOR - ZONA_SUPERIOR
    ZONA_ANCHO_DISPONIBLE = W

    # 📏 Ajuste de tamaño SEGÚN PROPORCIÓN de la imagen
    if 0.7 <= proporcion <= 1.4:
        # Imagen casi cuadrada → tamaño normal
        MAX_W = int(ZONA_ANCHO_DISPONIBLE * 0.97)
        MAX_H = int(ZONA_ALTO_DISPONIBLE * 0.97)
    elif proporcion < 0.7:
        # Imagen MUY ALTA → reducimos ancho para que no se pase abajo
        MAX_W = int(ZONA_ANCHO_DISPONIBLE * 0.72)
        MAX_H = int(ZONA_ALTO_DISPONIBLE * 0.92)
    else:
        # Imagen MUY ANCHA → reducimos alto para que no se pase abajo
        MAX_W = int(ZONA_ANCHO_DISPONIBLE * 0.97)
        MAX_H = int(ZONA_ALTO_DISPONIBLE * 0.72)

    # Escalar manteniendo proporción perfecta (NUNCA SE DEFORMA)
    ratio = min(MAX_W / ancho_original, MAX_H / alto_original)
    new_w = int(ancho_original * ratio)
    new_h = int(alto_original * ratio)
    mueble = mueble.resize((new_w, new_h), Image.LANCZOS)

    # Centrado DENTRO de los límites
    mueble_x = (W - new_w) // 2
    mueble_y = ZONA_SUPERIOR + (ZONA_ALTO_DISPONIBLE - new_h) // 2

    # 🛡️ SEGURIDAD EXTRA: si por cálculo se pasa, lo ajustamos
    if mueble_y + new_h > ZONA_INFERIOR:
        mueble_y = ZONA_INFERIOR - new_h

    canvas.paste(mueble, (mueble_x, mueble_y), mueble)

    # Convertir a RGB para dibujar texto
    canvas_rgb = canvas.convert("RGB")
    draw = ImageDraw.Draw(canvas_rgb)

    # 3. Título grande centrado arriba (SIN CAMBIOS)
    print(f"   ✍️  Título: {titulo} | Color: {COLOR_TITULO}")
    f_tit, tit_size = ajustar_tamano_fuente(titulo, FUENTE_TITULO, 120, W - 60)
    bbox_t = draw.textbbox((0, 0), titulo, font=f_tit)
    tit_w  = bbox_t[2] - bbox_t[0]
    tit_h  = bbox_t[3] - bbox_t[1]
    tit_x  = (W - tit_w) // 2
    tit_y  = 20

    # Sombra y texto del título
    draw.text((tit_x + 3, tit_y + 3), titulo, font=f_tit, fill=COLOR_SOMBRA)
    draw.text((tit_x, tit_y), titulo, font=f_tit, fill=COLOR_TITULO)

    # 4. Cursiva "a medida" (SIN CAMBIOS)
    f_cur = cargar_fuente(FUENTE_CURSIVA, 85)
    bbox_c = draw.textbbox((0, 0), "a medida", font=f_cur)
    cur_w = bbox_c[2] - bbox_c[0]
    cur_x = tit_x + tit_w - cur_w + 10
    cur_y = tit_y + tit_h + 5

    # Sombra y texto cursiva
    draw.text((cur_x + 2, cur_y + 2), "a medida", font=f_cur, fill=COLOR_SOMBRA)
    draw.text((cur_x, cur_y), "a medida", font=f_cur, fill=COLOR_CURSIVA)

    # Guardar imagen final
    ruta = "post_final.jpg"
    canvas_rgb.save(ruta, "JPEG", quality=97, subsampling=0)
    print("   ✅ Pieza guardada")
    return ruta

# ─────────────────────────────────────────────
# GITHUB — subir imagen publicada
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
        return f"https://raw.githubusercontent.com/{GH_REPO}/main/imagenes_public
