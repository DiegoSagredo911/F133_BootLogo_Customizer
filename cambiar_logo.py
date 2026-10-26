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
================================================================================
"""

import sys
import os
import struct
import io
import wave
import configparser
import argparse

try:
    from PIL import Image
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

# Constantes de Hardware de la pantalla 10.26"
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 600
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

def print_banner():
    print("=" * 75)
    print("   🚗 F133 BOOT LOGO & FIRMWARE CUSTOMIZER (10.26\" 1600x600)")
    print("   Desarrollado por: Diego Sagredo Ailef")
    print("   GitHub: https://github.com/diegosagredo911")
    print("=" * 75)

def load_configuration():
    config = configparser.ConfigParser()
    # Valores por defecto
    settings = {
        "bt_name": "L200",
        "language": 3,
        "version_str": "DIEGO SAGREDO EDITION 2026",
        "sound_mode": "silencio",
        "sound_file": "custom_sound.wav"
    }

    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding="utf-8")
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

    print("\n[!] No se encontró ninguna imagen para procesar.")
    print("    Por favor coloca tu imagen en esta carpeta como:")
    print("    -> custom_logo.png  (o custom_logo.jpg)")
    print("    o pásala como argumento: python3 cambiar_logo.py --image mi_foto.jpg\n")
    sys.exit(1)

def process_logo(input_image_path):
    print(f"\n[1/5] Procesando imagen de arranque: {os.path.basename(input_image_path)}")
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
        print(f"      • Vista previa generada: {os.path.relpath(preview_path, BASE_DIR)}")

        vertical_mipi = landscape_full.rotate(MIPI_ROTATION, expand=True)
        print(f"      • Rotación nativa MIPI DSI aplicada: {vertical_mipi.size} px")

        target_bin = os.path.join(MINFS_DIR, "res", "stalogo0.bin")
        vertical_mipi.save(target_bin, format="JPEG", quality=85, progressive=False, optimize=True)
        file_size = os.path.getsize(target_bin)
        print(f"      • stalogo0.bin actualizado ({file_size / 1024:.1f} KB)")

def process_sound(sound_mode, sound_file):
    print(f"\n[2/5] Configurando sonido de encendido...")
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

            max_frames = int(out_rate * 6.0) # máx 6 segundos
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

    # Modo silencio predeterminado (0dB)
    with wave.open(target_wav, 'wb') as dst:
        dst.setnchannels(2)
        dst.setsampwidth(2)
        dst.setframerate(44100)
        dst.writeframes(b'\x00' * 5200)
    print("      • Sonido de encendido configurado a 0dB digital (100% Silencioso).")

def process_system_configs(bt_name, lang_id, version_str):
    lang_name = IDIOMAS_MAP.get(lang_id, f"ID {lang_id}")
    print(f"\n[3/5] Aplicando configuraciones de sistema:")
    print(f"      • Nombre de Bluetooth: '{bt_name}'")
    print(f"      • Idioma por defecto: {lang_name} ({lang_id})")
    print(f"      • Versión de sistema:  '{version_str}'")

    # 1. Modificar app_config.fex (Texto)
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
            else:
                new_lines.append(line)
        with open(fex_path, "w", encoding="gbk", errors="ignore") as f:
            f.writelines(new_lines)

    # 2. Modificar app_config.bin (Registros binarios)
    bin_path = os.path.join(MINFS_DIR, "app_config.bin")
    if os.path.exists(bin_path):
        with open(bin_path, "rb") as f:
            bdata = bytearray(f.read())

        # bt_name en offset 4772 (8 bytes)
        bt_bytes = bt_name.encode("latin1", errors="ignore")[:8]
        bdata[4772:4780] = bt_bytes + b"\x00" * (8 - len(bt_bytes))

        # idioma en offset 4636 (uint32)
        bdata[4636:4640] = struct.pack("<I", int(lang_id))

        # versión en offset 4436 (32 bytes)
        v_bytes = version_str.encode("latin1", errors="ignore")[:31]
        bdata[4436:4468] = v_bytes + b"\x00" * (32 - len(v_bytes))

        with open(bin_path, "wb") as f:
            f.write(bdata)

def repack_minfs():
    print("\n[4/5] Re-empaquetando sistema de archivos MINFS (data_udisk.fex)...")
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
    print("\n[5/5] Ensamblando imagen de firmware (IMAGEWTY container)...")
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
    parser.add_argument("--bt", "-b", help="Nombre del Bluetooth (máx 8 caracteres)", default=None)
    parser.add_argument("--lang", "-l", help="ID del idioma por defecto (3 = Español)", type=int, default=None)
    parser.add_argument("--sound", "-s", help="Modo de sonido ('silencio' o ruta a un archivo .wav)", default=None)
    parser.add_argument("--version-text", "-v", help="Texto de versión de sistema", default=None)
    args = parser.parse_args()

    print_banner()

    # Cargar ajustes desde config.ini
    cfg = load_configuration()

    # Sobrescribir con flags CLI si fueron pasados
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
    process_logo(img_path)
    process_sound(cfg["sound_mode"], cfg["sound_file"])
    process_system_configs(cfg["bt_name"], cfg["language"], cfg["version_str"])
    udisk_data = repack_minfs()
    build_firmware(udisk_data)

    print("\n" + "=" * 75)
    print("   ✅ ¡FIRMWARE PERSONALIZADO GENERADO CON ÉXITO!")
    print("=" * 75)
    print(" RESUMEN DE PERSONALIZACIONES APLICADAS:")
    print(f" • Logo de inicio:     {os.path.basename(img_path)} (1600x600 nativo)")
    print(f" • Nombre Bluetooth:   {cfg['bt_name']}")
    print(f" • Idioma por defecto: {IDIOMAS_MAP.get(cfg['language'], str(cfg['language']))}")
    print(f" • Sonido de arranque: {cfg['sound_mode']}")
    print(f" • Versión de sistema: {cfg['version_str']}")
    print("-" * 75)
    print(" INSTRUCCIONES PARA INSTALAR EN TU PANTALLA:")
    print(" 1. Formatea un pendrive USB (de 32 GB o menos) en formato FAT32.")
    print(" 2. Copia la carpeta 'output/F133_IMG' completa directamente a la raíz del pendrive.")
    print("    (Estructura requerida: USB -> F133_IMG -> melis_f133-b-pnd...)")
    print(" 3. Conecta el pendrive a la pantalla encendida y confirma la actualización.")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    main()
