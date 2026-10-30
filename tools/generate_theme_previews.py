#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tools/generate_theme_previews.py
--------------------------------
Genera capturas visuales realistas en alta resolución (1280x480) de cada vista
del sistema Melis OS para cada tema (tactical, stealth, cyber):
  01. Escritorio Principal (Desktop)
  02. Menú de Ajustes y Configuración (Settings)
  03. Reproductor Multimedia (Music Player)
  04. Teléfono y Marcador Bluetooth (BT Phone)
  05. Radio FM y Transmisor de Audio (FM Audio)
  06. Ecualizador Gráfico (EQ & Audio FX)
  07. Cortina Desplegable Rápida (Pullmenu)
  08. Reloj de Pantalla de Bloqueo (Standby Clock)
  00. Mosaico Resumen de Todas las Vistas (Collage panorámico)
"""

import os
import sys
import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES_DIR = os.path.join(BASE_DIR, "themes")
BACKUP_DIR = os.path.join(THEMES_DIR, "factory_backup", "appres", "img")

UI_WIDTH = 1280
UI_HEIGHT = 480

def get_font(size, bold=False):
    font_paths = [
        "/System/Library/Fonts/SFProDisplay-Bold.otf" if bold else "/System/Library/Fonts/SFProDisplay-Regular.otf",
        "/System/Library/Fonts/SFProText-Bold.otf" if bold else "/System/Library/Fonts/SFProText-Regular.otf",
        "/System/Library/Fonts/SFPro-Bold.ttf" if bold else "/System/Library/Fonts/SFPro-Regular.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def load_theme_img(theme, rel_path):
    theme_p = os.path.join(THEMES_DIR, theme, "appres", "img", rel_path)
    if os.path.exists(theme_p):
        return Image.open(theme_p).convert("RGBA")
    backup_p = os.path.join(BACKUP_DIR, rel_path)
    if os.path.exists(backup_p):
        return Image.open(backup_p).convert("RGBA")
    return None

def paste_safe(canvas, img, pos, anchor="tl", target_size=None):
    if img is None:
        return
    im = img
    if target_size and im.size != target_size:
        im = im.resize(target_size, Image.Resampling.LANCZOS)
    x, y = pos
    if anchor == "center":
        x = x - im.size[0] // 2
        y = y - im.size[1] // 2
    canvas.paste(im, (x, y), im)

def get_theme_colors(theme):
    if theme == "stealth":
        return {
            "name": "Stealth Luxe / Monocromo Titanio",
            "accent": (220, 225, 235, 255),
            "accent_sub": (175, 185, 200, 255),
            "text": (235, 240, 245, 255),
            "text_sub": (160, 175, 195, 255),
            "card_bg": (14, 18, 26, 235),
            "border": (55, 68, 85, 255)
        }
    elif theme == "tactical":
        return {
            "name": "Tactical Off-Road / 4x4 Aventura",
            "accent": (255, 140, 0, 255),
            "accent_sub": (212, 255, 0, 255),
            "text": (245, 245, 235, 255),
            "text_sub": (190, 210, 180, 255),
            "card_bg": (16, 22, 20, 240),
            "border": (70, 85, 65, 255)
        }
    else: # cyber
        return {
            "name": "Cyber Sport / Neón Dinámico",
            "accent": (0, 229, 255, 255),
            "accent_sub": (255, 0, 128, 255),
            "text": (240, 250, 255, 255),
            "text_sub": (170, 230, 255, 255),
            "card_bg": (12, 16, 32, 240),
            "border": (40, 70, 120, 255)
        }

def get_base_wallpaper(theme):
    bg_p = os.path.join(THEMES_DIR, theme, "appres", "img", "setting", "bg0.png")
    if not os.path.exists(bg_p):
        bg_p = os.path.join(THEMES_DIR, theme, "appres", "img", "setting", "bg0.jpg")
    if os.path.exists(bg_p):
        im = Image.open(bg_p).convert("RGBA")
        if im.size != (UI_WIDTH, UI_HEIGHT):
            im = im.resize((UI_WIDTH, UI_HEIGHT), Image.Resampling.LANCZOS)
        return im
    return Image.new("RGBA", (UI_WIDTH, UI_HEIGHT), (16, 18, 24, 255))

def render_headbar(canvas, theme, current_title=None):
    draw = ImageDraw.Draw(canvas)
    col = get_theme_colors(theme)
    # Barra base
    bar_overlay = Image.new("RGBA", (UI_WIDTH, 48), (10, 14, 20, 220))
    canvas.paste(bar_overlay, (0, 0), bar_overlay)
    draw.line([(0, 48), (UI_WIDTH, 48)], fill=(255, 255, 255, 25), width=1)
    
    # Home & Back buttons
    home = load_theme_img(theme, "headbar/home.png")
    back = load_theme_img(theme, "headbar/back.png")
    paste_safe(canvas, home, (10, 2), target_size=(74, 44))
    paste_safe(canvas, back, (90, 2), target_size=(74, 44))
    
    if current_title:
        draw.text((180, 24), current_title, fill=col["accent"], font=get_font(18, bold=True), anchor="lm")
    
    # Status icons
    vol = load_theme_img(theme, "headbar/vol.png")
    bright = load_theme_img(theme, "headbar/bright.png")
    wifi = load_theme_img(theme, "headbar/wifi.png")
    bt = load_theme_img(theme, "headbar/bt.png")
    
    paste_safe(canvas, vol, (960, 10), target_size=(32, 28))
    draw.text((1000, 24), "80%", fill=col["text_sub"], font=get_font(13, bold=True), anchor="lm")
    
    paste_safe(canvas, bright, (1050, 10), target_size=(28, 28))
    paste_safe(canvas, wifi, (1100, 12), target_size=(30, 24))
    paste_safe(canvas, bt, (1145, 12), target_size=(22, 26))
    
    now = datetime.datetime.now()
    draw.text((1220, 24), now.strftime("%H:%M"), fill=col["text"], font=get_font(16, bold=True), anchor="mm")

# 1. Vista Escritorio
def render_view_desktop(theme):
    im = get_base_wallpaper(theme)
    draw = ImageDraw.Draw(im)
    col = get_theme_colors(theme)
    render_headbar(im, theme)
    
    # Reloj digital central
    now = datetime.datetime.now()
    draw.text((370, 110), now.strftime("%H:%M"), fill=col["text"], font=get_font(68, bold=True), anchor="mm")
    draw.text((376, 185), now.strftime("%Y-%m-%d"), fill=col["accent_sub"], font=get_font(18, bold=False), anchor="mm")
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    draw.text((373, 228), dias[now.weekday()], fill=col["text_sub"], font=get_font(16, bold=True), anchor="mm")
    
    # Tarjeta de música desktop_bg.png
    card = load_theme_img(theme, "desktop/desktop_bg.png")
    if card:
        paste_safe(im, card, (778, 70), target_size=(394, 222))
    else:
        draw.rounded_rectangle([778, 70, 1172, 292], radius=16, fill=col["card_bg"], outline=col["border"], width=1)
        
    draw.text((975, 130), "Reproductor Multimedia", fill=col["accent"], font=get_font(18, bold=True), anchor="mm")
    draw.text((975, 160), "Bluetooth Audio / F133 Hi-Fi", fill=col["text_sub"], font=get_font(13), anchor="mm")
    
    # Controles tarjeta
    c_prev = load_theme_img(theme, "desktop/pre.png")
    c_play = load_theme_img(theme, "desktop/play.png")
    c_next = load_theme_img(theme, "desktop/next.png")
    paste_safe(im, c_prev, (880, 220), anchor="center")
    paste_safe(im, c_play, (975, 220), anchor="center")
    paste_safe(im, c_next, (1070, 220), anchor="center")
    
    # Botones CarPlay y Android Auto en los extremos
    cp = load_theme_img(theme, "desktop/desktop_Carplay.png")
    aa = load_theme_img(theme, "desktop/desktop_Aoa.png")
    paste_safe(im, cp, (16, 320), target_size=(130, 116))
    paste_safe(im, aa, (1134, 320), target_size=(130, 116))
    
    # 6 Botones del lanzador central
    apps = [
        ("desktop/desktop_Audio.png", "Audio", 176),
        ("desktop/desktop_Usb.png", "USB", 336),
        ("desktop/desktop_SD.png", "SD Card", 496),
        ("desktop/desktop_Bt.png", "Teléfono", 656),
        ("desktop/desktop_ArMir.png", "Mirror", 816),
        ("desktop/desktop_Calculator.png", "Calc", 976)
    ]
    for rel_p, label, x in apps:
        app_img = load_theme_img(theme, rel_p)
        paste_safe(im, app_img, (x, 312), target_size=(126, 126))
        draw.text((x + 63, 444), label, fill=col["text"], font=get_font(12, bold=True), anchor="mm")
        
    return im

# 2. Vista Ajustes
def render_view_setting(theme):
    im = get_base_wallpaper(theme)
    draw = ImageDraw.Draw(im)
    col = get_theme_colors(theme)
    render_headbar(im, theme, current_title="Configuración del Sistema")
    
    # Barra lateral de pestañas (setting/tab_bg.png translúcido)
    tab_bg = load_theme_img(theme, "setting/tab_bg.png")
    paste_safe(im, tab_bg, (0, 48), target_size=(380, 432))
    
    tabs = [
        ("setting/0.png", "General", True),
        ("setting/1.png", "Fecha y Hora", False),
        ("setting/2.png", "Pantalla", False),
        ("setting/3.png", "Fondos de Pantalla", False),
        ("setting/4.png", "Información", False),
    ]
    for i, (tab_ico, title, is_active) in enumerate(tabs):
        ty = 65 + i * 70
        if is_active:
            draw.rounded_rectangle([15, ty, 365, ty + 60], radius=10, fill=col["accent"], outline=col["accent"])
            tcol = (10, 15, 20, 255)
        else:
            draw.rounded_rectangle([15, ty, 365, ty + 60], radius=10, fill=(20, 25, 35, 180), outline=col["border"])
            tcol = col["text"]
            
        ico = load_theme_img(theme, tab_ico)
        paste_safe(im, ico, (30, ty + 5), target_size=(50, 50))
        draw.text((95, ty + 30), title, fill=tcol, font=get_font(16, bold=True), anchor="lm")
        
    # Panel de contenido derecho (setting/content_bg.png)
    content_bg = load_theme_img(theme, "setting/content_bg.png")
    if content_bg:
        paste_safe(im, content_bg, (400, 65), target_size=(860, 400))
    else:
        draw.rounded_rectangle([400, 65, 1260, 465], radius=16, fill=col["card_bg"], outline=col["border"], width=1)
        
    # Opciones de ajustes
    items = [
        ("Brillo de Pantalla (Backlight)", "slider"),
        ("Sonido al Encender (0dB Silencioso)", "toggle_off"),
        ("Enlace Automático CarPlay / Auto", "toggle_on"),
        ("Inversión de Cámara Trasera (AHD 1080P)", "toggle_on"),
    ]
    sl_bg = load_theme_img(theme, "setting/sl_bg.png")
    sl_p = load_theme_img(theme, "setting/sl_p.png")
    on_img = load_theme_img(theme, "setting/on.png")
    off_img = load_theme_img(theme, "setting/off.png")
    
    for idx, (label, ctrl_type) in enumerate(items):
        iy = 95 + idx * 75
        draw.text((430, iy + 20), label, fill=col["text"], font=get_font(16, bold=False), anchor="lm")
        if ctrl_type == "slider":
            paste_safe(im, sl_bg, (850, iy + 10), target_size=(320, 22))
            paste_safe(im, sl_p, (1050, iy + 7), target_size=(28, 28))
            draw.text((1200, iy + 20), "85%", fill=col["accent"], font=get_font(14, bold=True), anchor="lm")
        elif ctrl_type == "toggle_on":
            paste_safe(im, on_img, (1100, iy + 2), target_size=(80, 36))
        elif ctrl_type == "toggle_off":
            paste_safe(im, off_img, (1100, iy + 2), target_size=(80, 36))
            
    # Botón acción inferior (default_btn.png)
    def_btn = load_theme_img(theme, "setting/default_btn.png")
    paste_safe(im, def_btn, (430, 405), target_size=(155, 50))
    draw.text((507, 430), "Restablecer", fill=col["text"], font=get_font(14, bold=True), anchor="mm")
    
    ok_btn = load_theme_img(theme, "setting/ok.png")
    paste_safe(im, ok_btn, (1080, 405), target_size=(155, 50))
    draw.text((1157, 430), "Guardar", fill=col["text"], font=get_font(14, bold=True), anchor="mm")
    
    return im

# 3. Vista Reproductor Música
def render_view_music(theme):
    im = get_base_wallpaper(theme)
    draw = ImageDraw.Draw(im)
    col = get_theme_colors(theme)
    render_headbar(im, theme, current_title="Reproductor de Música")
    
    # Carátula del disco (music/icon.png)
    disc = load_theme_img(theme, "music/icon.png")
    paste_safe(im, disc, (140, 80), target_size=(240, 230))
    
    # Tarjeta de información (music/info_bg.png)
    info_bg = load_theme_img(theme, "music/info_bg.png")
    if info_bg:
        paste_safe(im, info_bg, (430, 80), target_size=(700, 230))
    else:
        draw.rounded_rectangle([430, 80, 1130, 310], radius=16, fill=col["card_bg"], outline=col["border"], width=1)
        
    draw.text((470, 125), "Nightcall (Drive OST)", fill=col["accent"], font=get_font(26, bold=True), anchor="lm")
    draw.text((470, 170), "Artista: Kavinsky / Lovefoxxx", fill=col["text"], font=get_font(18), anchor="lm")
    draw.text((470, 210), "Álbum: OutRun [FLAC 96kHz/24bit Hi-Res]", fill=col["text_sub"], font=get_font(15), anchor="lm")
    draw.text((470, 255), "Pista 03 / 12  •  Almacenamiento USB 01", fill=col["accent_sub"], font=get_font(14, bold=True), anchor="lm")
    
    # Barra de progreso
    draw.text((140, 345), "02:45", fill=col["text_sub"], font=get_font(14, bold=True), anchor="lm")
    sl_bg = load_theme_img(theme, "music/sl_bg.png")
    sl_p = load_theme_img(theme, "music/sl_p.png")
    sl_sel = load_theme_img(theme, "music/sl_sel.png")
    paste_safe(im, sl_bg, (200, 338), target_size=(880, 18))
    paste_safe(im, sl_sel, (200, 338), target_size=(480, 18))
    paste_safe(im, sl_p, (670, 333), target_size=(28, 28))
    draw.text((1140, 345), "04:18", fill=col["text_sub"], font=get_font(14, bold=True), anchor="rm")
    
    # Botonera de control inferior
    btns = [
        ("music/eq.png", 220),
        ("music/prev.png", 370),
        ("music/play.png", 520),
        ("music/next.png", 670),
        ("music/repeat_all.png", 820),
        ("music/random.png", 970),
    ]
    for b_rel, bx in btns:
        b_img = load_theme_img(theme, b_rel)
        paste_safe(im, b_img, (bx, 385), target_size=(120, 70))
        
    return im

# 4. Vista Teléfono Bluetooth
def render_view_bt(theme):
    im = get_base_wallpaper(theme)
    draw = ImageDraw.Draw(im)
    col = get_theme_colors(theme)
    render_headbar(im, theme, current_title="Teléfono Bluetooth Manos Libres")
    
    # Cuadro de entrada número (bt/input.png)
    inp = load_theme_img(theme, "bt/input.png")
    paste_safe(im, inp, (320, 65), target_size=(540, 50))
    draw.text((345, 90), "+56 9 8765 4321", fill=col["accent"], font=get_font(24, bold=True), anchor="lm")
    
    del_btn = load_theme_img(theme, "bt/del.png")
    paste_safe(im, del_btn, (880, 65), target_size=(80, 50))
    
    # Teclado numérico 3x4
    keys = [
        ("1", "bt/1.png"), ("2", "bt/2.png"), ("3", "bt/3.png"),
        ("4", "bt/4.png"), ("5", "bt/5.png"), ("6", "bt/6.png"),
        ("7", "bt/7.png"), ("8", "bt/8.png"), ("9", "bt/9.png"),
        ("*", "bt/star.png"), ("0", "bt/0.png"), ("#", "bt/hash.png"),
    ]
    start_x = 320
    start_y = 125
    kw = 140
    kh = 55
    for idx, (num, ico_p) in enumerate(keys):
        r = idx // 3
        c = idx % 3
        kx = start_x + c * (kw + 20)
        ky = start_y + r * (kh + 8)
        k_img = load_theme_img(theme, ico_p)
        paste_safe(im, k_img, (kx, ky), target_size=(kw, kh))
        
    # Botones Llamar y Colgar a los lados
    ans = load_theme_img(theme, "bt/answer.png")
    hang = load_theme_img(theme, "bt/hangup.png")
    paste_safe(im, ans, (120, 200), target_size=(160, 80))
    paste_safe(im, hang, (1000, 200), target_size=(160, 80))
    
    # Barra de pestañas inferior (bt/tab_bg.png translúcido)
    bt_tab = load_theme_img(theme, "bt/tab_bg.png")
    paste_safe(im, bt_tab, (0, 395), target_size=(UI_WIDTH, 85))
    
    b_tabs = ["Teclado", "Contactos", "Historial", "Música BT", "Emparejar"]
    for idx, name in enumerate(b_tabs):
        bx = 128 + idx * 220
        is_cur = idx == 0
        tcol = col["accent"] if is_cur else col["text_sub"]
        draw.text((bx, 438), name, fill=tcol, font=get_font(16, bold=is_cur), anchor="mm")
        
    return im

# 5. Vista Radio FM
def render_view_fm(theme):
    im = get_base_wallpaper(theme)
    draw = ImageDraw.Draw(im)
    col = get_theme_colors(theme)
    render_headbar(im, theme, current_title="Transmisor FM / Radio")
    
    # Pestaña FM superior (audio/tab_fm_sel.png)
    fm_tab = load_theme_img(theme, "audio/tab_fm_sel.png")
    paste_safe(im, fm_tab, (480, 55), target_size=(320, 45))
    draw.text((640, 77), "TRANSMISOR FM AUDIO", fill=col["accent"], font=get_font(15, bold=True), anchor="mm")
    
    # Display frecuencia grande
    freq_bg = load_theme_img(theme, "audio/freq_bg.png")
    if freq_bg:
        paste_safe(im, freq_bg, (280, 115), target_size=(720, 160))
    else:
        draw.rounded_rectangle([280, 115, 1000, 275], radius=16, fill=col["card_bg"], outline=col["border"], width=1)
        
    draw.text((600, 195), "107.9", fill=col["accent"], font=get_font(84, bold=True), anchor="mm")
    mhz = load_theme_img(theme, "audio/mhz.png")
    paste_safe(im, mhz, (840, 175), target_size=(90, 45))
    
    # Botones Sintonizar Izq / Der
    prev_b = load_theme_img(theme, "audio/prev.png")
    next_b = load_theme_img(theme, "audio/next.png")
    paste_safe(im, prev_b, (140, 150), target_size=(90, 90))
    paste_safe(im, next_b, (1050, 150), target_size=(90, 90))
    
    # Presintonías P1..P6
    presets = ["87.5", "92.1", "96.5", "101.3", "105.7", "107.9"]
    for i, p_val in enumerate(presets):
        px = 140 + i * 170
        is_sel = i == 5
        p_ico = load_theme_img(theme, f"audio/p{i+1}_sel.png" if is_sel else f"audio/p{i+1}.png")
        if p_ico:
            paste_safe(im, p_ico, (px, 320), target_size=(130, 80))
        else:
            bg_c = col["accent"] if is_sel else col["card_bg"]
            draw.rounded_rectangle([px, 320, px + 130, 400], radius=12, fill=bg_c, outline=col["border"], width=1)
        txt_c = (10, 15, 20, 255) if is_sel else col["text"]
        draw.text((px + 65, 360), f"P{i+1}: {p_val}", fill=txt_c, font=get_font(15, bold=True), anchor="mm")
        
    return im

# 6. Vista Ecualizador
def render_view_eq(theme):
    im = get_base_wallpaper(theme)
    draw = ImageDraw.Draw(im)
    col = get_theme_colors(theme)
    render_headbar(im, theme, current_title="Ecualizador DSP y Efectos de Audio")
    
    # Presets superiores: Standard, Rock, Pop, Jazz, Clásica
    presets = [("Estándar", False), ("Rock", True), ("Pop", False), ("Jazz", False), ("Clásica", False)]
    eq_btn = load_theme_img(theme, "eq/eq_btn.png")
    for i, (p_name, active) in enumerate(presets):
        bx = 160 + i * 200
        paste_safe(im, eq_btn, (bx, 65), target_size=(170, 52))
        tcol = col["accent"] if active else col["text"]
        draw.text((bx + 85, 91), p_name, fill=tcol, font=get_font(16, bold=active), anchor="mm")
        
    # 7 Bandas gráficas de ecualización
    bands = [("60Hz", +4), ("150Hz", +6), ("400Hz", +2), ("1kHz", -1), ("3kHz", +3), ("7kHz", +5), ("15kHz", +7)]
    for i, (b_name, db) in enumerate(bands):
        bx = 200 + i * 135
        # Riel del slider
        draw.rounded_rectangle([bx + 20, 150, bx + 28, 360], radius=4, fill=(35, 45, 60, 200), outline=col["border"])
        # Perilla según dB
        pos_y = int(255 - (db / 10.0) * 85)
        draw.ellipse([bx + 9, pos_y - 12, bx + 39, pos_y + 12], fill=col["accent"], outline=(255, 255, 255, 240), width=2)
        # Etiquetas
        draw.text((bx + 24, pos_y - 25), f"{db:+d}dB", fill=col["accent_sub"], font=get_font(12, bold=True), anchor="mm")
        draw.text((bx + 24, 385), b_name, fill=col["text_sub"], font=get_font(14, bold=True), anchor="mm")
        
    # Botón Loudness a la derecha
    loud = load_theme_img(theme, "eq/loud_on.png")
    if loud:
        paste_safe(im, loud, (1120, 200), target_size=(110, 60))
    else:
        draw.rounded_rectangle([1120, 200, 1230, 260], radius=12, fill=col["accent"], outline=col["accent"])
        draw.text((1175, 230), "LOUD ON", fill=(10, 15, 20, 255), font=get_font(14, bold=True), anchor="mm")
        
    return im

# 7. Vista Cortina Pullmenu
def render_view_pullmenu(theme):
    im = get_base_wallpaper(theme)
    # Oscurecer fondo tipo cortina
    darken = Image.new("RGBA", (UI_WIDTH, UI_HEIGHT), (0, 0, 0, 160))
    im.paste(darken, (0, 0), darken)
    
    draw = ImageDraw.Draw(im)
    col = get_theme_colors(theme)
    
    # Panel de cortina superior
    draw.rounded_rectangle([140, 20, 1140, 420], radius=22, fill=col["card_bg"], outline=col["accent"], width=2)
    draw.text((640, 55), "PANEL DE ACCESOS RÁPIDOS", fill=col["accent"], font=get_font(18, bold=True), anchor="mm")
    
    # 6 Módulos rápidos (114x101)
    tiles = [
        ("pullmenu/bt.png", "Bluetooth", True),
        ("pullmenu/fm.png", "Radio FM", True),
        ("pullmenu/mute.png", "Silencio", False),
        ("pullmenu/wallpaper.png", "Fondo", False),
        ("pullmenu/tft.png", "Pantalla", False),
        ("pullmenu/aout.png", "Salida Audio", True)
    ]
    for i, (rel_p, name, is_on) in enumerate(tiles):
        tx = 200 + (i % 3) * 300
        ty = 100 + (i // 3) * 140
        t_img = load_theme_img(theme, rel_p)
        paste_safe(im, t_img, (tx, ty), target_size=(114, 101))
        tcol = col["accent"] if is_on else col["text"]
        draw.text((tx + 57, ty + 115), name, fill=tcol, font=get_font(14, bold=True), anchor="mm")
        
    # Barra de brillo inferior
    draw.text((200, 380), "Brillo TFT:", fill=col["text_sub"], font=get_font(15, bold=True), anchor="lm")
    draw.rounded_rectangle([320, 372, 1020, 388], radius=8, fill=(40, 50, 65, 200), outline=col["border"])
    draw.rounded_rectangle([320, 372, 850, 388], radius=8, fill=col["accent"])
    draw.ellipse([840, 366, 864, 394], fill=(255, 255, 255, 255))
    draw.text((1050, 380), "75%", fill=col["accent"], font=get_font(15, bold=True), anchor="lm")
    
    return im

# 8. Vista Standby (Reloj de espera)
def render_view_standby(theme):
    im = Image.new("RGBA", (UI_WIDTH, UI_HEIGHT), (8, 10, 14, 255))
    draw = ImageDraw.Draw(im)
    col = get_theme_colors(theme)
    
    # Fondo sutil del tema
    bg_p = os.path.join(THEMES_DIR, theme, "appres", "img", "setting", "bg0.png")
    if os.path.exists(bg_p):
        wall = Image.open(bg_p).convert("RGBA").filter(ImageFilter.GaussianBlur(10))
        dark = Image.new("RGBA", (UI_WIDTH, UI_HEIGHT), (0, 0, 0, 200))
        wall.paste(dark, (0, 0), dark)
        im.paste(wall, (0, 0))
        
    # Esfera del reloj analógico (standby/bg.png)
    clock_bg = load_theme_img(theme, "standby/bg.png")
    cx, cy = 640, 210
    paste_safe(im, clock_bg, (cx, cy), anchor="center", target_size=(260, 260))
    
    # Manecillas (hour, minute, second)
    hour = load_theme_img(theme, "standby/hour.png")
    minute = load_theme_img(theme, "standby/minute.png")
    second = load_theme_img(theme, "standby/second.png")
    paste_safe(im, hour, (cx, cy - 35), anchor="center")
    paste_safe(im, minute, (cx, cy - 45), anchor="center")
    paste_safe(im, second, (cx, cy - 50), anchor="center")
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=col["accent"])
    
    # Reloj digital y fecha inferior
    now = datetime.datetime.now()
    draw.text((cx, 375), now.strftime("%H:%M:%S"), fill=col["text"], font=get_font(38, bold=True), anchor="mm")
    draw.text((cx, 420), now.strftime("%A, %d de %B de %Y"), fill=col["accent_sub"], font=get_font(16, bold=False), anchor="mm")
    
    return im

# Mosaico resumen de todas las vistas
def create_summary_collage(theme, views_dict, out_path):
    # Cuadrícula de 4x2 vistas
    vw, vh = 640, 240
    cw, ch = vw * 2, vh * 4 + 80
    canvas = Image.new("RGB", (cw, ch), (12, 14, 18))
    draw = ImageDraw.Draw(canvas)
    col = get_theme_colors(theme)
    
    # Cabecera
    draw.text((cw // 2, 40), f"CATÁLOGO DE VISTAS - TEMA: {col['name'].upper()}", fill=col["accent"], font=get_font(26, bold=True), anchor="mm")
    
    order = [
        ("01. Escritorio Principal", "01_escritorio"),
        ("02. Menú de Ajustes", "02_ajustes"),
        ("03. Reproductor Música", "03_musica"),
        ("04. Teléfono Bluetooth", "04_telefono_bluetooth"),
        ("05. Radio FM Transmisor", "05_radio_fm"),
        ("06. Ecualizador DSP", "06_ecualizador"),
        ("07. Cortina Pullmenu", "07_cortina_pullmenu"),
        ("08. Reloj Standby", "08_reloj_standby"),
    ]
    
    for i, (title, key) in enumerate(order):
        c = i % 2
        r = i // 2
        vx = c * vw
        vy = 80 + r * vh
        
        v_img = views_dict[key].resize((vw - 8, vh - 26), Image.Resampling.LANCZOS)
        canvas.paste(v_img, (vx + 4, vy + 22))
        draw.text((vx + 14, vy + 12), title, fill=(230, 235, 245), font=get_font(13, bold=True), anchor="lm")
        draw.rectangle([vx + 2, vy + 20, vx + vw - 4, vy + vh - 2], outline=col["border"], width=1)
        
    canvas.save(out_path, format="JPEG", quality=92)

def generate_previews_for_theme(theme):
    print(f"\nGenerando capturas de vistas para tema: {theme.upper()}...")
    vistas_dir = os.path.join(THEMES_DIR, theme, "vistas")
    os.makedirs(vistas_dir, exist_ok=True)
    
    views = {
        "01_escritorio": render_view_desktop(theme),
        "02_ajustes": render_view_setting(theme),
        "03_musica": render_view_music(theme),
        "04_telefono_bluetooth": render_view_bt(theme),
        "05_radio_fm": render_view_fm(theme),
        "06_ecualizador": render_view_eq(theme),
        "07_cortina_pullmenu": render_view_pullmenu(theme),
        "08_reloj_standby": render_view_standby(theme),
    }
    
    for name, img in views.items():
        save_p = os.path.join(vistas_dir, f"{name}.png")
        img.save(save_p, format="PNG", optimize=True)
        print(f"  [+] Vista generada: {name}.png")
        
    summary_p = os.path.join(vistas_dir, "00_resumen_todas_las_vistas.jpg")
    create_summary_collage(theme, views, summary_p)
    print(f"  [+] Mosaico panorámico generado: 00_resumen_todas_las_vistas.jpg")

if __name__ == "__main__":
    themes = sys.argv[1:] if len(sys.argv) > 1 else ["tactical", "stealth", "cyber"]
    for t in themes:
        generate_previews_for_theme(t)
    print("\n[OK] ¡Todas las vistas generadas con éxito en cada carpeta temática!")
