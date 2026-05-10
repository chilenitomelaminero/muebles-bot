import os
import io
import json
import base64
import requests
import time
import hashlib
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
META_TOKEN   = os.environ.get("META_TOKEN")
FB_PAGE_ID   = os.environ.get("META_PAGE_ID")
IG_USER_ID   = os.environ.get("META_INSTAGRAM_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GH_TOKEN     = os.environ.get("GH_TOKEN")
GH_REPO      = os.environ.get("GITHUB_REPOSITORY", "chilenitomelaminero/muebles-bot")

FONDOS = [
    {"ruta": "plantilla/FD_AZUL.png",         "tipo": "azul"},
    {"ruta": "plantilla/FD_BLANCO.png",        "tipo": "blanco"},
    {"ruta": "plantilla/FD_TRANPARENTE.png",   "tipo": "transparente"},
]

RUTA_MUEBLES   = "muebles_sin_fondo"
FUENTE_TITULO  = "fonts/Montserrat-ExtraBold.ttf"
FUENTE_CURSIVA = "fonts/GreatVibes-Regular.ttf"

COLORES_POR_FONDO = {
    "azul":         {"titulo": (255, 255, 255), "cursiva": (255, 220, 0),  "sombra": (0, 0, 0)},
    "blanco":       {"titulo": (0, 56, 159),    "cursiva": (0, 56, 159),   "sombra": (200, 200, 200)},
    "transparente": {"titulo": (255, 255, 255), "cursiva": (255, 220, 0),  "sombra": (0, 0, 0)},
}

WHATSAPP_NUMERO = "+51 903 427 486"

MAPA_TITULOS = {
    "cajonera": "CAJONERA", "cajonera_2": "CAJONERA", "cajonera_blanca": "CAJONERA",
    "cajonera_con_estante_y_espejo": "CAJONERA", "cajonera_con_una_puerta": "CAJONERA",
    "cajonera_moderna": "CAJONERA", "centro_de_tv": "CENTRO DE TV",
    "cocina_pequena": "COCINA", "cojonera_nina": "CAJONERA",
    "despensa_multiuso": "DESPENSA", "despensa_multiuso_2": "DESPENSA",
    "despensa_multiuso_3": "DESPENSA", "escritorio": "ESCRITORIO",
    "estante_oficina": "ESTANTE", "horno_y_microondas": "MUEBLE HORNO",
    "librero": "LIBRERO", "librero_estante": "LIBRERO",
    "mesa_centro_melamina": "MESA DE CENTRO", "mesa_de_centro": "MESA DE CENTRO",
    "mini_centro_entretenimiento": "CENTRO TV", "mueble_de_bano": "AUXILIAR BAÑO",
    "mueble_lavaplatos": "MUEBLE COCINA", "mueble_cocina": "MUEBLE COCINA",
    "mueble_espejo_tocador": "TOCADOR", "mueble_multifuncional": "MULTIFUNCIONAL",
    "mueble_organizador_multifuncional": "ORGANIZADOR", "mueble_repostero_blanco": "REPOSTERO",
    "organizadores_dormitorio": "ORGANIZADOR", "repisero_repostero": "REPOSTERO",
    "repisero_tocador": "TOCADOR", "repisero_tocador_con_espejo": "TOCADOR",
    "repisero_tocador_moderno": "TOCADOR", "repostero": "REPOSTERO",
    "ropero": "ROPERO", "ropero_2": "ROPERO", "ropero_moderno_blanco": "ROPERO",
    "ropero_2_puertas": "ROPERO", "ropero_3_puertas_y_dos_cajones": "ROPERO",
    "ropero_bebe": "ROPERO BEBÉ", "ropero_con_espejo": "ROPERO",
    "ropero_con_espejo_y_cajones": "ROPERO", "ropero_con_repisa": "ROPERO",
    "ropero_con_repisas_y_cajones": "ROPERO", "ropero_dos_puertas_oscuro": "ROPERO",
    "ropero_moderno": "ROPERO", "ropero_organizador": "ROPERO",
    "ropero_tocador": "ROPERO TOCADOR", "ropero_tres_puertas": "ROPERO",
    "velador": "VELADOR",
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

def obtener_ambiente(titulo):
    t = titulo.upper()
    if any(x in t for x in ["COCINA", "REPOSTERO", "HORNO", "DESPENSA", "LAVAPLATOS"]):
        return "tu cocina"
    if any(x in t for x in ["ROPERO", "TOCADOR", "VELADOR", "CAJONERA", "DORMITORIO"]):
        return "tu dormitorio"
    if any(x in t for x in ["TV", "CENTRO", "SALA", "MESA DE CENTRO"]):
        return "tu sala"
    if "BAÑO" in t:
        return "tu baño"
    if any(x in t for x in ["ESCRITORIO", "ESTANTE", "LIBRERO", "OFICINA"]):
        return "tu oficina o estudio"
    return "tu hogar"

def nombre_a_titulo(nombre_archivo):
    nombre = os.path.splitext(nombre_archivo)[0].lower()
    nombre = (nombre.replace("ñ","n").replace("á","a").replace("é","e")
              .replace("í","i").replace("ó","o").replace("ú","u"))
    if nombre in MAPA_TITULOS:
        return MAPA_TITULOS[nombre]
    return nombre.replace("_", " ").upper()

def elegir_fondo_del_dia():
    hoy = datetime.now().strftime("%Y%m%d")
    semilla = int(hashlib.md5(hoy.encode()).hexdigest(), 16)
    indice = semilla % len(FONDOS)
    return FONDOS[indice]

def elegir_imagen_del_dia(lista_archivos):
    hoy = datetime.now().strftime("%Y%m%d")
    semilla = int(hashlib.md5((hoy + "mueble").encode()).hexdigest(), 16)
    indice = semilla % len(lista_archivos)
    return lista_archivos[indice]

def listar_muebles_github():
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{RUTA_MUEBLES}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}
    r = requests.get(url, headers=headers).json()
    if isinstance(r, list):
        return [f['name'] for f in r if f['name'].lower().endswith('.png')]
    return []

def descargar_mueble_github(nombre_archivo):
    url = f"https://raw.githubusercontent.com/{GH_REPO}/main/{RUTA_MUEBLES}/{nombre_archivo}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return Image.open(io.BytesIO(r.content))
    return None

# ─────────────────────────────────────────────
# COMPOSICIÓN GRÁFICA
# ─────────────────────────────────────────────
def componer_pieza(fondo_info, imagen_mueble, titulo):
    W, H = 1080, 1080
    colores = COLORES_POR_FONDO.get(fondo_info["tipo"], COLORES_POR_FONDO["azul"])
    COLOR_TITULO, COLOR_CURSIVA, COLOR_SOMBRA = colores["titulo"], colores["cursiva"], colores["sombra"]

    fondo = Image.open(fondo_info["ruta"]).convert("RGBA").resize((W, H), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H))
    canvas.paste(fondo, (0, 0))

    mueble = imagen_mueble.convert("RGBA")
    Z_SUP, Z_INF = int(H * 0.22), int(H * 0.82)
    Z_H = Z_INF - Z_SUP

    ratio = min((W * 0.75) / mueble.width, (Z_H * 0.92) / mueble.height)
    nw, nh = int(mueble.width * ratio), int(mueble.height * ratio)
    mueble = mueble.resize((nw, nh), Image.LANCZOS)
    canvas.paste(mueble, ((W - nw) // 2, Z_SUP + (Z_H - nh) // 2), mueble)

    canvas_rgb = canvas.convert("RGB")
    draw = ImageDraw.Draw(canvas_rgb)

    f_tit, _ = ajustar_tamano_fuente(titulo, FUENTE_TITULO, 115, W - 100)
    bbox_t = draw.textbbox((0, 0), titulo, font=f_tit)
    tw, th = bbox_t[2] - bbox_t[0], bbox_t[3] - bbox_t[1]
    tx, ty = (W - tw) // 2, 45

    draw.text((tx + 3, ty + 3), titulo, font=f_tit, fill=COLOR_SOMBRA)
    draw.text((tx, ty), titulo, font=f_tit, fill=COLOR_TITULO)

    f_cur = cargar_fuente(FUENTE_CURSIVA, 90)
    cw = draw.textbbox((0, 0), "a medida", font=f_cur)[2]
    cx = min(tx + tw - (cw // 2), W - cw - 40)
    draw.text((cx + 2, ty + th - 8), "a medida", font=f_cur, fill=COLOR_SOMBRA)
    draw.text((cx, ty + th - 10), "a medida", font=f_cur, fill=COLOR_CURSIVA)

    ruta = "post_final.jpg"
    canvas_rgb.save(ruta, "JPEG", quality=98, subsampling=0)
    return ruta

# ─────────────────────────────────────────────
# GITHUB Y CAPTION
# ─────────────────────────────────────────────
def subir_a_github(ruta):
    ts = int(time.time())
    with open(ruta, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')
    url = f"https://api.github.com/repos/{GH_REPO}/contents/imagenes_publicadas/post_{ts}.jpg"
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}
    payload = {"message": f"Post {ts}", "content": content, "branch": "main"}
    r = requests.put(url, headers=headers, json=payload)
    return f"https://raw.githubusercontent.com/{GH_REPO}/main/imagenes_publicadas/post_{ts}.jpg" if r.status_code in (200,201) else None

def generar_caption(titulo, nombre_archivo):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ambiente = obtener_ambiente(titulo)
    hashtags = f"#{titulo.title().replace(' ','')} #MueblesMelamina #SJL #Lima #ElChilenitoMelaminero"

    prompt = (
        f"Eres el community manager de 'El Chilenito Melaminero' en SJL, Lima.\n"
        f"Escribe un post para un {titulo} a medida ideal para {ambiente}.\n\n"
        f"ESTRUCTURA:\n1. Frase gancho sobre {ambiente}.\n2. Beneficio del {titulo}.\n"
        f"3. Escribe EXACTAMENTE: 'En El Chilenito Melaminero creamos soluciones que combinan orden, diseño y buen precio 🏡'\n"
        f"4. 6 Características con ✅ (Incluye Diseño a medida, SJL y Lima).\n"
        f"5. Escribe EXACTAMENTE: '📲 Cotiza por WhatsApp {WHATSAPP_NUMERO} y recibe asesoría personalizada'\n"
        f"6. Hashtags: {hashtags}\n\n"
        f"IMPORTANTE: No menciones el baño a menos que el mueble sea de baño."
    )

    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
    r = requests.post(url, headers=headers, json=payload).json()
    return r['choices'][0]['message']['content']

# ─────────────────────────────────────────────
# PUBLICACIÓN Y MAIN
# ─────────────────────────────────────────────
def publicar_fb(ruta, texto):
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    with open(ruta, 'rb') as f:
        r = requests.post(url, data={'message': texto, 'access_token': META_TOKEN}, files={'source': f})
    return 'id' in r.json()

def publicar_ig(url_img, texto):
    r1 = requests.post(f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media", data={'image_url': url_img, 'caption': texto, 'access_token': META_TOKEN}).json()
    c_id = r1.get('id')
    if not c_id: return False
    time.sleep(15)
    r2 = requests.post(f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish", data={'creation_id': c_id, 'access_token': META_TOKEN}).json()
    return 'id' in r2

def main():
    try:
        fondo_info = elegir_fondo_del_dia()
        archivos = listar_muebles_github()
        if not archivos: return
        nombre_hoy = elegir_imagen_del_dia(archivos)
        titulo = nombre_a_titulo(nombre_hoy)
        img_mueble = descargar_mueble_github(nombre_hoy)
        if not img_mueble: return
        
        ruta = componer_pieza(fondo_info, img_mueble, titulo)
        url_p = subir_a_github(ruta)
        caption = generar_caption(titulo, nombre_hoy)
        
        publicar_fb(ruta, caption)
        if url_p: publicar_ig(url_p, caption)
        print(f"✅ Post finalizado: {titulo}")
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    main()
