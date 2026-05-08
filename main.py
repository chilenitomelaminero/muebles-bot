import os
import io
import json
import requests
import time
from PIL import Image
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import google.generativeai as genai

# CONFIGURACIÓN DE IDs
ID_CARPETA_LOGO = "1EKyQ0HCDd2gp89_0FAdGClZ9KO3fvcUN"
ID_PUBLICACIONES = "1ajUOSc3fw52khPvXF2XgVF77soWCwT1z"

# TOKENS (Asegúrate de tener META_INSTAGRAM_ID en tus Secrets)
HF_TOKEN = os.environ.get("HF_TOKEN")
META_TOKEN = os.environ.get("META_TOKEN")
FB_PAGE_ID = os.environ.get("META_PAGE_ID")
IG_USER_ID = os.environ.get("META_INSTAGRAM_ID") 
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

API_URL_HF = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')

def conectar_drive():
    creds_json = os.environ.get("GDRIVE_CREDENTIALS")
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def descargar_logo(service):
    query = f"'{ID_CARPETA_LOGO}' in parents and name = 'logo_principal.webp'"
    res = service.files().list(q=query).execute()
    if not res.get('files'): return None
    request = service.files().get_media(fileId=res['files'][0]['id'])
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return Image.open(fh)

def generar_imagen_ia(descripcion):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    prompt = f"Professional photography of a {descripcion}, high quality melamine wood texture, realistic lighting, workshop background, 8k resolution."
    response = requests.post(API_URL_HF, headers=headers, json={"inputs": prompt})
    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    return None

def aplicar_marca_agua(foto_ia, img_logo):
    foto = foto_ia.convert("RGBA")
    logo = img_logo.convert("RGBA")
    ancho_logo = int(foto.width * 0.18)
    w_percent = (ancho_logo / float(logo.width))
    alto_logo = int((float(logo.height) * float(w_percent)))
    logo = logo.resize((ancho_logo, alto_logo), Image.LANCZOS)
    foto.paste(logo, (foto.width - logo.width - 40, foto.height - logo.height - 40), logo)
    final = foto.convert("RGB")
    final.save("post_final.jpg", "JPEG", quality=95)
    return "post_final.jpg"

def publicar_en_facebook(ruta_foto, texto):
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    payload = {'message': texto, 'access_token': META_TOKEN, 'published': 'true'}
    with open(ruta_foto, 'rb') as f:
        r = requests.post(url, data=payload, files={'source': f})
    return r.json()

def publicar_en_instagram(url_imagen_publica, texto):
    """Instagram requiere una URL pública de la imagen"""
    # 1. Crear contenedor
    url_base = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media"
    payload = {
        'image_url': url_imagen_publica,
        'caption': texto,
        'access_token': META_TOKEN
    }
    res = requests.post(url_base, data=payload).json()
    creation_id = res.get('id')
    
    if creation_id:
        # 2. Publicar contenedor
        url_pub = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish"
        res_pub = requests.post(url_pub, data={'creation_id': creation_id, 'access_token': META_TOKEN})
        return res_pub.json()
    return res

def main():
    print("🚀 Iniciando el Bot del Chilenito Melaminero (FB + IG)...")
    try:
        service = conectar_drive()
        mueble_del_dia = "Centro de entretenimiento moderno en melamina color siena y blanco con cajones push open"
        
        foto_mueble = generar_imagen_ia(mueble_del_dia)
        if not foto_mueble: return
        
        logo = descargar_logo(service)
        if not logo: return
        
        ruta_archivo = aplicar_marca_agua(foto_mueble, logo)
        
        prompt_texto = f"Escribe un post de Facebook e Instagram para el 'Chilenito Melaminero' (mueblista en SJL). El mueble es: {mueble_del_dia}. Tono cercano y profesional."
        caption = model_gemini.generate_content(prompt_texto).text

        # PUBLICAR EN FACEBOOK
        res_fb = publicar_en_facebook(ruta_archivo, caption)
        print(f"📡 Respuesta Facebook: {res_fb}")

        # NOTA PARA INSTAGRAM: 
        # Instagram API exige que la foto esté en una URL pública (Imgur, Cloudinary, o un servidor).
        # Si solo usas GitHub, Instagram es más difícil de automatizar sin un hosting intermedio.
        
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    main()
