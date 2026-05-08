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

# ====================================================================
# CONFIGURACIÓN (Tus IDs de Drive ya están aquí)
# ====================================================================
ID_CARPETA_LOGO = "1EKyQ0HCDd2gp89_0FAdGClZ9KO3fvcUN"
ID_PUBLICACIONES = "1ajUOSc3fw52khPvXF2XgVF77soWCwT1z"

# Tokens desde los Secrets de GitHub
HF_TOKEN = os.environ.get("HF_TOKEN")
META_TOKEN = os.environ.get("META_TOKEN")
FB_PAGE_ID = os.environ.get("META_PAGE_ID")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# URL del modelo de imagen en Hugging Face
API_URL_HF = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

# Inicializar Gemini
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')

# ====================================================================
# FUNCIONES TÉCNICAS
# ====================================================================

def conectar_drive():
    creds_json = os.environ.get("GDRIVE_CREDENTIALS")
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def descargar_logo(service):
    """Busca el logo_principal.webp en tu carpeta de Drive"""
    query = f"'{ID_CARPETA_LOGO}' in parents and name = 'logo_principal.webp'"
    res = service.files().list(q=query).execute()
    if not res.get('files'):
        print("❌ No se encontró el logo en Drive.")
        return None
    
    file_id = res['files'][0]['id']
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return Image.open(fh)

def generar_imagen_ia(descripcion):
    """Genera la foto del mueble usando Hugging Face"""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    # Prompt optimizado para realismo de carpintería
    prompt = f"Professional photography of a {descripcion}, high quality wood texture, realistic lighting, carpentry workshop background, 8k resolution."
    
    print(f"🎨 Creando imagen realista de: {descripcion}...")
    response = requests.post(API_URL_HF, headers=headers, json={"inputs": prompt})
    
    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    else:
        print(f"❌ Error en Hugging Face: {response.status_code} - {response.text}")
        return None

def aplicar_marca_agua(foto_ia, img_logo):
    """Pega tu logo en la esquina inferior derecha"""
    foto = foto_ia.convert("RGBA")
    logo = img_logo.convert("RGBA")
    
    # Tamaño del logo (18% del ancho de la foto)
    ancho_logo = int(foto.width * 0.18)
    w_percent = (ancho_logo / float(logo.width))
    alto_logo = int((float(logo.height) * float(w_percent)))
    logo = logo.resize((ancho_logo, alto_logo), Image.LANCZOS)
    
    # Posición (Margen de 40px)
    x = foto.width - logo.width - 40
    y = foto.height - logo.height - 40
    
    foto.paste(logo, (x, y), logo)
    
    final = foto.convert("RGB")
    ruta = "post_final.jpg"
    final.save(ruta, "JPEG", quality=95)
    return ruta

def publicar_en_facebook(ruta_foto, texto):
    """Sube la foto y el texto a tu página de Facebook"""
    url = f"
