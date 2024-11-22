import os
from moviepy.editor import TextClip
from moviepy.config import change_settings

def verify_imagemagick():
    """Verifica la instalación y configuración de ImageMagick"""
    print("\nVerificando ImageMagick...")
    print("-" * 50)
    
    # Rutas posibles
    possible_paths = [
        r"C:\Program Files\ImageMagick-7.1.1-Q16\magick.exe",
        r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
        r"C:\Program Files (x86)\ImageMagick-7.1.1-Q16\magick.exe",
        r"C:\Program Files\ImageMagick-7.1.1-Q16\convert.exe"
    ]
    
    # Verificar cada ruta
    found = False
    for path in possible_paths:
        if os.path.exists(path):
            print(f"\n✓ ImageMagick encontrado en: {path}")
            found = True
            
            try:
                # Configurar MoviePy
                change_settings({"IMAGEMAGICK_BINARY": path})
                
                # Probar creación de texto
                print("\nProbando creación de texto...")
                clip = TextClip("Test", fontsize=30)
                clip.close()
                print("✓ Prueba exitosa!")
                return path
                
            except Exception as e:
                print(f"✗ Error en prueba: {e}")
    
    if not found:
        print("\n✗ ImageMagick no encontrado")
        print("\nPor favor:")
        print("1. Descarga ImageMagick desde: https://imagemagick.org/script/download.php#windows")
        print("2. Durante la instalación marca 'Install legacy utilities'")
        print("3. Reinicia el sistema")
    
    return None

if __name__ == "__main__":
    result = verify_imagemagick()
    if result:
        print(f"\nUsa esta ruta en tu configuración:")
        print(f'IMAGEMAGICK_BINARY = r"{result}"')