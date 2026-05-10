"""
MUEBLES BOT - Chilenito Melaminero
Sistema con fondo plantilla + PNG sin fondo desde GitHub
- Fondo AZUL → letras BLANCAS
- Fondo BLANCO → letras AZULES
- Imagen mueble grande (91% del canvas)
- Rotación automática de imágenes sin repetir
"""

import os
import io
import json
import base64
import random
import requests
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
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
    {"ruta": "plantilla/FD_AZUL.png",   "tipo": "azul"},
    {"ruta": "plantilla/FD_BLANCO.png", "tipo": "blanco"},
]

RUTA_MUEBLES   = "muebles_sin_fondo"
RUTA_REGISTRO  = "publicados.json"
FUENTE_TITULO  = "fonts/Montserrat-ExtraBold.ttf"
FUENTE_CURSIVA = "fonts/GreatVibes-Regular.ttf"

# COLORES según tipo de fondo
COLORES_POR_FONDO = {
    "azul":   {"titulo": (255, 255, 255), "cursiva": (255, 220, 0), "sombra": (0, 0, 0)},
    "blanco": {"titulo": (0, 56, 159),    "cursiva": (0, 56, 159),  "sombra": (200, 200, 200)},
    # (0, 56, 159) = #00389F — azul corporativo para fondo blanco
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
# CONTEXTO DE AMBIENTE por título de mueble
# ─────────────────────────────────────────────
CONTEXTO_MUEBLE = {
    "CAJONERA":         "dormitorio",
    "TOCADOR":          "dormitorio",
    "ROPERO":           "dormitorio",
    "ROPERO BEBÉ":      "habitación de bebé",
    "ROPERO TOCADOR":   "dormitorio",
    "VELADOR":          "dormitorio",
    "ORGANIZADOR":      "dormitorio",
    "ESCRITORIO":       "oficina o estudio",
    "ESTANTE":          "oficina o sala",
    "LIBRERO":          "sala o estudio",
    "COCINA":           "cocina",
    "MUEBLE COCINA":    "cocina",
    "REPOSTERO":        "cocina",
    "DESPENSA":         "cocina",
    "MUEBLE HORNO":     "cocina",
    "AUXILIAR BAÑO":    "baño",
    "CENTRO DE TV":     "sala de estar",
    "CENTRO TV":        "sala de estar",
    "MESA DE CENTRO":   "sala de estar",
    "MULTIFUNCIONAL":   "hogar",
}

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
            return fuente, tamano
        tamano -= 5
        fuente = cargar_fuente(ruta_fuente, tamano)
    return fuente, tamano

def nombre_a_titulo(nombre_archivo):
    nombre = os.path.splitext(nombre_archivo)[0].lower()
    nombre = (nombre
        .replace("ñ", "n").replace("á", "a").replace("é", "e")
        .replace("í", "i").replace("ó", "o").replace("ú", "u"))
    if nombre in MAPA_TITULOS:
        return MAPA_TITULOS[nombre]
    return nombre.replace("_", " ").upper()

def elegir_fondo_del_dia():
    """Rota entre los fondos disponibles aleatoriamente."""
    fondo = random.choice(FONDOS)
    print(f"   🎨 Fondo elegido: {fondo['ruta']} (tipo: {fondo['tipo']})")
    return fondo

# ─────────────────────────────────────────────
# GITHUB — listar y descargar muebles
# ─────────────────────────────────────────────
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
# REGISTRO DE IMÁGENES YA PUBLICADAS
# ─────────────────────────────────────────────
def cargar_registro_github():
    """Lee el JSON de imágenes ya publicadas desde el repo."""
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{RUTA_REGISTRO}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}
    r = requests.get(url, headers=headers).json()

    if "content" in r:
        contenido = base64.b64decode(r["content"]).decode("utf-8")
        datos = json.loads(contenido)
        sha = r["sha"]
        print(f"   📋 Registro cargado: {len(datos['publicados'])} publicadas")
        return datos["publicados"], sha

    # Si no existe el archivo todavía, empezamos desde cero
    print("   📋 Sin registro previo, comenzando desde cero")
    return [], None

