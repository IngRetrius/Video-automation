"""
tests/generate_test_content.py: Genera contenido de prueba para TikTok
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2

def generate_test_video(output_path: str, duration: int = 10):
    """Genera un video de prueba"""
    # Configurar video
    fps = 30
    width = 1080
    height = 1920
    
    # Crear writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Generar frames
    for i in range(duration * fps):
        # Crear frame con gradiente
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        gradient = np.linspace(0, 255, height, dtype=np.uint8)
        frame[:, :, 0] = gradient[:, np.newaxis]  # Rojo
        frame[:, :, 1] = 255 - gradient[:, np.newaxis]  # Verde
        
        # Agregar texto
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"Frame de prueba: {i+1}"
        cv2.putText(frame, text, (50, height//2), font, 2, (255,255,255), 3)
        
        out.write(frame)
    
    out.release()
    print(f"✓ Video de prueba generado: {output_path}")

def generate_test_cover(output_path: str):
    """Genera una imagen de cover de prueba"""
    # Crear imagen
    img = Image.new('RGB', (1080, 1920), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        # Intentar usar Arial, si no está disponible usar default
        font = ImageFont.truetype('arial.ttf', 60)
    except:
        font = ImageFont.load_default()
    
    # Agregar texto
    text = "Cover de prueba\nGenerado automáticamente"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Centrar texto
    x = (1080 - text_width) // 2
    y = (1920 - text_height) // 2
    
    # Dibujar texto
    draw.text((x, y), text, font=font, fill='black')
    
    # Guardar
    img.save(output_path, quality=95)
    print(f"✓ Cover de prueba generado: {output_path}")

def main():
    # Paths
    project_root = Path(__file__).resolve().parent.parent
    test_videos_path = project_root / 'storage' / 'test_videos'
    test_covers_path = project_root / 'storage' / 'test_covers'
    
    # Crear directorios si no existen
    test_videos_path.mkdir(parents=True, exist_ok=True)
    test_covers_path.mkdir(parents=True, exist_ok=True)
    
    # Generar contenido
    video_path = str(test_videos_path / 'test_video.mp4')
    cover_path = str(test_covers_path / 'test_cover.jpg')
    
    print("\nGenerando contenido de prueba...")
    generate_test_video(video_path)
    generate_test_cover(cover_path)
    
    print("\n✓ Contenido de prueba generado correctamente")
    print(f"Video: {video_path}")
    print(f"Cover: {cover_path}")

if __name__ == "__main__":
    main()