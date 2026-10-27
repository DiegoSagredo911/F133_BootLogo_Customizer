# 🚗 Logos de Marcas para el Tablero / Brand Logos for Dashboard

Esta carpeta contiene logos y emblemas de marcas vehiculares optimizados para la insignia central de la pantalla.

## Logos incluidos por defecto:
* `mitsubishi.png` (Predeterminado para Mitsubishi L200 Katana)
* `toyota.png` (Para Hilux, Fortuner, RAV4, Land Cruiser, etc.)
* `ford.png` (Para Ranger, Raptor, F-150, Everest, etc.)
* `nissan.png` (Para Navara / Frontier, NP300, etc.)
* `chevrolet.png` (Para D-Max, Colorado, Silverado, etc.)
* `jeep.png` (Para Wrangler, Gladiator, Cherokee, etc.)

## ¿Cómo usar tu propio logo?
1. Coloca tu imagen (en formato **PNG** o **JPG**) en esta carpeta, por ejemplo `logos/mi_auto.png`.
2. No te preocupes por el fondo: Python detectará y **eliminará automáticamente fondos negros o blancos** con bordes suavizados (anti-aliasing).
3. Abre `config.ini` y especifica la ruta:
   ```ini
   [vehiculo]
   marca = TOYOTA
   modelo = HILUX
   subtitulo = 4X4 D-4D
   archivo_logo = logos/toyota.png
   armonizar_color_logo = si
   ```
4. Ejecuta `python3 cambiar_logo.py` y el firmware se generará automáticamente con tu logo adaptado al tema elegido.
