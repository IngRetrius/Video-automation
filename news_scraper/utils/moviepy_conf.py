import os

# Configuración local de MoviePy
IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"

if not os.path.exists(IMAGEMAGICK_BINARY):
    print(f"⚠️ ADVERTENCIA: ImageMagick no encontrado en {IMAGEMAGICK_BINARY}")
    print("Por favor:")
    print("1. Descarga ImageMagick desde: https://imagemagick.org/script/download.php#windows")
    print("2. Instálalo marcando 'Install legacy utilities'")
    print("3. Actualiza la ruta IMAGEMAGICK_BINARY si es necesario")