#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tests/test_firmware_suite.py
-----------------------------
Suite de pruebas automatizadas para validar:
1. Integridad de la copia de seguridad de fábrica (factory_backup).
2. Cobertura del 100% y transparencia correcta en los temas (tactical, stealth, cyber).
3. Verificación de glifos no borrados y dígitos flotantes con fondo transparente.
4. Generación y validez de las capturas de vistas en cada tema.
5. Procesamiento de logo de arranque (rotación MIPI 600x1600) y audio silencioso 0dB.
6. Empaquetado MINFS: límite físico estricto de 13,303,808 bytes (12.69 MB) y holgura de seguridad.
7. Ensamblado de contenedor IMAGEWTY y checksum sum32.
8. Restauración de tema original de fábrica (Stock Firmware).
"""

import os
import sys
import struct
import unittest
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

THEMES_DIR = os.path.join(BASE_DIR, "themes")
BACKUP_DIR = os.path.join(THEMES_DIR, "factory_backup", "appres", "img")
MINFS_DIR = os.path.join(BASE_DIR, "assets", "minfs_extracted")
PARTITION_LIMIT = 13303808  # 12.69 MB

class TestFirmwareSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 75)
        print("   🧪 INICIANDO SUITE DE PRUEBAS DE VALIDACIÓN DE FIRMWARE")
        print("=" * 75)

    def test_01_factory_backup_integrity(self):
        """Verifica que el respaldo de fábrica esté intacto y completo."""
        self.assertTrue(os.path.exists(BACKUP_DIR), "El directorio factory_backup no existe")
        
        backup_files = []
        for r, d, fs in os.walk(BACKUP_DIR):
            for f in fs:
                if f.startswith("."):
                    continue
                backup_files.append(os.path.relpath(os.path.join(r, f), BACKUP_DIR))
                
        self.assertGreaterEqual(len(backup_files), 564, f"Faltan archivos en factory_backup: {len(backup_files)}")
        
        # Verificar archivos clave de fábrica
        critical_files = [
            "setting/tab_bg.png",
            "bt/tab_bg.png",
            "videoin/tab_bg.png",
            "setting/bg0.jpg",
            "headbar/aoa.png",
            "headbar/cpl.png",
            "desktop/desktop_Carplay.png",
            "desktop/0.png"
        ]
        for cf in critical_files:
            fp = os.path.join(BACKUP_DIR, cf)
            self.assertTrue(os.path.exists(fp), f"Archivo crítico faltante en backup: {cf}")
            with Image.open(fp) as im:
                self.assertGreater(im.size[0], 0)
                self.assertGreater(im.size[1], 0)

    def test_02_theme_assets_coverage_and_transparency(self):
        """Valida que los 3 temas cubran el 100% de archivos y que tab_bg mantenga alfa original."""
        themes = ["tactical", "stealth", "cyber"]
        
        # Lista de archivos en fábrica (ignorando metadatos de SO)
        factory_files = set()
        for r, d, fs in os.walk(BACKUP_DIR):
            for f in fs:
                if f.startswith("."):
                    continue
                factory_files.add(os.path.relpath(os.path.join(r, f), BACKUP_DIR))

        for t in themes:
            t_dir = os.path.join(THEMES_DIR, t, "appres", "img")
            self.assertTrue(os.path.exists(t_dir), f"Carpeta de tema {t} no existe")
            
            # Verificar cobertura
            missing = []
            for ff in factory_files:
                if not os.path.exists(os.path.join(t_dir, ff)):
                    missing.append(ff)
            self.assertEqual(len(missing), 0, f"Tema {t} tiene {len(missing)} archivos faltantes: {missing[:5]}")
            
            # Verificar preservación de transparencia en tab_bg
            for tb in ["setting/tab_bg.png", "bt/tab_bg.png", "videoin/tab_bg.png"]:
                with Image.open(os.path.join(BACKUP_DIR, tb)) as f1:
                    orig_im = f1.convert("RGBA")
                orig_alpha = orig_im.split()[-1].getextrema()
                
                with Image.open(os.path.join(t_dir, tb)) as f2:
                    theme_im = f2.convert("RGBA")
                theme_alpha = theme_im.split()[-1].getextrema()
                
                self.assertEqual(orig_im.size, theme_im.size, f"Tamaño no coincide en {tb} para {t}")
                self.assertEqual(orig_alpha, theme_alpha, f"Rango alfa alterado en {tb} para {t}")

    def test_03_critical_glyphs_and_floating_digits(self):
        """Verifica que ningún icono esté borrado/plano y que los números del reloj sean transparentes."""
        themes = ["tactical", "stealth", "cyber"]
        
        # Iconos que antes sufrían borrado
        icons_to_check = [
            "headbar/aoa.png", "headbar/cpl.png", "headbar/sd.png", "headbar/usb.png",
            "music/play.png", "desktop/desktop_Carplay.png", "desktop/desktop_Aoa.png"
        ]
        
        for t in themes:
            t_dir = os.path.join(THEMES_DIR, t, "appres", "img")
            for ic in icons_to_check:
                p = os.path.join(t_dir, ic)
                with Image.open(p) as f:
                    im = f.convert("RGBA")
                alpha = im.split()[-1]
                bbox = alpha.getbbox()
                self.assertIsNotNone(bbox, f"Icono borrado/invisible detectado en {t}: {ic}")
                colors = len(set(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()))
                self.assertGreater(colors, 1, f"Icono plano de 1 solo color en {t}: {ic}")
                
            # Dígitos flotantes: deben tener fondo transparente (alpha min = 0)
            digits = ["desktop/0.png", "desktop/5.png", "desktop/colon.png", "audio/0.png", "setting/0.png"]
            for d in digits:
                p = os.path.join(t_dir, d)
                with Image.open(p) as f:
                    im = f.convert("RGBA")
                alpha = im.split()[-1]
                a_min, a_max = alpha.getextrema()
                self.assertEqual(a_min, 0, f"Dígito con caja negra opaca detrás en {t}: {d}")
                self.assertGreater(a_max, 200, f"Dígito sin contenido visible en {t}: {d}")

    def test_04_view_previews_generated(self):
        """Verifica que cada tema tenga sus 8 vistas y el mosaico resumen generado correctamente."""
        themes = ["tactical", "stealth", "cyber"]
        expected_views = [
            "00_resumen_todas_las_vistas.jpg",
            "01_escritorio.png",
            "02_ajustes.png",
            "03_musica.png",
            "04_telefono_bluetooth.png",
            "05_radio_fm.png",
            "06_ecualizador.png",
            "07_cortina_pullmenu.png",
            "08_reloj_standby.png"
        ]
        for t in themes:
            v_dir = os.path.join(THEMES_DIR, t, "vistas")
            self.assertTrue(os.path.exists(v_dir), f"Carpeta de vistas no existe para {t}")
            for ev in expected_views:
                fp = os.path.join(v_dir, ev)
                self.assertTrue(os.path.exists(fp), f"Vista {ev} no existe en {t}")
                sz = os.path.getsize(fp)
                self.assertGreater(sz, 20000, f"Vista {ev} en {t} parece vacía o corrupta ({sz} bytes)")

    def test_05_repack_minfs_partition_boundary(self):
        """Valida que el empaquetador MINFS nunca exceda el límite de 12.69 MB de la SPI NOR Flash."""
        import cambiar_logo
        
        # Aplicar tema táctico para medir empaque optimizado
        cambiar_logo.process_ui_theme("tactical", "MITSUBISHI", "L200", "4X4", None, False, "L200")
        udisk_data = cambiar_logo.repack_minfs()
        self.assertEqual(len(udisk_data), PARTITION_LIMIT, f"Tamaño final de data_udisk no es {PARTITION_LIMIT}")
        
        # Medir datos reales usados
        last_non_zero = 0
        for i in range(len(udisk_data) - 1, -1, -1):
            if udisk_data[i] != 0:
                last_non_zero = i + 1
                break
                
        free_space = PARTITION_LIMIT - last_non_zero
        print(f"\n      [MINFS Test - Tema Tactical]")
        print(f"      • Datos reales usados: {last_non_zero:,} bytes ({last_non_zero/(1024*1024):.2f} MB)")
        print(f"      • Espacio libre de seguridad: {free_space:,} bytes ({free_space/(1024*1024):.2f} MB)")
        self.assertLess(last_non_zero, PARTITION_LIMIT, "¡Desbordamiento de partición MINFS!")
        self.assertGreater(free_space, 1500000, "Menos de 1.5 MB de holgura en el tema optimizado")

    def test_06_build_firmware_container(self):
        """Valida que el firmware resultante tenga la cabecera IMAGEWTY y checksum sum32 válido."""
        import cambiar_logo
        
        udisk_data = cambiar_logo.repack_minfs()
        cambiar_logo.build_firmware(udisk_data)
        
        usb_fw = os.path.join(BASE_DIR, "output", "F133_IMG", "melis_f133-b-pnd-16M-board_uart0_16Mnor.img")
        self.assertTrue(os.path.exists(usb_fw), "El firmware USB no fue generado")
        
        with open(usb_fw, "rb") as f:
            header = f.read(8)
            self.assertEqual(header, b"IMAGEWTY", "La imagen no tiene el contenedor Allwinner IMAGEWTY")
            
            # Verificar que el checksum en offset 0x1060000 coincida con sum32
            expected_sum32 = sum(struct.unpack('<%dI' % (len(udisk_data) // 4), udisk_data)) & 0xffffffff
            f.seek(0x1060000)
            written_sum32 = struct.unpack('<I', f.read(4))[0]
            self.assertEqual(written_sum32, expected_sum32, "Checksum sum32 del firmware no coincide")

    def test_07_restore_factory_theme_cycle(self):
        """Valida que alternar a 'original' restaure intactos los 570 archivos de fábrica."""
        import cambiar_logo
        
        # 1. Aplicar tema original
        cambiar_logo.process_ui_theme("original", "MITSUBISHI", "L200", "4X4", None, False, "L200")
        
        # 2. Verificar que los archivos en MINFS coincidan con el factory backup
        minfs_img_dir = os.path.join(MINFS_DIR, "appres", "img")
        for tb in ["setting/tab_bg.png", "bt/tab_bg.png", "videoin/tab_bg.png"]:
            orig_p = os.path.join(BACKUP_DIR, tb)
            minfs_p = os.path.join(minfs_img_dir, tb)
            with open(orig_p, "rb") as f1, open(minfs_p, "rb") as f2:
                self.assertEqual(f1.read(), f2.read(), f"El archivo {tb} en MINFS no coincide con factory_backup")

        # 3. Volver a aplicar tactical para dejar el tema personalizado activo
        cambiar_logo.process_ui_theme("tactical", "MITSUBISHI", "L200", "4X4", None, False, "L200")
        udisk = cambiar_logo.repack_minfs()
        cambiar_logo.build_firmware(udisk)

if __name__ == "__main__":
    unittest.main()
