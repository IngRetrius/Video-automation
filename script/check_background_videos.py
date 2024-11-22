"""
Script para verificar y preparar videos de fondo
"""

import os
import sys
import shutil
from pathlib import Path

# Añadir el directorio raíz al path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from news_scraper.utils import BACKGROUND_VIDEOS_PATH

def check_background_videos():
    """Verifica y prepara los videos de fondo"""
    
    # Crear directorio si no existe
    os.makedirs(BACKGROUND_VIDEOS_PATH, exist_ok=True)
    
    # Verificar contenido del directorio
    videos = [f for f in os.listdir(BACKGROUND_VIDEOS_PATH) 
             if f.endswith(('.mp4', '.mov', '.avi'))]
    
    print("\nVerificación de videos de fondo:")
    print(f"Directorio: {BACKGROUND_VIDEOS_PATH}")
    print(f"Videos encontrados: {len(videos)}")
    
    if not videos:
        print("\n⚠ No se encontraron videos de fondo!")
        print("Por favor, coloca algunos videos de fondo en el directorio:")
        print(f"{BACKGROUND_VIDEOS_PATH}")
        print("\nFormatos soportados: .mp4, .mov, .avi")
        
        # Crear video de ejemplo si no hay ninguno
        create_example = input("\n¿Desea crear un video de ejemplo? (s/n): ")
        if create_example.lower() == 's':
            try:
                # Crear un video de ejemplo usando MoviePy
                from moviepy.editor import ColorClip
                duration = 30  # 30 segundos
                size = (1920, 1080)
                
                # Crear un video negro
                color_clip = ColorClip(size=size, color=(0, 0, 0), duration=duration)
                
                # Guardar el video
                example_path = os.path.join(BACKGROUND_VIDEOS_PATH, 'example_background.mp4')
                color_clip.write_videofile(
                    example_path,
                    fps=30,
                    codec='libx264',
                    audio=False
                )
                
                print(f"\n✓ Video de ejemplo creado: {example_path}")
            except Exception as e:
                print(f"\n✗ Error creando video de ejemplo: {e}")
    else:
        print("\nVideos disponibles:")
        for video in videos:
            full_path = os.path.join(BACKGROUND_VIDEOS_PATH, video)
            size_mb = os.path.getsize(full_path) / (1024 * 1024)
            print(f"- {video} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    check_background_videos()