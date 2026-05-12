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

    # 1. Cargar fondo (SIN CAMBIOS)
    print("   🖼️  Cargando fondo...")
    fondo = Image.open(fondo_info["ruta"]).convert("RGBA").resize((W, H), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H))
    canvas.paste(fondo, (0, 0))

    # 2. Imagen PNG del mueble → AJUSTADA PARA NO TAPAR LOGO/WHATSAPP
    print("   🪑 Posicionando mueble...")
    mueble = imagen_mueble.convert("RGBA")
    ancho_original, alto_original = mueble.size
    proporcion = ancho_original / alto_original

    # 📏 ZONAS DEFINIDAS:
    ZONA_SUPERIOR = int(H * 0.18)   # Espacio para título arriba
    ZONA_INFERIOR = int(H * 0.82)    # 🚫 LÍMITE INFERIOR: no pasa de aquí (deja abajo el 18% para logo y WhatsApp)
    ZONA_ALTO_DISPONIBLE = ZONA_INFERIOR - ZONA_SUPERIOR
    ZONA_ANCHO_DISPONIBLE = W

    # 📏 Ajuste de proporciones SOLO para el mueble
    if 0.7 <= proporcion <= 1.4:
        # Casi cuadrada
        MAX_W = int(ZONA_ANCHO_DISPONIBLE * 0.97)
        MAX_H = int(ZONA_ALTO_DISPONIBLE * 0.97)
    elif proporcion < 0.7:
        # Muy ALTA → reducimos más el alto para que no se pase abajo
        MAX_W = int(ZONA_ANCHO_DISPONIBLE * 0.72)
        MAX_H = int(ZONA_ALTO_DISPONIBLE * 0.92)
    else:
        # Muy ANCHA → reducimos alto
        MAX_W = int(ZONA_ANCHO_DISPONIBLE * 0.97)
        MAX_H = int(ZONA_ALTO_DISPONIBLE * 0.72)

    # Escalar manteniendo proporción, SIN DEFORMAR
    ratio = min(MAX_W / ancho_original, MAX_H / alto_original)
    new_w = int(ancho_original * ratio)
    new_h = int(alto_original * ratio)
    mueble = mueble.resize((new_w, new_h), Image.LANCZOS)

    # Centrado perfecto DENTRO de la zona permitida
    mueble_x = (W - new_w) // 2
    mueble_y = ZONA_SUPERIOR + (ZONA_ALTO_DISPONIBLE - new_h) // 2

    # Seguridad extra: nunca se pasa del límite inferior
    if mueble_y + new_h > ZONA_INFERIOR:
        mueble_y = ZONA_INFERIOR - new_h

    canvas.paste(mueble, (mueble_x, mueble_y), mueble)

    # Convertir a RGB para texto
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

    # Sombra y texto título
    draw.text((tit_x + 3, tit_y + 3), titulo, font=f_tit, fill=COLOR_SOMBRA)
    draw.text((tit_x, tit_y), titulo, font=f_tit, fill=COLOR_TITULO)

    # 4. Cursiva "a medida" (SIN CAMBIOS)
    f_cur = cargar_fuente(FUENTE_CURSIVA, 85)
    bbox_c = draw.textbbox((0, 0), "a medida", font=f_cur)
    cur_w = bbox_c[2] - bbox_c[0]
    cur_x = tit_x + tit_w - cur_w + 10
    cur_y = tit_y + tit_h + 5

    draw.text((cur_x + 2, cur_y + 2), "a medida", font=f_cur, fill=COLOR_SOMBRA)
    draw.text((cur_x, cur_y), "a medida", font=f_cur, fill=COLOR_CURSIVA)

    # Guardar
    ruta = "post_final.jpg"
    canvas_rgb.save(ruta, "JPEG", quality=97, subsampling=0)
    print("   ✅ Pieza guardada")
    return ruta
