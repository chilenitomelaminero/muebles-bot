"""
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
# COMPOSICIÓN GRÁFICA
# ─────────────────────────────────────────────
def componer_pieza(fondo_info, imagen_mueble, titulo):
    W, H = 1080, 1080

    # Colores según tipo de fondo
    colores = COLORES_POR_FONDO.get(fondo_info["tipo"], COLORES_POR_FONDO["azul"])
    COLOR_TITULO  = colores["titulo"]
    COLOR_CURSIVA = colores["cursiva"]
    COLOR_SOMBRA  = colores["sombra"]

    # 1. Cargar fondo
    print("   🖼️  Cargando fondo...")
    fondo = Image.open(fondo_info["ruta"]).convert("RGBA").resize((W, H), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H))
    canvas.paste(fondo, (0, 0))

    # 2. Imagen mueble — GRANDE (70% del canvas)
    print("   🪑 Posicionando mueble...")
    mueble = imagen_mueble.convert("RGBA")

    # Zona disponible: entre el área del título (arriba) y el WhatsApp/logo (abajo)
    ZONA_SUPERIOR = int(H * 0.18)   # espacio para título arriba
    ZONA_INFERIOR = H    # hasta el borde completo (logo está en el fondo)
    ZONA_H = ZONA_INFERIOR - ZONA_SUPERIOR

    # Escalar al 91% del ancho o alto disponible (+30% respecto al original)
    MAX_W = int(W * 0.97)           # 91% del ancho  (era 70%)
    MAX_H = int(ZONA_H * 0.99)      # 98% de la zona disponible (era 95%)
    ratio = min(MAX_W / mueble.width, MAX_H / mueble.height)
    new_w = int(mueble.width * ratio)
    new_h = int(mueble.height * ratio)
    mueble = mueble.resize((new_w, new_h), Image.LANCZOS)

    # Centrar en la zona disponible
    mueble_x = (W - new_w) // 2
    mueble_y = ZONA_SUPERIOR + (ZONA_H - new_h) // 2
    canvas.paste(mueble, (mueble_x, mueble_y), mueble)

    # Convertir a RGB para texto
    canvas_rgb = canvas.convert("RGB")
    draw = ImageDraw.Draw(canvas_rgb)

    # 3. Título grande centrado arriba
    print(f"   ✍️  Título: {titulo} | Color: {COLOR_TITULO}")
    f_tit, tit_size = ajustar_tamano_fuente(titulo, FUENTE_TITULO, 120, W - 60)
    bbox_t = draw.textbbox((0, 0), titulo, font=f_tit)
    tit_w  = bbox_t[2] - bbox_t[0]
    tit_h  = bbox_t[3] - bbox_t[1]
    tit_x  = (W - tit_w) // 2
    tit_y  = 20

    # Sombra
    draw.text((tit_x + 3, tit_y + 3), titulo, font=f_tit, fill=COLOR_SOMBRA)
    # Texto principal
    draw.text((tit_x, tit_y), titulo, font=f_tit, fill=COLOR_TITULO)

    # 4. Cursiva "a medida" — alineada a la derecha del título
    f_cur = cargar_fuente(FUENTE_CURSIVA, 85)
    bbox_c = draw.textbbox((0, 0), "a medida", font=f_cur)
    cur_w = bbox_c[2] - bbox_c[0]
    cur_x = tit_x + tit_w - cur_w + 10
    cur_y = tit_y + tit_h + 5

    # Sombra cursiva
    draw.text((cur_x + 2, cur_y + 2), "a medida", font=f_cur, fill=COLOR_SOMBRA)
    # Cursiva
    draw.text((cur_x, cur_y), "a medida", font=f_cur, fill=COLOR_CURSIVA)

    # Guardar
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
        return f"https://raw.githubusercontent.com/{GH_REPO}/main/imagenes_publicadas/post_{ts}.jpg"
    print(f"⚠️  GitHub upload falló: {r.status_code}")
    return None

# ─────────────────────────────────────────────
# CAPTION
# ─────────────────────────────────────────────
def generar_caption(titulo, nombre_archivo):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

    titulo_limpio  = titulo.title().replace(" ", "")
    keyword_seo    = f"{titulo.title()} a medida Lima"   # keyword principal SEO

    hashtags = (
        f"#{titulo_limpio} #{titulo_limpio}AMedida "
        f"#MueblesMelamina #MelaminaAMedida #MueblesSJL #MueblesLima "
        f"#ElChilenitoMelaminero #OrganizacionHogar"
    )

    prompt = (
        f"Eres el community manager de 'El Chilenito Melaminero', mueblista en SJL, Lima Perú. "
        f"Escribe un post CORTO para Facebook e Instagram.\n\n"
        f"REGLAS SEO:\n"
        f"- La PRIMERA línea debe contener exactamente la keyword: '{keyword_seo}'\n"
        f"- Úsala de forma natural, no forzada.\n\n"
        f"ESTRUCTURA (respeta el orden, sin corchetes en la respuesta):\n"
        f"1. Frase gancho que incluya '{keyword_seo}'.\n"
        f"2. Máximo 3 características con emoji ✅ (las más relevantes del {titulo}).\n"
        f"3. CTA exacto: '📲 Cotiza por WhatsApp {WHATSAPP_NUMERO}'\n"
        f"4. Hashtags: {hashtags}\n\n"
        f"Máximo 180 palabras. Español peruano natural. Solo el texto, sin explicaciones."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 400
    }

    r = requests.post(url, headers=headers, json=payload).json()
    caption = r['choices'][0]['message']['content']
    print(f"   ✅ Caption: {len(caption)} caracteres")
    return caption

# ─────────────────────────────────────────────
# PUBLICACIÓN META
# ─────────────────────────────────────────────
def publicar_fb(ruta, texto):
    print(f"\n   🔍 DEBUG Facebook:")
    print(f"      FB_PAGE_ID: {FB_PAGE_ID[:10]}..." if FB_PAGE_ID else "      FB_PAGE_ID: NO CONFIGURADO")
    print(f"      META_TOKEN: {'✅ Presente' if META_TOKEN else '❌ NO ENCONTRADO'}")
    
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    print(f"      URL: {url}")
    
    try:
        with open(ruta, 'rb') as f:
            r = requests.post(url,
                data={'message': texto, 'access_token': META_TOKEN},
                files={'source': f})
        
        print(f"      Status: {r.status_code}")
        response_json = r.json()
        print(f"      Response: {response_json}")
        
        ok = 'id' in response_json
        if ok:
            print(f"      ✅ Post ID: {response_json.get('id')}")
        else:
            print(f"      ❌ Error: {response_json.get('error', 'Desconocido')}")
        return ok
    except Exception as e:
        print(f"      💥 Exception: {str(e)}")
        return False

def publicar_ig(url_imagen, texto):
    print(f"\n   🔍 DEBUG Instagram:")
    print(f"      IG_USER_ID: {IG_USER_ID[:10]}..." if IG_USER_ID else "      IG_USER_ID: NO CONFIGURADO")
    print(f"      META_TOKEN: {'✅ Presente' if META_TOKEN else '❌ NO ENCONTRADO'}")
    print(f"      Image URL: {url_imagen[:50]}..." if url_imagen else "      Image URL: NO DISPONIBLE")
    
    try:
        print(f"\n      📤 Creando contenedor de media...")
        r1 = requests.post(
            f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media",
            data={'image_url': url_imagen, 'caption': texto, 'access_token': META_TOKEN}
        ).json()
        
        print(f"      Response: {r1}")
        c_id = r1.get('id')
        
        if not c_id:
            print(f"      ❌ Error creando contenedor: {r1.get('error', 'Desconocido')}")
            return False
        
        print(f"      ✅ Container ID: {c_id}")
        print(f"\n      ⏳ Esperando 15 segundos antes de publicar...")
        time.sleep(15)
        
        print(f"      📤 Publicando media...")
        r2 = requests.post(
            f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish",
            data={'creation_id': c_id, 'access_token': META_TOKEN}
        ).json()
        
        print(f"      Response: {r2}")
        ok = 'id' in r2
        
        if ok:
            print(f"      ✅ Post ID: {r2.get('id')}")
        else:
            print(f"      ❌ Error publicando: {r2.get('error', 'Desconocido')}")
        
        return ok
    except Exception as e:
        print(f"      💥 Exception: {str(e)}")
        return False

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 70)
    print("  🚀 MUEBLES BOT - Chilenito Melaminero")
    print("=" * 70)

    # ─────── DEBUG ZONA HORARIA ───────
    utc_tz = pytz.timezone('UTC')
    lima_tz = pytz.timezone('America/Lima')
    
    utc_now = datetime.now(utc_tz)
    lima_now = datetime.now(lima_tz)
    
    print(f"\n⏰ VERIFICACIÓN DE HORA:")
    print(f"   🌍 UTC:  {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   🇵🇪 Lima: {lima_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Control de horario: solo se salta si está en cronjob automático
    es_automatico = os.environ.get("GITHUB_EVENT_NAME") == "schedule"
    
    if es_automatico and lima_now.hour != 9:
        print(f"\n⏭️  SALTANDO - NO ES LA HORA AUTOMÁTICA")
        print(f"   Hora actual: {lima_now.strftime('%H:%M')}")
        print(f"   Horario automático: 09:00-09:59 AM Lima")
        print(f"   Próxima ejecución: mañana a las 9:00 AM")
        return
    
    if not es_automatico:
        print(f"\n✅ EJECUCIÓN MANUAL - Procediendo (ignorando horario automático)")
    else:
        print(f"\n✅ HORA CORRECTA - Procediendo con publicación")

    try:
        # 1. Elegir fondo del día
        print("\n🎨 Eligiendo fondo del día...")
        fondo_info = elegir_fondo_del_dia()

        # 2. Listar y elegir mueble del día
        print("\n📂 Listando muebles...")
        archivos = listar_muebles_github()
        if not archivos:
            print("❌ No hay imágenes en muebles_sin_fondo")
            return

        nombre_hoy = elegir_imagen_del_dia(archivos)
        titulo = nombre_a_titulo(nombre_hoy)
        print(f"\n📅 Mueble del día: {nombre_hoy}")
        print(f"   🏷️  Título: {titulo}")

        # 3. Descargar imagen
        print(f"\n⬇️  Descargando {nombre_hoy}...")
        imagen_mueble = descargar_mueble_github(nombre_hoy)
        if not imagen_mueble:
            return
        print("   ✅ Descargada")

        # 4. Componer
        print("\n🎨 Componiendo pieza gráfica...")
        ruta = componer_pieza(fondo_info, imagen_mueble, titulo)

        # 5. Subir a GitHub
        print("\n📤 Subiendo a GitHub...")
        url_p = subir_a_github(ruta)

        # 6. Caption
        print("\n✍️  Generando caption...")
        caption = generar_caption(titulo, nombre_hoy)

        # 7. Publicar
        print("\n📘 Publicando en Facebook...")
        f_ok = publicar_fb(ruta, caption)

        print("\n📸 Publicando en Instagram...")
        i_ok = publicar_ig(url_p, caption) if url_p else False

        print(f"\n{'='*70}")
        print(f"  ✅ Facebook:  {'✅ PUBLICADO' if f_ok else '❌ FALLÓ'}")
        print(f"  ✅ Instagram: {'✅ PUBLICADO' if i_ok else '❌ FALLÓ'}")
        print(f"  📦 Mueble:    {nombre_hoy}")
        print(f"  🏷️  Título:    {titulo}")
        print(f"  🎨 Fondo:     {fondo_info['tipo']}")
        print(f"{'='*70}")

    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
