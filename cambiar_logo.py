#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
 F133 Boot Logo & Firmware Customizer (10.26" Screen - 1600x600)
================================================================================
 Herramienta automatizada para personalizar:
   1. Logo de Arranque (Boot Logo a pantalla completa 1600x600)
   2. Nombre de Bluetooth (BT Name)
   3. Idioma por Defecto (Language)
   4. Sonido de Encendido (Silencio a 0dB o archivo de audio personalizado)
   5. Información de Versión del Sistema
   6. Estilo de Interfaz Visual (Stealth Luxe, Tactical Off-Road, Cyber Sport)
   7. Insignia Vehicular (Marca, Modelo, Subtítulo y Logo con remoción de fondo)
================================================================================
"""

import sys
import os
import struct
import io
import wave
import configparser
import argparse
import math
import json
import datetime
import shutil

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    print("\n[ERROR] Se requiere la librería Pillow (PIL).")
    print("Por favor instálala ejecutando: pip install Pillow\n")
    sys.exit(1)

# Rutas del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MINFS_DIR = os.path.join(ASSETS_DIR, "minfs_extracted")
BASE_IMG_PATH = os.path.join(ASSETS_DIR, "base_img", "melis_f133-b-pnd-16M-board_uart0_16Mnor.img")
ORIG_FEX_DIR = os.path.join(ASSETS_DIR, "extracted_fex")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
USB_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "F133_IMG")
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")
LOGOS_DIR = os.path.join(BASE_DIR, "logos")
THEMES_DIR = os.path.join(BASE_DIR, "themes")

# Constantes de Hardware de la pantalla 10.26"
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 600
UI_WIDTH = 1280
UI_HEIGHT = 480
MIPI_ROTATION = 270  # Rotación física del bus MIPI DSI (600x1600 vertical)
PARTITION_SIZE = 13303808  # 13 MB exactos de la partición data_udisk

IDIOMAS_MAP = {
    0: "Chino Simplificado",
    1: "Chino Tradicional",
    2: "English",
    3: "Español",
    4: "Ruso",
    5: "Francés",
    6: "Alemán",
    7: "Italiano",
    8: "Portugués",
    9: "Polaco",
    10: "Turco",
    17: "Coreano",
    18: "Japonés"
}

THEMES_MAP = {
    "original": "Original de Fábrica (Stock Firmware)",
    "factory": "Original de Fábrica (Stock Firmware)",
    "stealth": "Stealth Luxe / Monocromo Titanio",
    "tactical": "Tactical Off-Road / 4x4 Aventura",
    "cyber": "Cyber Sport / Neón Dinámico"
}

def print_banner():
    print("=" * 75)
    print("   🚗 F133 BOOT LOGO & FIRMWARE CUSTOMIZER (10.26\" 1600x600)")
    print("   Desarrollado por: Diego Sagredo Ailef")
    print("   GitHub: https://github.com/diegosagredo911")
    print("=" * 75)

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

def load_configuration():
    config = configparser.ConfigParser()
    settings = {
        "theme_style": "stealth",
        "brand": "MITSUBISHI",
        "model": "L200 KATANA",
        "subtitle": "4X4 TURBO DIESEL",
        "logo_file": "logos/mitsubishi.png",
        "tint_logo": True,
        "bt_name": "L200",
        "language": 3,
        "version_str": "DIEGO SAGREDO EDITION 2026",
        "sound_mode": "silencio",
        "sound_file": "custom_sound.wav"
    }

    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding="utf-8")
        if config.has_section("interfaz"):
            st = config.get("interfaz", "estilo", fallback=settings["theme_style"]).strip().lower()
            if st in THEMES_MAP:
                settings["theme_style"] = st
        if config.has_section("vehiculo"):
            settings["brand"] = config.get("vehiculo", "marca", fallback=settings["brand"]).strip()
            settings["model"] = config.get("vehiculo", "modelo", fallback=settings["model"]).strip()
            settings["subtitle"] = config.get("vehiculo", "subtitulo", fallback=settings["subtitle"]).strip()
            settings["logo_file"] = config.get("vehiculo", "archivo_logo", fallback=settings["logo_file"]).strip()
            arm = config.get("vehiculo", "armonizar_color_logo", fallback="si").strip().lower()
            settings["tint_logo"] = (arm in ["si", "yes", "true", "1"])
        if config.has_section("bluetooth"):
            settings["bt_name"] = config.get("bluetooth", "nombre", fallback=settings["bt_name"]).strip()
        if config.has_section("sistema"):
            settings["language"] = config.getint("sistema", "idioma", fallback=settings["language"])
            settings["version_str"] = config.get("sistema", "version_texto", fallback=settings["version_str"]).strip()
        if config.has_section("sonido"):
            settings["sound_mode"] = config.get("sonido", "modo", fallback=settings["sound_mode"]).strip().lower()
            settings["sound_file"] = config.get("sonido", "archivo", fallback=settings["sound_file"]).strip()

    return settings

def find_input_image(cli_image=None):
    if cli_image and os.path.exists(cli_image):
        return cli_image

    candidates = ["custom_logo.png", "custom_logo.jpg", "custom_logo.jpeg", "logo.png", "logo.jpg"]
    for c in candidates:
        full_path = os.path.join(BASE_DIR, c)
        if os.path.exists(full_path):
            return full_path

    print("\n[!] No se encontró ninguna imagen de arranque para procesar.")
    print("    Por favor coloca tu imagen en esta carpeta como:")
    print("    -> custom_logo.png  (o custom_logo.jpg)")
    print("    o pásala como argumento: python3 cambiar_logo.py --image mi_foto.jpg\n")
    sys.exit(1)

def process_logo(input_image_path):
    print(f"\n[1/6] Procesando imagen de arranque: {os.path.basename(input_image_path)}")
    with Image.open(input_image_path) as im:
        im = im.convert("RGBA")
        src_w, src_h = im.size
        print(f"      • Resolución de origen: {src_w}x{src_h} px")

        canvas = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0, 255))
        ratio = min(SCREEN_WIDTH / src_w, SCREEN_HEIGHT / src_h)
        new_w = int(src_w * ratio)
        new_h = int(src_h * ratio)
        
        resized = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
        offset_x = (SCREEN_WIDTH - new_w) // 2
        offset_y = (SCREEN_HEIGHT - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y), resized)

        landscape_full = canvas.convert("RGB")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        preview_path = os.path.join(OUTPUT_DIR, "vista_previa_pantalla.jpg")
        landscape_full.save(preview_path, format="JPEG", quality=95)
        print(f"      • Vista previa de arranque: {os.path.relpath(preview_path, BASE_DIR)}")

        vertical_mipi = landscape_full.rotate(MIPI_ROTATION, expand=True)
        print(f"      • Rotación nativa MIPI DSI aplicada: {vertical_mipi.size} px")

        target_bin = os.path.join(MINFS_DIR, "res", "stalogo0.bin")
        vertical_mipi.save(target_bin, format="JPEG", quality=85, progressive=False, optimize=True)
        file_size = os.path.getsize(target_bin)
        print(f"      • stalogo0.bin actualizado ({file_size / 1024:.1f} KB)")

def process_sound(sound_mode, sound_file):
    print(f"\n[2/6] Configurando sonido de encendido...")
    target_wav = os.path.join(MINFS_DIR, "res", "sounds", "chord.wav")
    os.makedirs(os.path.dirname(target_wav), exist_ok=True)

    custom_path = os.path.join(BASE_DIR, sound_file)

    if sound_mode == "archivo" and os.path.exists(custom_path):
        print(f"      • Convirtiendo archivo personalizado: {sound_file}")
        try:
            with wave.open(custom_path, 'rb') as src:
                in_channels = src.getnchannels()
                in_sampwidth = src.getsampwidth()
                in_framerate = src.getframerate()
                in_nframes = src.getnframes()
                raw_frames = src.readframes(in_nframes)

            total_samples = in_nframes * in_channels
            if in_sampwidth == 1:
                fmt = f"{total_samples}B"
                raw_ints = struct.unpack(fmt, raw_frames)
                floats = [(x - 128) / 128.0 for x in raw_ints]
            elif in_sampwidth == 2:
                fmt = f"<{total_samples}h"
                raw_ints = struct.unpack(fmt, raw_frames)
                floats = [x / 32768.0 for x in raw_ints]
            elif in_sampwidth == 3:
                floats = []
                for i in range(0, len(raw_frames), 3):
                    b = raw_frames[i:i+3]
                    floats.append(int.from_bytes(b, byteorder='little', signed=True) / 8388608.0)
            elif in_sampwidth == 4:
                fmt = f"<{total_samples}i"
                raw_ints = struct.unpack(fmt, raw_frames)
                floats = [x / 2147483648.0 for x in raw_ints]
            else:
                floats = [0.0] * total_samples

            if in_channels == 1:
                left = floats
                right = floats
            else:
                left = floats[0::in_channels]
                right = floats[1::in_channels]

            out_rate = 44100
            if in_framerate != out_rate:
                resample_ratio = out_rate / in_framerate
                out_len = int(len(left) * resample_ratio)
                new_left = []
                new_right = []
                for i in range(out_len):
                    src_idx = i / resample_ratio
                    i0 = int(src_idx)
                    i1 = min(i0 + 1, len(left) - 1)
                    frac = src_idx - i0
                    new_left.append(left[i0] * (1.0 - frac) + left[i1] * frac)
                    new_right.append(right[i0] * (1.0 - frac) + right[i1] * frac)
                left, right = new_left, new_right

            max_frames = int(out_rate * 6.0)
            left = left[:max_frames]
            right = right[:max_frames]

            out_bytes = bytearray()
            for l, r in zip(left, right):
                li = int(max(-1.0, min(1.0, l)) * 32767.0)
                ri = int(max(-1.0, min(1.0, r)) * 32767.0)
                out_bytes.extend(struct.pack('<hh', li, ri))

            with wave.open(target_wav, 'wb') as dst:
                dst.setnchannels(2)
                dst.setsampwidth(2)
                dst.setframerate(out_rate)
                dst.writeframes(out_bytes)

            print(f"      • Sonido personalizado integrado (44.1kHz Estéreo, {len(left)/out_rate:.2f}s)")
            return
        except Exception as e:
            print(f"      [!] Error al convertir {sound_file}: {e}")
            print("      • Aplicando modo silencio por seguridad.")

    with wave.open(target_wav, 'wb') as dst:
        dst.setnchannels(2)
        dst.setsampwidth(2)
        dst.setframerate(44100)
        dst.writeframes(b'\x00' * 5200)
    print("      • Sonido de encendido configurado a 0dB digital (100% Silencioso).")

def process_system_configs(bt_name, lang_id, version_str):
    lang_name = IDIOMAS_MAP.get(lang_id, f"ID {lang_id}")
    now = datetime.datetime.now()
    cur_year = now.year
    cur_month = now.month
    cur_day = now.day
    date_display = now.strftime("%d/%m/%Y")

    print(f"\n[3/6] Aplicando configuraciones de sistema:")
    print(f"      • Nombre de Bluetooth: '{bt_name}'")
    print(f"      • Idioma por defecto: {lang_name} ({lang_id})")
    print(f"      • Versión de sistema:  '{version_str}'")
    print(f"      • Fecha inicial del sistema (RTC): {date_display} (Sincronizada a la compilación)")

    fex_path = os.path.join(MINFS_DIR, "app_config.fex")
    if os.path.exists(fex_path):
        with open(fex_path, "r", encoding="gbk", errors="ignore") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.strip().startswith("bt_name ="):
                new_lines.append(f"bt_name =string:{bt_name}\n")
            elif line.strip().startswith("language="):
                new_lines.append(f"language={lang_id}\n")
            elif line.strip().startswith("version ="):
                new_lines.append(f"version =string:{version_str}\n")
            elif line.strip().startswith("year="):
                new_lines.append(f"year={cur_year}\n")
            elif line.strip().startswith("month="):
                new_lines.append(f"month={cur_month}\n")
            elif line.strip().startswith("day="):
                new_lines.append(f"day={cur_day}\n")
            else:
                new_lines.append(line)
        with open(fex_path, "w", encoding="gbk", errors="ignore") as f:
            f.writelines(new_lines)

    bin_path = os.path.join(MINFS_DIR, "app_config.bin")
    if os.path.exists(bin_path):
        with open(bin_path, "rb") as f:
            bdata = bytearray(f.read())

        bt_bytes = bt_name.encode("latin1", errors="ignore")[:8]
        bdata[4772:4780] = bt_bytes + b"\x00" * (8 - len(bt_bytes))
        bdata[4636:4640] = struct.pack("<I", int(lang_id))
        v_bytes = version_str.encode("latin1", errors="ignore")[:31]
        bdata[4436:4468] = v_bytes + b"\x00" * (32 - len(v_bytes))

        # Actualizar fecha inicial RTC (año, mes, día)
        bdata[4756:4760] = struct.pack("<I", cur_year)
        bdata[4760:4764] = struct.pack("<I", cur_month)
        bdata[4764:4768] = struct.pack("<I", cur_day)

        with open(bin_path, "wb") as f:
            f.write(bdata)

    # Actualizar fecha en headbar.json
    headbar_json_path = os.path.join(MINFS_DIR, "appres", "layout", "headbar", "headbar.json")
    if os.path.exists(headbar_json_path):
        try:
            with open(headbar_json_path, "r", encoding="utf-8") as f:
                hb_layout = json.load(f)
            if "label-010" in hb_layout:
                hb_layout["label-010"]["text"] = f"{cur_day:02d}/{cur_month:02d}/{cur_year}"
            with open(headbar_json_path, "w", encoding="utf-8") as f:
                json.dump(hb_layout, f, indent=4)
        except Exception:
            pass

# ----------------------------------------------------------------------
# PROCESADOR DE LOGOS Y ELIMINACIÓN INTELIGENTE DE FONDO
# ----------------------------------------------------------------------
def auto_remove_background(im, tolerance=32):
    im = im.convert("RGBA")
    w, h = im.size
    alpha = im.split()[-1]
    hist = alpha.histogram()
    if sum(hist[:128]) > (w * h * 0.05):
        return im

    corners = [
        im.getpixel((0, 0))[:3],
        im.getpixel((w - 1, 0))[:3],
        im.getpixel((0, h - 1))[:3],
        im.getpixel((w - 1, h - 1))[:3],
        im.getpixel((2, 2))[:3],
        im.getpixel((w - 3, 2))[:3],
        im.getpixel((2, h - 3))[:3],
        im.getpixel((w - 3, h - 3))[:3],
    ]
    bg_r = sum(c[0] for c in corners) // len(corners)
    bg_g = sum(c[1] for c in corners) // len(corners)
    bg_b = sum(c[2] for c in corners) // len(corners)

    pixels = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            dist = math.sqrt((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2)
            if dist < tolerance:
                pixels[x, y] = (r, g, b, 0)
            elif dist < tolerance + 25:
                frac = (dist - tolerance) / 25.0
                pixels[x, y] = (r, g, b, int(255 * frac))
    return im

def adapt_brand_logo(logo_path, target_size=(46, 36), tint_color=None):
    if not logo_path or not os.path.exists(logo_path):
        return None
    raw_im = Image.open(logo_path)
    cleaned = auto_remove_background(raw_im)
    bbox = cleaned.getbbox()
    if not bbox:
        return None
    trimmed = cleaned.crop(bbox)
    src_w, src_h = trimmed.size
    tgt_w, tgt_h = target_size
    scale = min(tgt_w / src_w, tgt_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized = trimmed.resize((new_w, new_h), Image.Resampling.LANCZOS)

    if tint_color is not None:
        r, g, b, a = resized.split()
        gray = resized.convert('L')
        tint_img = Image.new("RGBA", (new_w, new_h), tint_color)
        t_alpha = bytearray()
        g_bytes = gray.tobytes()
        a_bytes = a.tobytes()
        for ga, al in zip(g_bytes, a_bytes):
            val = int((al / 255.0) * min(255, max(60, int(ga * 1.25))))
            t_alpha.append(val)
        tint_img.putalpha(Image.frombytes('L', (new_w, new_h), bytes(t_alpha)))
        return tint_img
    return resized

def draw_vector_brand_fallback(draw, brand_name, cx, cy, size, color):
    b = brand_name.upper().strip()
    if "TOYOTA" in b:
        w, h = int(size * 1.0), int(size * 0.7)
        draw.ellipse([cx - w, cy - h, cx + w, cy + h], outline=color, width=3)
        draw.ellipse([cx - int(w*0.75), cy - int(h*0.75), cx + int(w*0.75), cy + int(h*0.3)], outline=color, width=3)
        draw.ellipse([cx - int(w*0.35), cy - int(h*0.8), cx + int(w*0.35), cy + int(h*0.75)], outline=color, width=3)
    elif "FORD" in b:
        w, h = int(size * 1.1), int(size * 0.65)
        draw.ellipse([cx - w, cy - h, cx + w, cy + h], outline=color, width=3)
        draw.text((cx, cy), "Ford", fill=color, font=get_font(int(size*0.8), bold=True), anchor="mm")
    else:
        # Default: Mitsubishi 3-Diamonds
        r = size * 0.95
        d1 = [(cx, cy), (cx - r*0.38, cy - r*0.48), (cx, cy - r*0.96), (cx + r*0.38, cy - r*0.48)]
        draw.polygon(d1, fill=color)
        def rotate_pt(pt, deg):
            rad = math.radians(deg)
            x = pt[0] - cx
            y = pt[1] - cy
            rx = x * math.cos(rad) - y * math.sin(rad)
            ry = x * math.sin(rad) + y * math.cos(rad)
            return (cx + rx, cy + ry)
        d2 = [rotate_pt(pt, 120) for pt in d1]
        d3 = [rotate_pt(pt, 240) for pt in d1]
        draw.polygon(d2, fill=color)
        draw.polygon(d3, fill=color)

def save_minfs_p_png(im_rgba, target_path):
    im_p = im_rgba.quantize(colors=255)
    im_p.save(target_path, format="PNG", optimize=True)

def get_theme_palette(style="stealth"):
    if style == "stealth":
        return {
            "name": "Stealth Luxe / Monocromo Titanio",
            "accent": (220, 225, 235, 255),
            "accent_sub": (175, 185, 200, 255),
            "bg_normal": (16, 20, 28, 225),
            "bg_pressed": (28, 38, 54, 245),
            "border_normal": (55, 68, 85, 255),
            "border_pressed": (220, 225, 235, 255),
            "glyph_normal": (205, 215, 225, 240),
            "glyph_pressed": (255, 255, 255, 255),
            "card_bg": (14, 18, 26, 230),
            "radius": 18,
            "tactical_notch": False,
        }
    elif style == "tactical":
        return {
            "name": "Tactical Off-Road / 4x4 Aventura",
            "accent": (212, 255, 0, 255),
            "accent_sub": (180, 195, 75, 255),
            "bg_normal": (18, 24, 22, 235),
            "bg_pressed": (34, 46, 36, 250),
            "border_normal": (65, 80, 60, 255),
            "border_pressed": (212, 255, 0, 255),
            "glyph_normal": (185, 205, 170, 235),
            "glyph_pressed": (212, 255, 0, 255),
            "card_bg": (16, 22, 20, 240),
            "radius": 6,
            "tactical_notch": True,
        }
    else: # cyber
        return {
            "name": "Cyber Sport / Neón Dinámico",
            "accent": (0, 235, 255, 255),
            "accent_sub": (255, 0, 110, 255),
            "bg_normal": (14, 18, 34, 235),
            "bg_pressed": (26, 36, 72, 250),
            "border_normal": (40, 65, 110, 255),
            "border_pressed": (0, 235, 255, 255),
            "glyph_normal": (165, 225, 255, 240),
            "glyph_pressed": (255, 0, 110, 255),
            "card_bg": (12, 16, 30, 240),
            "radius": 14,
            "tactical_notch": False,
        }

def tint_glyph_from_image(im_rgba, target_color):
    gray = im_rgba.convert("L")
    w, h = im_rgba.size
    tinted = Image.new("RGBA", (w, h), target_color[:3] + (0,))
    t_alpha = bytearray()
    g_bytes = gray.tobytes()
    a_bytes = im_rgba.split()[3].tobytes()
    for ga, al in zip(g_bytes, a_bytes):
        if al > 15:
            val = int((al / 255.0) * min(255, int(ga * 1.25)))
            t_alpha.append(val)
        else:
            t_alpha.append(0)
    tinted.putalpha(Image.frombytes("L", (w, h), bytes(t_alpha)))
    return tinted

def draw_styled_button(size=(126, 126), pressed=False, style="stealth"):
    w, h = size
    pal = get_theme_palette(style)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bg_col = pal["bg_pressed"] if pressed else pal["bg_normal"]
    border_col = pal["border_pressed"] if pressed else pal["border_normal"]
    
    if pal["tactical_notch"]:
        d.rectangle([2, 2, w - 2, h - 2], fill=bg_col, outline=border_col, width=2 if pressed else 1)
        k = min(12, w//4, h//4)
        acc = pal["accent"]
        d.line([(2, 2), (2 + k, 2)], fill=acc, width=2)
        d.line([(2, 2), (2, 2 + k)], fill=acc, width=2)
        d.line([(w - 2, 2), (w - 2 - k, 2)], fill=acc, width=2)
        d.line([(w - 2, 2), (w - 2, 2 + k)], fill=acc, width=2)
        d.line([(2, h - 2), (2 + k, h - 2)], fill=acc, width=2)
        d.line([(2, h - 2), (2, h - 2 - k)], fill=acc, width=2)
        d.line([(w - 2, h - 2), (w - 2 - k, h - 2)], fill=acc, width=2)
        d.line([(w - 2, h - 2), (w - 2, h - 2 - k)], fill=acc, width=2)
    else:
        rad = min(pal["radius"], w//3, h//3)
        d.rounded_rectangle([2, 2, w - 2, h - 2], radius=rad, fill=bg_col, outline=border_col, width=2 if pressed else 1)
        if style == "stealth":
            d.arc([4, 4, w - 4, max(8, h//2 + 2)], start=180, end=0, fill=(255, 255, 255, 40), width=1)
        elif style == "cyber":
            d.line([(w//4, h - 3), (w - w//4, h - 3)], fill=pal["accent_sub"], width=2)
    return im, d

generate_base_button = draw_styled_button

def inject_desktop_extras(style="stealth"):
    desktop_dir = os.path.join(MINFS_DIR, "appres", "img", "desktop")
    pal = get_theme_palette(style)
    
    # 1. Tarjeta multimedia central desktop_bg.png (394x222)
    bg_card = Image.new("RGBA", (394, 222), (0, 0, 0, 0))
    d = ImageDraw.Draw(bg_card)
    w, h = 394, 222
    if pal["tactical_notch"]:
        d.rectangle([3, 3, w - 3, h - 3], fill=pal["card_bg"], outline=pal["border_normal"], width=2)
        acc = pal["accent"]
        d.line([(3, 3), (25, 3)], fill=acc, width=3)
        d.line([(3, 3), (3, 25)], fill=acc, width=3)
        d.line([(w - 3, 3), (w - 25, 3)], fill=acc, width=3)
        d.line([(w - 3, 3), (w - 3, 25)], fill=acc, width=3)
        d.line([(3, h - 3), (25, h - 3)], fill=acc, width=3)
        d.line([(3, h - 3), (3, h - 25)], fill=acc, width=3)
        d.line([(w - 3, h - 3), (w - 25, h - 3)], fill=acc, width=3)
        d.line([(w - 3, h - 3), (w - 3, h - 25)], fill=acc, width=3)
        d.line([(18, 142), (w - 18, 142)], fill=(65, 80, 60, 200), width=1)
    elif style == "stealth":
        d.rounded_rectangle([3, 3, w - 3, h - 3], radius=20, fill=pal["card_bg"], outline=pal["border_normal"], width=2)
        d.arc([8, 8, w - 8, 80], start=180, end=0, fill=(255, 255, 255, 35), width=1)
        d.line([(24, 142), (w - 24, 142)], fill=(55, 68, 85, 160), width=1)
    else: # cyber
        d.rounded_rectangle([3, 3, w - 3, h - 3], radius=16, fill=pal["card_bg"], outline=pal["accent"], width=2)
        d.line([(24, 142), (w - 24, 142)], fill=pal["accent_sub"], width=2)
    save_minfs_p_png(bg_card, os.path.join(desktop_dir, "desktop_bg.png"))
    
    # 2. Controles de reproducción pre / next (40x26)
    for pressed, fname in [(False, "pre.png"), (True, "pre_sel.png")]:
        im = Image.new("RGBA", (40, 26), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        col = pal["glyph_pressed"] if pressed else pal["glyph_normal"]
        d.polygon([(18, 13), (28, 6), (28, 20)], fill=col)
        d.polygon([(8, 13), (18, 6), (18, 20)], fill=col)
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))
        
    for pressed, fname in [(False, "next.png"), (True, "next_sel.png")]:
        im = Image.new("RGBA", (40, 26), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        col = pal["glyph_pressed"] if pressed else pal["glyph_normal"]
        d.polygon([(22, 13), (12, 6), (12, 20)], fill=col)
        d.polygon([(32, 13), (22, 6), (22, 20)], fill=col)
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))

    # 3. Play / Pause (62x62)
    for fname, is_play in [("play.png", True), ("pause.png", False)]:
        im = Image.new("RGBA", (62, 62), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([3, 3, 59, 59], fill=pal["bg_pressed"], outline=pal["accent"], width=2)
        col = pal["accent"] if style != "stealth" else (255, 255, 255, 255)
        if is_play:
            d.polygon([(24, 18), (44, 31), (24, 44)], fill=col)
        else:
            d.rectangle([22, 20, 27, 42], fill=col)
            d.rectangle([35, 20, 40, 42], fill=col)
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))

def inject_headbar_assets(style="stealth"):
    headbar_dir = os.path.join(MINFS_DIR, "appres", "img", "headbar")
    pal = get_theme_palette(style)
    
    # 1. Home button (110x64)
    for pressed, fname in [(False, "home.png"), (True, "home_sel.png")]:
        im, d = draw_styled_button((110, 64), pressed, style)
        col = pal["glyph_pressed"] if pressed else pal["glyph_normal"]
        cx, cy = 55, 32
        d.polygon([(cx, cy - 14), (cx - 16, cy + 1), (cx + 16, cy + 1)], fill=col)
        d.rectangle([cx - 11, cy + 1, cx + 11, cy + 15], fill=col)
        d.rectangle([cx - 3, cy + 6, cx + 3, cy + 15], fill=pal["bg_normal"])
        save_minfs_p_png(im, os.path.join(headbar_dir, fname))
        
    # 2. Back button (110x64)
    for pressed, fname in [(False, "back.png"), (True, "back_sel.png")]:
        im, d = draw_styled_button((110, 64), pressed, style)
        col = pal["glyph_pressed"] if pressed else pal["glyph_normal"]
        cx, cy = 55, 32
        d.polygon([(cx - 12, cy), (cx + 8, cy - 14), (cx + 8, cy + 14)], fill=col)
        d.rectangle([cx + 6, cy - 4, cx + 16, cy + 4], fill=col)
        save_minfs_p_png(im, os.path.join(headbar_dir, fname))

    # 3. Aux button (50x64)
    for pressed, fname in [(False, "btn.png"), (True, "btn_sel.png")]:
        im, d = draw_styled_button((50, 64), pressed, style)
        save_minfs_p_png(im, os.path.join(headbar_dir, fname))
        
    # 4. Status icons tinting
    icons = ["vol.png", "vol_no.png", "bright.png", "night.png", "wifi.png", "wifi_no.png", "bt.png", "bt_no.png"]
    for icon_name in icons:
        path = os.path.join(headbar_dir, icon_name)
        if os.path.exists(path):
            raw = Image.open(path).convert("RGBA")
            target_col = pal["accent"] if not icon_name.endswith("_no.png") else (130, 140, 150, 200)
            tinted = tint_glyph_from_image(raw, target_col)
            save_minfs_p_png(tinted, path)

def inject_setting_assets(style="stealth"):
    setting_dir = os.path.join(MINFS_DIR, "appres", "img", "setting")
    pal = get_theme_palette(style)
    
    # 1. Pestañas de categorías 0.png..9.png y 0_sel.png..9_sel.png (166x62)
    for i in range(10):
        for pressed, suffix in [(False, ".png"), (True, "_sel.png")]:
            fname = f"{i}{suffix}"
            path = os.path.join(setting_dir, fname)
            orig_glyph = None
            if os.path.exists(path):
                orig = Image.open(path).convert("RGBA")
                target_col = pal["glyph_pressed"] if pressed else pal["glyph_normal"]
                orig_glyph = tint_glyph_from_image(orig, target_col)
                
            im, d = draw_styled_button((166, 62), pressed, style)
            if pressed:
                d.line([(4, 10), (4, 52)], fill=pal["accent"], width=4)
            if orig_glyph:
                im.paste(orig_glyph, (0, 0), orig_glyph)
            save_minfs_p_png(im, path)
            
    # 2. Switches / Toggles on.png & off.png (88x37)
    im_off = Image.new("RGBA", (88, 37), (0, 0, 0, 0))
    d_off = ImageDraw.Draw(im_off)
    d_off.rounded_rectangle([2, 2, 86, 35], radius=18, fill=(28, 34, 42, 240), outline=(65, 75, 88, 255), width=2)
    d_off.ellipse([6, 6, 31, 31], fill=(160, 170, 185, 255))
    save_minfs_p_png(im_off, os.path.join(setting_dir, "off.png"))
    
    im_on = Image.new("RGBA", (88, 37), (0, 0, 0, 0))
    d_on = ImageDraw.Draw(im_on)
    acc = pal["accent"]
    d_on.rounded_rectangle([2, 2, 86, 35], radius=18, fill=pal["bg_pressed"], outline=acc, width=2)
    d_on.ellipse([57, 6, 82, 31], fill=acc)
    save_minfs_p_png(im_on, os.path.join(setting_dir, "on.png"))
    
    # 3. Sliders sl_bg.png (572x30), sl_p.png (31x17), sl_sel.png (31x17)
    sl_bg = Image.new("RGBA", (572, 30), (0, 0, 0, 0))
    d_sl = ImageDraw.Draw(sl_bg)
    d_sl.rounded_rectangle([2, 10, 570, 20], radius=5, fill=(24, 30, 38, 240), outline=pal["border_normal"], width=1)
    save_minfs_p_png(sl_bg, os.path.join(setting_dir, "sl_bg.png"))
    
    for fname in ["sl_p.png", "sl_sel.png"]:
        thumb = Image.new("RGBA", (31, 17), (0, 0, 0, 0))
        d_th = ImageDraw.Draw(thumb)
        d_th.rounded_rectangle([2, 1, 29, 15], radius=6, fill=pal["accent"], outline=(255, 255, 255, 240), width=1)
        save_minfs_p_png(thumb, os.path.join(setting_dir, fname))

    # 4. Action buttons: default_btn (155x60), ok (166x62), x (166x62), del (39x22)
    for pressed, fname in [(False, "default_btn.png"), (True, "f_btn_sel.png")]:
        im, d = draw_styled_button((155, 60), pressed, style)
        save_minfs_p_png(im, os.path.join(setting_dir, fname))
        
    for pressed, fname in [(False, "ok.png"), (True, "ok_sel.png")]:
        im, d = draw_styled_button((166, 62), pressed, style)
        col = pal["glyph_pressed"] if pressed else pal["glyph_normal"]
        cx, cy = 83, 31
        d.line([(cx - 16, cy + 2), (cx - 4, cy + 14)], fill=col, width=4)
        d.line([(cx - 4, cy + 14), (cx + 16, cy - 12)], fill=col, width=4)
        save_minfs_p_png(im, os.path.join(setting_dir, fname))

    for pressed, fname in [(False, "x.png"), (True, "x_sel.png")]:
        im, d = draw_styled_button((166, 62), pressed, style)
        col = pal["glyph_pressed"] if pressed else pal["glyph_normal"]
        cx, cy = 83, 31
        d.line([(cx - 12, cy - 12), (cx + 12, cy + 12)], fill=col, width=4)
        d.line([(cx - 12, cy + 12), (cx + 12, cy - 12)], fill=col, width=4)
        save_minfs_p_png(im, os.path.join(setting_dir, fname))

    # Item selection strip item_sel.png (830x50)
    it_sel = Image.new("RGBA", (830, 50), (0, 0, 0, 0))
    d_it = ImageDraw.Draw(it_sel)
    d_it.rectangle([0, 0, 830, 50], fill=(pal["accent"][0], pal["accent"][1], pal["accent"][2], 40))
    d_it.line([(0, 0), (0, 50)], fill=pal["accent"], width=4)
    save_minfs_p_png(it_sel, os.path.join(setting_dir, "item_sel.png"))

def inject_pullmenu_assets(style="stealth"):
    pullmenu_dir = os.path.join(MINFS_DIR, "appres", "img", "pullmenu")
    pal = get_theme_palette(style)
    
    # Quick tiles (114x101)
    tiles = ["bt", "fm", "mute", "wallpaper", "tft", "aout"]
    for tile in tiles:
        for pressed in [False, True]:
            fname = f"{tile}_sel.png" if pressed else f"{tile}.png"
            path = os.path.join(pullmenu_dir, fname)
            orig_glyph = None
            if os.path.exists(path):
                raw = Image.open(path).convert("RGBA")
                target_col = pal["glyph_pressed"] if pressed else pal["glyph_normal"]
                orig_glyph = tint_glyph_from_image(raw, target_col)
                
            im, d = draw_styled_button((114, 101), pressed, style)
            if orig_glyph:
                im.paste(orig_glyph, (0, 0), orig_glyph)
            save_minfs_p_png(im, path)

def inject_eq_assets(style="stealth"):
    eq_dir = os.path.join(MINFS_DIR, "appres", "img", "eq")
    pal = get_theme_palette(style)
    
    # Presets buttons btn.png (155x60), eq_btn.png (127x65)
    for pressed, fname in [(False, "btn.png"), (True, "btn_sel.png")]:
        im, d = draw_styled_button((155, 60), pressed, style)
        save_minfs_p_png(im, os.path.join(eq_dir, fname))
        
    for pressed, fname in [(False, "eq_btn.png"), (True, "eq_btn_sel.png")]:
        im, d = draw_styled_button((127, 65), pressed, style)
        save_minfs_p_png(im, os.path.join(eq_dir, fname))

    # Loud on / off (79x34)
    for is_on, fname in [(False, "loud_off.png"), (True, "loud_on.png")]:
        im, d = draw_styled_button((79, 34), is_on, style)
        col = pal["accent"] if is_on else pal["glyph_normal"]
        d.text((39, 17), "LOUD", fill=col, anchor="mm")
        save_minfs_p_png(im, os.path.join(eq_dir, fname))

def inject_secondary_views_theme(style="stealth"):
    """Tinta y estiliza las 14 carpetas secundarias de la interfaz para cobertura visual del 100%."""
    pal = get_theme_palette(style)
    subdirs = ["audio", "auxin", "bt", "calculator", "calendar", "calibrate", "dialog", "explorer", "link", "movie", "music", "photo", "standby", "videoin"]
    base_img = os.path.join(MINFS_DIR, "appres", "img")
    
    count = 0
    for d in subdirs:
        dir_path = os.path.join(base_img, d)
        if not os.path.exists(dir_path):
            continue
        for f in os.listdir(dir_path):
            if f.endswith(".png"):
                p = os.path.join(dir_path, f)
                try:
                    raw = Image.open(p).convert("RGBA")
                    is_pressed = "_sel" in f or "on" in f or "sel" in f
                    target_col = pal["glyph_pressed"] if is_pressed else pal["glyph_normal"]
                    tinted = tint_glyph_from_image(raw, target_col)
                    save_minfs_p_png(tinted, p)
                    count += 1
                except Exception:
                    pass
    return count

def inject_physical_ui_assets(style="cyber"):
    desktop_dir = os.path.join(MINFS_DIR, "appres", "img", "desktop")
    setting_dir = os.path.join(MINFS_DIR, "appres", "img", "setting")
    handset_file = os.path.join(ASSETS_DIR, "phone_handset.png")
    bg2_file = os.path.join(setting_dir, "bg2.jpg")

    pal = get_theme_palette(style)
    accent = pal["accent"]
    accent_sub = pal["accent_sub"]

    # 1. Fondo predeterminado bg0.jpg configurado a Fibra de Carbono limpio de fábrica
    factory_carbon = os.path.join(THEMES_DIR, "factory_backup", "appres", "img", "setting", "bg0.jpg")
    if not os.path.exists(factory_carbon):
        factory_carbon = os.path.join(setting_dir, "bg0.jpg")
    if os.path.exists(factory_carbon):
        bg0_jpg = os.path.join(setting_dir, "bg0.jpg")
        shutil.copy2(factory_carbon, bg0_jpg)
        carbon_im = Image.open(factory_carbon)
        carbon_im.save(os.path.join(setting_dir, "bg0.png"))
        thumb = carbon_im.resize((140, 70), Image.Resampling.LANCZOS)
        thumb.save(os.path.join(setting_dir, "small_bg0.png"))
        print("      • Fondo de pantalla inicial (bg0.jpg) configurado a Fibra de Carbono limpio de fábrica.")

    # 2. Ícono de Teléfono (desktop_Bt.png / desktop_Bt_sel.png)
    for pressed, fname in [(False, "desktop_Bt.png"), (True, "desktop_Bt_sel.png")]:
        im, draw = generate_base_button((126, 126), pressed, style)
        icx, icy = 63, 63
        if os.path.exists(handset_file):
            raw_h = Image.open(handset_file).convert("RGBA")
            h_size = 54
            smooth_h = raw_h.resize((h_size*2, h_size*2), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(0.5)).resize((h_size, h_size), Image.Resampling.LANCZOS)
            im.paste(smooth_h, (icx - h_size//2, icy - h_size//2), smooth_h)
        else:
            draw.ellipse([icx - 10, icy - 16, icx + 16, icy - 2], fill=(255, 255, 255, 240))
            draw.ellipse([icx - 16, icy + 2, icx + 10, icy + 16], fill=(255, 255, 255, 240))
            draw.line([(icx - 8, icy - 12), (icx - 12, icy + 10)], fill=(255, 255, 255, 240), width=8)
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))
    print("      • Ícono de Teléfono oficial inyectado en MINFS (reemplazando el runa Bluetooth).")

    # 3. Ícono de Calculadora (desktop_Calculator.png / desktop_Calculator_sel.png)
    for pressed, fname in [(False, "desktop_Calculator.png"), (True, "desktop_Calculator_sel.png")]:
        im, draw = generate_base_button((126, 126), pressed, style)
        icx, icy = 63, 63
        w, h = 26, 34
        draw.rounded_rectangle([icx - w, icy - h, icx + w, icy + h], radius=8, outline=(255, 255, 255, 240), width=3)
        draw.rounded_rectangle([icx - w + 5, icy - h + 5, icx + w - 5, icy - h + 18], radius=3, outline=(255, 255, 255, 240), width=2)
        btn_acc = accent if pressed else accent_sub
        draw.rounded_rectangle([icx + 4, icy + 15, icx + 18, icy + 26], radius=4, fill=btn_acc)
        for r_y in [icy - 4, icy + 7]:
            for c_x in [icx - 15, icx - 2, icx + 11]:
                draw.ellipse([c_x - 3, r_y - 3, c_x + 3, r_y + 3], outline=(255, 255, 255, 220), width=2)
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))
    print("      • Ícono de Calculadora moderna inyectado en MINFS.")

    # 4. Ícono de Audio (desktop_Audio.png / desktop_Audio_sel.png)
    for pressed, fname in [(False, "desktop_Audio.png"), (True, "desktop_Audio_sel.png")]:
        im, draw = generate_base_button((126, 126), pressed, style)
        icx, icy = 63, 63
        draw.ellipse([icx - 18, icy + 8, icx - 2, icy + 22], fill=(255, 255, 255, 240))
        draw.ellipse([icx + 6, icy + 3, icx + 22, icy + 17], fill=(255, 255, 255, 240))
        draw.line([(icx - 2, icy + 14), (icx - 2, icy - 18)], fill=(255, 255, 255, 240), width=4)
        draw.line([(icx + 22, icy + 9), (icx + 22, icy - 24)], fill=(255, 255, 255, 240), width=4)
        draw.polygon([(icx - 2, icy - 14), (icx + 22, icy - 20), (icx + 22, icy - 26), (icx - 2, icy - 20)], fill=(255, 255, 255, 240))
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))

    # 5. Ícono de USB (desktop_Usb.png / desktop_Usb_sel.png)
    for pressed, fname in [(False, "desktop_Usb.png"), (True, "desktop_Usb_sel.png")]:
        im, draw = generate_base_button((126, 126), pressed, style)
        icx, icy = 63, 63
        draw.line([(icx, icy + 22), (icx, icy - 16)], fill=(255, 255, 255, 240), width=4)
        draw.ellipse([icx - 5, icy + 18, icx + 5, icy + 28], fill=(255, 255, 255, 240))
        draw.polygon([(icx, icy - 26), (icx - 7, icy - 16), (icx + 7, icy - 16)], fill=(255, 255, 255, 240))
        draw.line([(icx, icy + 8), (icx - 14, icy - 2), (icx - 14, icy - 12)], fill=(255, 255, 255, 240), width=3)
        draw.ellipse([icx - 19, icy - 17, icx - 9, icy - 7], fill=(255, 255, 255, 240))
        draw.line([(icx, icy + 4), (icx + 14, icy - 6), (icx + 14, icy - 16)], fill=(255, 255, 255, 240), width=3)
        draw.rectangle([icx + 10, icy - 21, icx + 18, icy - 13], fill=(255, 255, 255, 240))
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))

    # 6. Ícono de SD (desktop_SD.png / desktop_SD_sel.png)
    for pressed, fname in [(False, "desktop_SD.png"), (True, "desktop_SD_sel.png")]:
        im, draw = generate_base_button((126, 126), pressed, style)
        icx, icy = 63, 63
        x0, y0, x1, y1 = icx - 24, icy - 30, icx + 24, icy + 30
        draw.polygon([(x0, y0 + 12), (x0 + 12, y0), (x1, y0), (x1, y1), (x0, y1)], outline=(255, 255, 255, 240), width=3)
        draw.text((icx, icy + 6), "SD", fill=(255, 255, 255, 240), font=get_font(16, bold=True), anchor="mm")
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))

    # 7. Íconos de Mirror (desktop_PhoneLink / ArMir / IpMir)
    for base_name in ["desktop_PhoneLink", "desktop_ArMir", "desktop_IpMir"]:
        for pressed, suffix in [(False, ".png"), (True, "_sel.png")]:
            fname = base_name + suffix
            im, draw = generate_base_button((126, 126), pressed, style)
            icx, icy = 63, 63
            draw.rounded_rectangle([icx - 20, icy - 26, icx + 6, icy + 20], radius=6, outline=(255, 255, 255, 240), width=3)
            draw.rounded_rectangle([icx - 6, icy - 16, icx + 20, icy + 30], radius=6, outline=(255, 255, 255, 240), width=3)
            save_minfs_p_png(im, os.path.join(desktop_dir, fname))

    # 8. Botones CarPlay y Android Auto (130x116 px contenidos sin desborde)
    for pressed, fname in [(False, "desktop_Carplay.png"), (True, "desktop_Carplay_sel.png")]:
        im = Image.new("RGBA", (130, 116), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        bg_col = pal["bg_pressed"] if pressed else pal["bg_normal"]
        draw.rounded_rectangle([2, 2, 128, 114], radius=18, fill=bg_col, outline=accent if pressed else pal["border_normal"], width=2 if pressed else 1)
        draw.rounded_rectangle([38, 20, 92, 58], radius=6, outline=(255, 255, 255, 240), width=3)
        draw.polygon([(69, 39), (59, 32), (59, 46)], fill=(255, 255, 255, 240))
        draw.text((65, 80), "CarPlay", fill=(245, 250, 255, 255), font=get_font(13, bold=True), anchor="mm")
        draw.line([(32, 108), (98, 108)], fill=accent if style=="cyber" else (245, 250, 255, 255), width=3)
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))

    for pressed, fname in [(False, "desktop_Aoa.png"), (True, "desktop_Aoa_sel.png")]:
        im = Image.new("RGBA", (130, 116), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        bg_col = pal["bg_pressed"] if pressed else pal["bg_normal"]
        draw.rounded_rectangle([2, 2, 128, 114], radius=18, fill=bg_col, outline=accent_sub if pressed else pal["border_normal"], width=2 if pressed else 1)
        aax = 65
        draw.line([(aax, 22), (aax - 16, 50)], fill=(255, 255, 255, 240), width=4)
        draw.line([(aax, 22), (aax + 16, 50)], fill=(255, 255, 255, 240), width=4)
        draw.line([(aax - 7, 42), (aax + 7, 42)], fill=(255, 255, 255, 240), width=3)
        draw.text((65, 80), "Android Auto", fill=(245, 250, 255, 255), font=get_font(12, bold=True), anchor="mm")
        draw.line([(32, 108), (98, 108)], fill=accent_sub if style=="cyber" else (245, 250, 255, 255), width=3)
        save_minfs_p_png(im, os.path.join(desktop_dir, fname))
    print("      • Todos los 16 archivos PNG de botones del escritorio inyectados en MINFS.")

    # 9. Vistas integradas completas (Tarjeta música, Barra superior, Ajustes, Cortina, EQ)
    inject_desktop_extras(style)
    print("      • Tarjeta multimedia y controles del reproductor inyectados en MINFS.")
    inject_headbar_assets(style)
    print("      • Barra superior (Headbar: botones e iconos de estado) inyectada en MINFS.")
    inject_setting_assets(style)
    print("      • Menú de Ajustes (Pestañas, switches ON/OFF, sliders y diálogos) inyectado en MINFS.")
    inject_pullmenu_assets(style)
    print("      • Cortina desplegable (Pullmenu: 6 accesos directos y brillo) inyectada en MINFS.")
    inject_secondary_views_theme(style)
    print("      • Vistas secundarias (Audio, BT, Calculadora, Calendario, Diálogos, Explorador, Música, Standby, etc.) 100% integradas en MINFS.")
    inject_eq_assets(style)
    print("      • Ecualizador (EQ: Presets, balance y Loudness) inyectado en MINFS.")

def process_ui_theme(style, brand, model, subtitle, logo_path, tint_logo, bt_name):
    theme_name = THEMES_MAP.get(style, "Personalizado")
    print(f"\n[4/6] Configurando estilo de interfaz:")
    print(f"      • Estilo seleccionado: {theme_name} ({style})")

    if style in ("original", "factory"):
        backup_dir = os.path.join(THEMES_DIR, "factory_backup", "appres", "img")
        if os.path.exists(backup_dir):
            restored = 0
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_p = os.path.relpath(src_file, backup_dir)
                    dest_file = os.path.join(MINFS_DIR, "appres", "img", rel_p)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(src_file, dest_file)
                    restored += 1
            print(f"      • {restored} archivos originales de fábrica restaurados al 100% en MINFS.")
        return

    # 1. Inyectar archivos físicos procedurales en MINFS (Base de estilo, tarjeta, switches y sliders)
    inject_physical_ui_assets(style)

    # 2. Inyectar iconos HD generados por Gemini desde la biblioteca de temas (themes/<style>/appres/img)
    theme_custom_dir = os.path.join(BASE_DIR, "themes", style, "appres", "img")
    if os.path.exists(theme_custom_dir):
        copied_count = 0
        for root, dirs, files in os.walk(theme_custom_dir):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg")):
                    src_file = os.path.join(root, file)
                    rel_p = os.path.relpath(src_file, theme_custom_dir)
                    dest_file = os.path.join(MINFS_DIR, "appres", "img", rel_p)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(src_file, dest_file)
                    copied_count += 1
        if copied_count > 0:
            print(f"      • {copied_count} iconos HD de Gemini (Sprite Sheet) inyectados con éxito en MINFS.")

    # 2. Ajustar coordenadas en desktop.json (restaurando reloj de fábrica y CarPlay/Android Auto contenidos)
    desktop_json_path = os.path.join(MINFS_DIR, "appres", "layout", "desktop", "desktop.json")
    if os.path.exists(desktop_json_path):
        try:
            with open(desktop_json_path, "r", encoding="utf-8") as f:
                d_layout = json.load(f)
            if "button-001" in d_layout: # btnCarplay
                d_layout["button-001"]["pos"] = "16,320,130,116"
            if "button-002" in d_layout: # btnAuto
                d_layout["button-002"]["pos"] = "1134,320,130,116"
            if "label-001" in d_layout: # lblTime
                d_layout["label-001"]["pos"] = "270,70,200,80"
            if "label-003" in d_layout: # lblDate
                d_layout["label-003"]["pos"] = "276,180,200,44"
                now = datetime.datetime.now()
                d_layout["label-003"]["text"] = now.strftime("%Y-%m-%d")
            if "label-004" in d_layout: # lblWeek
                d_layout["label-004"]["pos"] = "298,225,150,40"
            if "backgd-006" in d_layout: # bgdAM
                d_layout["backgd-006"]["pos"] = "470,112,65,39"
            if "backgd-005" in d_layout: # bgdPM
                d_layout["backgd-005"]["pos"] = "470,112,65,39"
            with open(desktop_json_path, "w", encoding="utf-8") as f:
                json.dump(d_layout, f, indent=4)
            print("      • Coordenadas de CarPlay, Android Auto y reloj/fecha configuradas en desktop.json.")
        except Exception as e:
            print(f"      [!] Nota al actualizar desktop.json: {e}")

    # 3. Generar vista previa visual en alta resolución (1280x480) fiel a la pantalla física
    bg0_png_path = os.path.join(MINFS_DIR, "appres", "img", "setting", "bg0.png")
    if os.path.exists(bg0_png_path):
        preview = Image.open(bg0_png_path).convert("RGBA")
    else:
        preview = Image.new("RGBA", (UI_WIDTH, UI_HEIGHT), (16, 18, 22, 255))
        
    draw = ImageDraw.Draw(preview)
    
    accent = (220, 225, 235, 255) if style == "stealth" else ((212, 255, 0, 255) if style == "tactical" else (0, 235, 255, 255))
    accent_sub = (255, 0, 110, 255) if style == "cyber" else accent
    
    # Headbar
    bar = Image.new("RGBA", (UI_WIDTH, 46), (12, 15, 20, 230))
    preview.paste(bar, (0, 0), bar)
    draw.line([(0, 46), (UI_WIDTH, 46)], fill=(255, 255, 255, 30), width=1)
    
    draw.rounded_rectangle([18, 7, 68, 39], radius=8, fill=(35, 40, 50, 200), outline=(255, 255, 255, 40), width=1)
    draw.polygon([(43, 15), (34, 23), (52, 23)], fill=(255, 255, 255, 230))
    draw.rectangle([37, 23, 49, 30], fill=(255, 255, 255, 230))
    
    draw.rounded_rectangle([80, 7, 180, 39], radius=8, fill=(35, 40, 50, 200), outline=(255, 255, 255, 40), width=1)
    draw.text((142, 23), "80%", fill=(255, 255, 255, 230), font=get_font(13, bold=True), anchor="mm")
    
    draw.rounded_rectangle([195, 7, 345, 39], radius=16, fill=(30, 35, 45, 200), outline=accent, width=1)
    draw.text((276, 23), f"{bt_name} OK", fill=(230, 235, 245, 255), font=get_font(12, bold=True), anchor="mm")
    
    # Reloj en vivo sincronizado con la fecha de compilación
    now = datetime.datetime.now()
    cur_date_str = now.strftime("%Y-%m-%d")
    dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    cur_day_name = dias_semana[now.weekday()]
    draw.text((370, 110), now.strftime("%H:%M"), fill=(255, 255, 255, 255), font=get_font(68, bold=True), anchor="mm")
    draw.text((376, 185), cur_date_str, fill=(200, 215, 235, 255), font=get_font(18, bold=False), anchor="mm")
    draw.text((373, 228), cur_day_name, fill=(215, 220, 230, 255), font=get_font(16, bold=True), anchor="mm")

    # Tarjeta de música de fábrica (778, 70, 394, 222)
    bg_card_file = os.path.join(MINFS_DIR, "appres", "img", "desktop", "desktop_bg.png")
    if os.path.exists(bg_card_file):
        bg_card_im = Image.open(bg_card_file).convert("RGBA")
        preview.paste(bg_card_im, (778, 70), bg_card_im)
    else:
        draw.rounded_rectangle([778, 70, 1172, 292], radius=18, fill=(14, 18, 26, 225), outline=(55, 68, 85, 255), width=1)
    
    # Controles multimedia del reproductor
    cx_mid = (778 + 1172) // 2
    cy_ctrl = 70 + 170
    draw.polygon([(cx_mid - 62, cy_ctrl), (cx_mid - 48, cy_ctrl - 10), (cx_mid - 48, cy_ctrl + 10)], fill=(215, 225, 240, 255))
    draw.polygon([(cx_mid - 48, cy_ctrl), (cx_mid - 34, cy_ctrl - 10), (cx_mid - 34, cy_ctrl + 10)], fill=(215, 225, 240, 255))
    draw.ellipse([cx_mid - 24, cy_ctrl - 24, cx_mid + 24, cy_ctrl + 24], fill=(245, 250, 255, 255))
    draw.polygon([(cx_mid - 7, cy_ctrl - 10), (cx_mid + 11, cy_ctrl), (cx_mid - 7, cy_ctrl + 10)], fill=(16, 20, 28, 255))
    draw.polygon([(cx_mid + 48, cy_ctrl), (cx_mid + 34, cy_ctrl - 10), (cx_mid + 34, cy_ctrl + 10)], fill=(215, 225, 240, 255))
    draw.polygon([(cx_mid + 62, cy_ctrl), (cx_mid + 48, cy_ctrl - 10), (cx_mid + 48, cy_ctrl + 10)], fill=(215, 225, 240, 255))
    draw.text((cx_mid, 70 + 80), "NULL", fill=(200, 215, 235, 255), font=get_font(20, bold=True), anchor="mm")

    # Botones inferiores (CarPlay y Auto contenidos con margen seguro de 16px)
    cp_rect = [16, 320, 146, 436]
    aa_rect = [1134, 320, 1264, 436]
    draw.rounded_rectangle(cp_rect, radius=18, fill=(18, 22, 34, 230), outline=accent if style=="cyber" else (255, 255, 255, 45), width=1)
    # Icono CarPlay
    draw.rounded_rectangle([cp_rect[0]+42, cp_rect[1]+24, cp_rect[2]-42, cp_rect[1]+60], radius=6, outline=(255, 255, 255, 240), width=3)
    draw.polygon([(81, 357), (71, 350), (71, 364)], fill=(255, 255, 255, 240))
    draw.text((81, 400), "CarPlay", fill=(245, 250, 255, 255), font=get_font(13, bold=True), anchor="mm")
    draw.line([(cp_rect[0]+35, cp_rect[3]-5), (cp_rect[2]-35, cp_rect[3]-5)], fill=accent if style=="cyber" else (245, 250, 255, 255), width=3)

    draw.rounded_rectangle(aa_rect, radius=18, fill=(18, 22, 34, 230), outline=accent_sub if style=="cyber" else (255, 255, 255, 45), width=1)
    # Icono Android Auto
    aax = (aa_rect[0] + aa_rect[2]) // 2
    draw.line([(aax, 344), (aax - 16, 370)], fill=(255, 255, 255, 240), width=4)
    draw.line([(aax, 344), (aax + 16, 370)], fill=(255, 255, 255, 240), width=4)
    draw.line([(aax - 7, 362), (aax + 7, 362)], fill=(255, 255, 255, 240), width=3)
    draw.text((1199, 400), "Android Auto", fill=(245, 250, 255, 255), font=get_font(12, bold=True), anchor="mm")
    draw.line([(aa_rect[0]+35, aa_rect[3]-5), (aa_rect[2]-35, aa_rect[3]-5)], fill=accent_sub if style=="cyber" else (245, 250, 255, 255), width=3)

    # 6 Apps del lanzador central
    app_names = ["Audio", "USB", "SD Card", "Teléfono", "Mirror", "Calculadora"]
    app_xs = [176 + i * 160 for i in range(6)]
    for i, name in enumerate(app_names):
        bx = app_xs[i]
        draw.rounded_rectangle([bx, 312, bx + 126, 428], radius=20, fill=(16, 20, 28, 220), outline=(255, 255, 255, 40), width=1)
        icx, icy = bx + 63, 360
        if name == "Audio":
            draw.ellipse([icx - 14, icy + 6, icx - 2, icy + 16], fill=(255, 255, 255, 240))
            draw.ellipse([icx + 4, icy + 2, icx + 16, icy + 12], fill=(255, 255, 255, 240))
            draw.line([(icx - 2, icy + 10), (icx - 2, icy - 14)], fill=(255, 255, 255, 240), width=3)
            draw.line([(icx + 16, icy + 6), (icx + 16, icy - 18)], fill=(255, 255, 255, 240), width=3)
            draw.polygon([(icx - 2, icy - 10), (icx + 16, icy - 14), (icx + 16, icy - 18), (icx - 2, icy - 14)], fill=(255, 255, 255, 240))
        elif name == "USB":
            draw.line([(icx, icy + 18), (icx, icy - 14)], fill=(255, 255, 255, 240), width=3)
            draw.polygon([(icx, icy - 22), (icx - 6, icy - 14), (icx + 6, icy - 14)], fill=(255, 255, 255, 240))
            draw.line([(icx, icy + 6), (icx - 12, icy - 2), (icx - 12, icy - 10)], fill=(255, 255, 255, 240), width=2)
            draw.ellipse([icx - 16, icy - 14, icx - 8, icy - 6], fill=(255, 255, 255, 240))
            draw.line([(icx, icy + 2), (icx + 12, icy - 6), (icx + 12, icy - 14)], fill=(255, 255, 255, 240), width=2)
            draw.rectangle([icx + 9, icy - 18, icx + 15, icy - 12], fill=(255, 255, 255, 240))
        elif name == "SD Card":
            draw.polygon([(icx-18, icy-20), (icx+10, icy-20), (icx+18, icy-12), (icx+18, icy+20), (icx-18, icy+20)], outline=(255, 255, 255, 240), width=2)
            draw.text((icx, icy + 4), "SD", fill=(255, 255, 255, 240), font=get_font(12, bold=True), anchor="mm")
        elif name == "Teléfono":
            handset_file = os.path.join(ASSETS_DIR, "phone_handset.png")
            if os.path.exists(handset_file):
                raw_h = Image.open(handset_file).convert("RGBA")
                smooth_h = raw_h.resize((92, 92), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(0.5)).resize((46, 46), Image.Resampling.LANCZOS)
                preview.paste(smooth_h, (icx - 23, icy - 23), smooth_h)
            else:
                draw.ellipse([icx - 8, icy - 14, icx + 14, icy - 2], fill=(255, 255, 255, 240))
                draw.ellipse([icx - 14, icy + 2, icx + 8, icy + 14], fill=(255, 255, 255, 240))
                draw.line([(icx - 6, icy - 10), (icx - 10, icy + 8)], fill=(255, 255, 255, 240), width=6)
        elif name == "Mirror":
            draw.rounded_rectangle([icx - 16, icy - 20, icx + 4, icy + 14], radius=4, outline=(255, 255, 255, 240), width=2)
            draw.rounded_rectangle([icx - 4, icy - 12, icx + 16, icy + 22], radius=4, outline=(255, 255, 255, 240), width=2)
        elif name == "Calculadora":
            draw.rounded_rectangle([icx - 18, icy - 24, icx + 18, icy + 24], radius=6, outline=(255, 255, 255, 240), width=2)
            draw.rounded_rectangle([icx - 14, icy - 20, icx + 14, icy - 10], radius=2, outline=(255, 255, 255, 240), width=1)
            for ky in [icy - 4, icy + 6, icy + 16]:
                for kx in [icx - 10, icx, icx + 10]:
                    draw.ellipse([kx - 3, ky - 3, kx + 3, ky + 3], outline=(255, 255, 255, 220), width=1)

        draw.text((bx + 63, 444), name, fill=(215, 225, 235, 255), font=get_font(13, bold=False), anchor="mm")

    preview_ui_path = os.path.join(OUTPUT_DIR, "vista_previa_escritorio.png")
    preview.save(preview_ui_path, format="PNG")
    print(f"      • Vista previa de escritorio generada: {os.path.relpath(preview_ui_path, BASE_DIR)}")

def repack_minfs():
    print("\n[5/6] Re-empaquetando sistema de archivos MINFS (data_udisk.fex)...")
    base_fex_path = os.path.join(ORIG_FEX_DIR, "23_data_udisk.fex")
    with open(base_fex_path, "rb") as f:
        orig = bytearray(f.read())

    new_data = bytearray(40448)
    new_data[:40448] = orig[:40448]
    current_data_off = 40448
    file_count = 0

    def process_dir(dir_offset, dir_size, current_path):
        nonlocal current_data_off, file_count
        pos = dir_offset
        end = dir_offset + dir_size
        while pos < end:
            fo, s1, s2 = struct.unpack('<III', orig[pos:pos+12])
            rl, is_d, nl = struct.unpack('<HHI', orig[pos+12:pos+20])
            if rl == 0 or nl == 0: break
            raw_name = orig[pos+20:pos+20+nl].split(b'\x00')[0]
            name = raw_name.decode('latin1', errors='ignore')
            item_path = os.path.join(current_path, name)
            
            if is_d == 1:
                process_dir(fo, s1, item_path)
            else:
                file_count += 1
                with open(item_path, 'rb') as fp:
                    content = fp.read()
                
                if current_data_off % 4 != 0:
                    pad = 4 - (current_data_off % 4)
                    new_data.extend(b'\x00' * pad)
                    current_data_off += pad
                
                new_off = current_data_off
                new_s1 = len(content)
                new_s2 = new_s1 if is_d != 6 else s2
                
                new_data[pos:pos+4] = struct.pack('<I', new_off)
                new_data[pos+4:pos+8] = struct.pack('<I', new_s1)
                new_data[pos+8:pos+12] = struct.pack('<I', new_s2)
                
                new_data.extend(content)
                current_data_off += len(content)
                
            pos += rl

    process_dir(512, 316, MINFS_DIR)
    assert current_data_off <= PARTITION_SIZE, f"Error: Tamaño excede el límite de {PARTITION_SIZE} bytes"
    new_data.extend(b'\x00' * (PARTITION_SIZE - len(new_data)))
    
    print(f"      • {file_count} archivos empaquetados en MINFS.")
    print(f"      • Partición data_udisk completada: {len(new_data) / (1024*1024):.2f} MB")
    return new_data

def build_firmware(new_udisk_data):
    print("\n[6/6] Ensamblando imagen de firmware (IMAGEWTY container)...")
    sum32 = sum(struct.unpack('<%dI' % (len(new_udisk_data) // 4), new_udisk_data)) & 0xffffffff
    print(f"      • Checksum sum32 recalculado: {hex(sum32)}")

    with open(BASE_IMG_PATH, "rb") as f:
        img_data = bytearray(f.read())

    udisk_off = 0x3b0000
    udisk_size = 0xcb0000
    img_data[udisk_off:udisk_off+udisk_size] = new_udisk_data

    vudisk_off = 0x1060000
    img_data[vudisk_off:vudisk_off+4] = struct.pack('<I', sum32)

    os.makedirs(USB_OUTPUT_DIR, exist_ok=True)
    usb_file = os.path.join(USB_OUTPUT_DIR, "melis_f133-b-pnd-16M-board_uart0_16Mnor.img")
    with open(usb_file, "wb") as f:
        f.write(img_data)

    custom_file = os.path.join(OUTPUT_DIR, "melis_f133_custom.img")
    with open(custom_file, "wb") as f:
        f.write(img_data)

    print(f"      • Firmware para USB: {os.path.relpath(usb_file, BASE_DIR)}")
    print(f"      • Firmware para MicroSD / PhoenixCard: {os.path.relpath(custom_file, BASE_DIR)}")

def main():
    parser = argparse.ArgumentParser(description="F133 Boot Logo & Firmware Customizer")
    parser.add_argument("--image", "-i", help="Ruta a la imagen para el boot logo", default=None)
    parser.add_argument("--theme", "-t", help="Estilo de interfaz ('stealth', 'tactical', 'cyber')", default=None)
    parser.add_argument("--brand", help="Marca del vehículo (ej: MITSUBISHI, TOYOTA, FORD)", default=None)
    parser.add_argument("--model", help="Modelo del vehículo (ej: L200 KATANA, HILUX)", default=None)
    parser.add_argument("--subtitle", help="Subtítulo o edición (ej: 4X4 TURBO DIESEL)", default=None)
    parser.add_argument("--brand-logo", help="Ruta al logo de la marca (PNG o JPG)", default=None)
    parser.add_argument("--bt", "-b", help="Nombre del Bluetooth (máx 8 caracteres)", default=None)
    parser.add_argument("--lang", "-l", help="ID del idioma por defecto (3 = Español)", type=int, default=None)
    parser.add_argument("--sound", "-s", help="Modo de sonido ('silencio' o ruta a un archivo .wav)", default=None)
    parser.add_argument("--version-text", "-v", help="Texto de versión de sistema", default=None)
    args = parser.parse_args()

    print_banner()

    cfg = load_configuration()

    if args.theme and args.theme.lower() in THEMES_MAP: cfg["theme_style"] = args.theme.lower()
    if args.brand: cfg["brand"] = args.brand
    if args.model: cfg["model"] = args.model
    if args.subtitle: cfg["subtitle"] = args.subtitle
    if args.brand_logo: cfg["logo_file"] = args.brand_logo
    if args.bt: cfg["bt_name"] = args.bt
    if args.lang is not None: cfg["language"] = args.lang
    if args.version_text: cfg["version_str"] = args.version_text
    if args.sound:
        if args.sound.lower() == "silencio":
            cfg["sound_mode"] = "silencio"
        else:
            cfg["sound_mode"] = "archivo"
            cfg["sound_file"] = args.sound

    img_path = find_input_image(args.image)
    
    # Flujo de ejecución
    process_logo(img_path)
    process_sound(cfg["sound_mode"], cfg["sound_file"])
    process_system_configs(cfg["bt_name"], cfg["language"], cfg["version_str"])
    process_ui_theme(cfg["theme_style"], cfg["brand"], cfg["model"], cfg["subtitle"], cfg["logo_file"], cfg["tint_logo"], cfg["bt_name"])
    udisk_data = repack_minfs()
    build_firmware(udisk_data)

    print("\n" + "=" * 75)
    print("   ✅ ¡FIRMWARE PERSONALIZADO GENERADO CON ÉXITO!")
    print("=" * 75)
    print(" RESUMEN DE PERSONALIZACIONES APLICADAS:")
    print(f" • Logo de inicio:     {os.path.basename(img_path)} (1600x600 nativo)")
    print(f" • Estilo de Interfaz: {THEMES_MAP.get(cfg['theme_style'], cfg['theme_style'])}")
    print(f" • Nombre Bluetooth:   {cfg['bt_name']}")
    print(f" • Idioma por defecto: {IDIOMAS_MAP.get(cfg['language'], str(cfg['language']))}")
    print(f" • Sonido de arranque: {cfg['sound_mode']}")
    print(f" • Versión de sistema: {cfg['version_str']}")
    print("-" * 75)
    print(" ARCHIVOS GENERADOS:")
    print(f" • Vista previa pantalla:    output/vista_previa_pantalla.jpg")
    print(f" • Vista previa escritorio:  output/vista_previa_escritorio.png")
    print(f" • Firmware para USB:        output/F133_IMG/melis_f133-b-pnd-16M-board_uart0_16Mnor.img")
    print("-" * 75)
    print(" INSTRUCCIONES PARA INSTALAR EN TU PANTALLA:")
    print(" 1. Formatea un pendrive USB (de 32 GB o menos) en formato FAT32.")
    print(" 2. Copia la carpeta 'output/F133_IMG' completa directamente a la raíz del pendrive.")
    print("    (Estructura requerida: USB -> F133_IMG -> melis_f133-b-pnd...)")
    print(" 3. Conecta el pendrive a la pantalla encendida y confirma la actualización.")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    main()
