# ─────────────────────────
# MUEBLE
# ─────────────────────────

mueble = imagen_mueble.convert("RGBA")

# RECORTE AUTOMATICO
bbox = mueble.getbbox()

if bbox:
    mueble = mueble.crop(bbox)

# ZONA MÁS EQUILIBRADA
ZONA_SUPERIOR = int(H * 0.28)
ZONA_INFERIOR = int(H * 0.88)

ZONA_H = ZONA_INFERIOR - ZONA_SUPERIOR

# TAMAÑO MÁS CONTROLADO
MAX_W = int(W * 0.82)
MAX_H = int(ZONA_H * 0.88)

# AJUSTES SEGÚN TIPO
if "ROPERO" in titulo:
    MAX_W = int(W * 0.74)

elif "VELADOR" in titulo:
    MAX_W = int(W * 0.58)

elif "TOCADOR" in titulo:
    MAX_W = int(W * 0.72)

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
    20
)

# ─────────────────────────
# HALO DE LUZ SUAVE
# ─────────────────────────

halo_size = int(
    max(new_w, new_h) * 1.08
)

halo = Image.new(
    "RGBA",
    (halo_size, halo_size),
    (255,255,255,0)
)

halo_draw = ImageDraw.Draw(halo)

halo_draw.ellipse(
    (0,0,halo_size,halo_size),
    fill=(255,255,255,28)
)

halo = halo.filter(
    ImageFilter.GaussianBlur(45)
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
# SOMBRA SUAVE
# ─────────────────────────

sombra = Image.new(
    "RGBA",
    mueble.size,
    (0,0,0,70)
)

sombra = sombra.filter(
    ImageFilter.GaussianBlur(18)
)

canvas.paste(
    sombra,
    (mueble_x + 12, mueble_y + 16),
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
