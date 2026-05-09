"""
MUEBLES BOT - Chilenito Melaminero
Genera imagen IA + caption Groq + publica en FB e IG
"""

import os
import io
import json
import base64
import requests
import time
import sys
import urllib.parse
from PIL import Image
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
    print("   ✅ Todas las credenciales presentes")


def conectar_drive():
    print("\n📁 Conectando a Google Drive...")
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
        print("   ❌ No se encontró logo_principal.webp")
        return None
    request = service.files().get_media(fileId=archivos[0]['id'])
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    print("   ✅ Logo descargado")
    return Image.open(fh)


def generar_imagen_ia(descripcion):
    print(f"\n🎨 Generando imagen IA...")
    prompt = f"Professional photography of {descripcion}, high quality melamine wood texture, realistic lighting, modern showroom background, 8k resolution"
    prompt_encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&model=flux&nologo=true"
    print("   ⏳ Pollinations AI (puede tardar 20-40 seg)...")
    try:
        response = requests.get(url, timeout=120)
        if response.status_code == 200:
            print("   ✅ Imagen generada")
            return Image.open(io.BytesIO(response.content))
        print(f"   ❌ Error status {response.status_code}")
        return None
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        return None


def aplicar_marca_agua(foto_ia, img_logo):
    print("\n🖼️  Aplicando marca de agua...")
    foto = foto_ia.convert("RGBA")
    logo = img_logo.convert("RGBA")
    ancho_logo = int(foto.width * 0.30)
    w_percent = (ancho_logo / float(logo.width))
    alto_logo = int((float(logo.height) * float(w_percent)))
    logo = logo.resize((ancho_logo, alto_logo), Image.LANCZOS)
    foto.paste(logo, (foto.width - logo.width - 40, foto.height - logo.height - 40), logo)
    final = foto.convert("RGB")
    ruta = "post_final.jpg"
    final.save(ruta, "JPEG", quality=95)
    print("   ✅ Imagen final guardada")
    return ruta


def subir_imagen_a_github(ruta_local):
    print("\n☁️  Subiendo imagen a GitHub...")
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
        print(f"   ✅ URL: {url_publica}")
        return url_publica
    print(f"   ❌ Error: {response.status_code} - {response.text[:300]}")
    return None


def generar_caption_groq(mueble):
    print("\n✍️  Generando caption con Groq...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        f"Escribe un post de Facebook e Instagram para 'Chilenito Melaminero' "
        f"(mueblista en SJL, Lima Perú). El mueble es: {mueble}. "
        f"Tono cercano y profesional. Incluye emojis y 8 hashtags al final. "
        f"Llamada a la acción para WhatsApp. Máximo 250 palabras."
    )
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 600
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        caption = response.json()['choices'][0]['message']['content']
        print(f"   ✅ Caption generado ({len(caption)} caracteres)")
        return caption
    print(f"   ❌ Error Groq: {response.status_code} - {response.text[:300]}")
    return None


def publicar_en_facebook(ruta_foto, texto):
    print("\n📘 Publicando en Facebook...")
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    payload = {'message': texto, 'access_token': META_TOKEN, 'published': 'true'}
    with open(ruta_foto, 'rb') as f:
        r = requests.post(url, data=payload, files={'source': f}, timeout=60)
    data = r.json()
    if 'id' in data:
        print(f"   ✅ Publicado! ID: {data['id']}")
        return True
    print(f"   ❌ Error: {json.dumps(data, indent=2)}")
    return False


def publicar_en_instagram(url_imagen_publica, texto):
    print("\n📸 Publicando en Instagram...")
    print("   1/2 Creando contenedor...")
    url_base = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media"
    payload = {'image_url': url_imagen_publica, 'caption': texto, 'access_token': META_TOKEN}
    res = requests.post(url_base, data=payload, timeout=30).json()
    creation_id = res.get('id')
    if not creation_id:
        print(f"   ❌ Error: {json.dumps(res, indent=2)}")
        return False
    print(f"   ✅ Contenedor: {creation_id}")
    print("   ⏳ Esperando 7 seg...")
    time.sleep(7)
    print("   2/2 Publicando...")
    url_pub = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish"
    res_pub = requests.post(url_pub, data={'creation_id': creation_id, 'access_token': META_TOKEN}, timeout=30).json()
    if 'id' in res_pub:
        print(f"   ✅ Publicado! ID: {res_pub['id']}")
        return True
    print(f"   ❌ Error: {json.dumps(res_pub, indent=2)}")
    return False


def main():
    print("=" * 60)
    print("  🚀 MUEBLES BOT - Chilenito Melaminero")
    print("=" * 60)
    validar_credenciales()
    try:
        service = conectar_drive()
        logo = descargar_logo(service)
        if not logo:
            print("\n💥 No se pudo descargar el logo")
            sys.exit(1)
        
        mueble = "Centro de entretenimiento moderno en melamina color siena y blanco con cajones push open"
        
        foto = generar_imagen_ia(mueble)
        if not foto:
            print("\n💥 No se pudo generar imagen")
            sys.exit(1)
        
        ruta = aplicar_marca_agua(foto, logo)
        url_publica = subir_imagen_a_github(ruta)
        
        caption = generar_caption_groq(mueble)
        if not caption:
            print("\n💥 No se pudo generar caption, usando uno por defecto")
            caption = f"🪑 {mueble}\n\n¡Calidad y diseño para tu hogar!\n\n📲 Escríbenos por WhatsApp\n\n#Muebles #Melamina #Lima #SJL #ChilenitoMelaminero #MueblesPeru #Decoracion #HogarPeru"
        
        fb_ok = publicar_en_facebook(ruta, caption)
        ig_ok = False
        if url_publica:
            ig_ok = publicar_en_instagram(url_publica, caption)
        
        print("\n" + "=" * 60)
        print(f"  Facebook:  {'✅ OK' if fb_ok else '❌ FALLÓ'}")
        print(f"  Instagram: {'✅ OK' if ig_ok else '❌ FALLÓ'}")
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