def guardar_registro_github(lista_publicados, sha=None):
    """Guarda el JSON actualizado en el repo."""
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{RUTA_REGISTRO}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}

    contenido = json.dumps({"publicados": lista_publicados}, indent=2, ensure_ascii=False)
    payload = {
        "message": f"Registro actualizado — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": base64.b64encode(contenido.encode("utf-8")).decode("utf-8"),
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha  # requerido para actualizar archivo existente

    r = requests.put(url, headers=headers, json=payload)
    ok = r.status_code in (200, 201)
    print(f"   {'✅' if ok else '❌'} Registro guardado ({len(lista_publicados)} entradas)")
    return ok

def elegir_imagen_nueva(lista_archivos):
    """
    Elige una imagen que NO se haya publicado aún.
    Si todas fueron publicadas, resetea el registro y empieza de nuevo.
    Devuelve: (nombre_archivo, lista_actualizada, sha)
    """
    publicados, sha = cargar_registro_github()

    # Filtrar las que todavía no se han usado
    pendientes = [f for f in lista_archivos if f not in publicados]

    if not pendientes:
        print("   🔄 Todas las imágenes fueron publicadas. Reseteando registro...")
        publicados = []
        sha = None
        pendientes = list(lista_archivos)

    # Elegir aleatoriamente entre las pendientes
    elegida = random.choice(pendientes)
    publicados.append(elegida)

    print(f"   🎲 Imagen elegida: {elegida}")
    print(f"   📊 Pendientes restantes: {len(pendientes) - 1} / {len(lista_archivos)}")

    return elegida, publicados, sha

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

    # 2. Imagen mueble — GRANDE (91% del canvas)
    print("   🪑 Posicionando mueble...")
    mueble = imagen_mueble.convert("RGBA")

    ZONA_SUPERIOR = int(H * 0.20)   # espacio para título arriba
    ZONA_INFERIOR = int(H * 0.83)   # límite antes del WhatsApp/logo
    ZONA_H = ZONA_INFERIOR - ZONA_SUPERIOR

    MAX_W = int(W * 0.91)           # 91% del ancho (30% más grande que antes)
    MAX_H = int(ZONA_H * 0.98)      # aprovecha casi toda la zona disponible
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

    # 3. Título grande centrado — un poco más abajo
    print(f"   ✍️  Título: {titulo} | Color: {COLOR_TITULO}")
    f_tit, tit_size = ajustar_tamano_fuente(titulo, FUENTE_TITULO, 120, W - 60)
    bbox_t = draw.textbbox((0, 0), titulo, font=f_tit)
    tit_w  = bbox_t[2] - bbox_t[0]
    tit_h  = bbox_t[3] - bbox_t[1]
    tit_x  = (W - tit_w) // 2
    tit_y  = 55                     # bajado respecto al original (era 20)

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

    titulo_limpio = titulo.title().replace(" ", "")
    hashtags = (
        f"#{titulo_limpio} #{titulo_limpio}AMedida "
        f"#MueblesMelamina #MelaminaAMedida #MueblesSJL #MueblesLima "
        f"#ElChilenitoMelaminero #OrganizacionHogar"
    )

    # Ambiente correcto para este mueble
    ambiente = CONTEXTO_MUEBLE.get(titulo, "hogar")

    # Característica interna específica según tipo de mueble
    CARACTERISTICA_INTERNA = {
        "ROPERO":           "Distribución interna funcional (colgado, cajones, repisas) 👚",
        "ROPERO BEBÉ":      "Distribución interna adaptada para ropa de bebé 🍼",
        "ROPERO TOCADOR":   "Espejo integrado y cajones organizadores 🪞",
        "CAJONERA":         "Cajones amplios y deslizantes de fácil acceso 🗄️",
        "TOCADOR":          "Espejo y compartimentos organizadores incluidos 💄",
        "VELADOR":          "Cajón y repisa lateral para mayor funcionalidad 🌙",
        "ESCRITORIO":       "Superficie amplia y cajones para organizar tus materiales 📚",
        "ESTANTE":          "Repisas regulables según tus necesidades 📂",
        "LIBRERO":          "Repisas a medida para todo tipo de libros 📖",
        "COCINA":           "Muebles diseñados para maximizar el espacio 🍳",
        "MUEBLE COCINA":    "Cajones y puertas con cierre suave 🍽️",
        "REPOSTERO":        "Repisas internas regulables para mayor almacenamiento 🧺",
        "DESPENSA":         "Múltiples compartimentos para mantener todo ordenado 🥫",
        "MUEBLE HORNO":     "Soporte reforzado apto para horno y microondas 🔥",
        "AUXILIAR BAÑO":    "Compartimentos resistentes a la humedad 🚿",
        "CENTRO DE TV":     "Espacio para TV, decodificador y accesorios 📺",
        "CENTRO TV":        "Espacio para TV, decodificador y accesorios 📺",
        "MESA DE CENTRO":   "Superficie amplia y repisa inferior de almacenamiento ☕",
        "ORGANIZADOR":      "Múltiples divisiones para mantener todo en su lugar 🗂️",
        "MULTIFUNCIONAL":   "Diseño versátil que se adapta a diferentes usos 🔧",
    }
    caract_interna = CARACTERISTICA_INTERNA.get(titulo, f"Diseño específico para {ambiente} ✨")

    prompt = (
        f"Eres el community manager de 'El Chilenito Melaminero', mueblista en SJL, Lima Perú. "
        f"Escribe un post corto para Facebook e Instagram sobre: {titulo} a medida en melamina para {ambiente}.\n\n"
        f"REGLAS ESTRICTAS:\n"
        f"- Todo el texto debe hablar exclusivamente de {ambiente}. NO menciones otros ambientes.\n"
        f"- El post debe ser CORTO. Máximo 10 líneas en total.\n"
        f"- Sin introducciones, sin explicaciones, solo el post.\n\n"
        f"Sigue EXACTAMENTE este formato, sin cambiar nada de lo que está en mayúsculas o entre comillas:\n\n"
        f"[frase gancho creativa sobre el {titulo} a medida — 1 línea con emoji]\n\n"
        f"[beneficio principal del {titulo} para {ambiente} — 1 sola oración con emoji]\n\n"
        f"En El Chilenito Melaminero creamos soluciones que combinan orden, diseño y buen precio 🏡\n\n"
        f"✅ Diseño personalizado según tu espacio\n"
        f"✅ {caract_interna}\n"
        f"✅ Colores disponibles a elección 🎨\n"
        f"✅ Material resistente y duradero 💪\n"
        f"✅ Precios accesibles 💰\n"
        f"✅ Entregas a domicilio en SJL y todo Lima 🚚\n\n"
        f"[frase motivadora corta sobre {ambiente} — 1 línea con emoji]\n\n"
        f"📲 Cotiza por WhatsApp {WHATSAPP_NUMERO} y recibe asesoría personalizada\n\n"
        f"{hashtags}\n\n"
        f"Responde SOLO con el post. Sin corchetes, sin explicaciones, en español peruano natural."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 400       # reducido para forzar respuestas cortas
    }

    r = requests.post(url, headers=headers, json=payload).json()
    caption = r['choices'][0]['message']['content']
    print(f"   ✅ Caption: {len(caption)} caracteres | Ambiente: {ambiente}")
    return caption

# ─────────────────────────────────────────────
# PUBLICACIÓN META
# ─────────────────────────────────────────────
def publicar_fb(ruta, texto):
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    with open(ruta, 'rb') as f:
        r = requests.post(url,
            data={'message': texto, 'access_token': META_TOKEN},
            files={'source': f})
    ok = 'id' in r.json()
    if not ok:
        print(f"⚠️  Facebook: {r.text[:300]}")
    return ok

def publicar_ig(url_imagen, texto):
    r1 = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media",
        data={'image_url': url_imagen, 'caption': texto, 'access_token': META_TOKEN}
    ).json()
    c_id = r1.get('id')
    if not c_id:
        print(f"⚠️  IG container: {r1}")
        return False
    time.sleep(15)
    r2 = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish",
        data={'creation_id': c_id, 'access_token': META_TOKEN}
    ).json()
    ok = 'id' in r2
    if not ok:
        print(f"⚠️  IG publish: {r2}")
    return ok

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  🚀 MUEBLES BOT - Chilenito Melaminero")
    print("=" * 60)

    try:
        # 1. Elegir fondo aleatorio
        print("\n🎨 Eligiendo fondo...")
        fondo_info = elegir_fondo_del_dia()

        # 2. Listar muebles disponibles
        print("\n📂 Listando muebles...")
        archivos = listar_muebles_github()
        if not archivos:
            print("❌ No hay imágenes en muebles_sin_fondo")
            return

        # 3. Elegir imagen no publicada aún
        print("\n🎲 Eligiendo imagen nueva...")
        nombre_hoy, registro_actualizado, registro_sha = elegir_imagen_nueva(archivos)
        titulo = nombre_a_titulo(nombre_hoy)
        print(f"   📅 Mueble del día: {nombre_hoy}")
        print(f"   🏷️  Título: {titulo}")

        # 4. Descargar imagen
        print(f"\n⬇️  Descargando {nombre_hoy}...")
        imagen_mueble = descargar_mueble_github(nombre_hoy)
        if not imagen_mueble:
            return
        print("   ✅ Descargada")

        # 5. Componer pieza gráfica
        print("\n🎨 Componiendo pieza gráfica...")
        ruta = componer_pieza(fondo_info, imagen_mueble, titulo)

        # 6. Subir imagen a GitHub
        print("\n📤 Subiendo a GitHub...")
        url_p = subir_a_github(ruta)

        # 7. Generar caption
        print("\n✍️  Generando caption...")
        caption = generar_caption(titulo, nombre_hoy)

        # 8. Publicar en redes
        print("\n📘 Publicando en Facebook...")
        f_ok = publicar_fb(ruta, caption)

        print("\n📸 Publicando en Instagram...")
        i_ok = publicar_ig(url_p, caption) if url_p else False

        # 9. Guardar registro SOLO si al menos una red publicó bien
        if f_ok or i_ok:
            print("\n💾 Actualizando registro de publicadas...")
            guardar_registro_github(registro_actualizado, registro_sha)
        else:
            print("\n⚠️  No se guardó el registro porque ambas publicaciones fallaron")

        print(f"\n{'='*60}")
        print(f"  Facebook:  {'✅' if f_ok else '❌'}")
        print(f"  Instagram: {'✅' if i_ok else '❌'}")
        print(f"  Mueble:    {nombre_hoy}")
        print(f"  Título:    {titulo}")
        print(f"  Fondo:     {fondo_info['tipo']}")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
