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

    # 1. Cargar fondo (SIN CAMBIOS, se mantiene igual)
    print("   🖼️  Cargando fondo...")
    fondo = Image.open(fondo_info["ruta"]).convert("RGBA").resize((W, H), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H))
    canvas.paste(fondo, (0, 0))

    # 2. Imagen PNG del mueble → SOLO AQUÍ SE AJUSTAN PROPORCIONES
    print("   🪑 Posicionando mueble...")
    mueble = imagen_mueble.convert("RGBA")
    ancho_original, alto_original = mueble.size
    proporcion = ancho_original / alto_original  # >1 = ancha ; <1 = alta

    # Zona disponible (igual que tenías antes)
    ZONA_SUPERIOR = int(H * 0.18)
    ZONA_ALTO = H - ZONA_SUPERIOR

    # 📏 Ajuste de proporciones SOLO para esta imagen
    if 0.7 <= proporcion <= 1.4:
        # Casi cuadrada → tamaño normal
        MAX_W = int(W * 0.97)
        MAX_H = int(ZONA_ALTO * 0.99)
    elif proporcion < 0.7:
        # Muy ALTA → hacemos que sea más angosta para que no se vea gigante
        MAX_W = int(W * 0.70)
        MAX_H = int(ZONA_ALTO * 0.97)
    else:
        # Muy ANCHA → hacemos que sea más baja para que no se deforme
        MAX_W = int(W * 0.97)
        MAX_H = int(ZONA_ALTO * 0.70)

    # Escalar manteniendo proporción perfecta
    ratio = min(MAX_W / ancho_original, MAX_H / alto_original)
    new_w = int(ancho_original * ratio)
    new_h = int(alto_original * ratio)
    mueble = mueble.resize((new_w, new_h), Image.LANCZOS)

    # Centrado (igual que siempre)
    mueble_x = (W - new_w) // 2
    mueble_y = ZONA_SUPERIOR + (ZONA_ALTO - new_h) // 2
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
