"""
tests/test_video_generator.py: Tests para el generador de videos
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Agregar el directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Ahora podemos importar los módulos del proyecto
from utils.video_generator import VideoGenerator

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Historia de prueba
test_story = {
    'reddit_id': 'test_story_001',
    'title': 'Historia de Prueba para Generación de Video',
    'author': 'TestUser123',
    'content': '''Esta es una historia de prueba para verificar la generación de video.
    
    El sistema debería procesar este texto y generar los subtítulos correspondientes.
    
    También verificamos el manejo de múltiples párrafos y diferentes longitudes de texto
    para asegurar que el sistema funcione correctamente en diversos escenarios.''',
    'url': 'https://reddit.com/r/HistoriasDeReddit/test'
}

async def run_test():
    try:
        print("\n" + "="*50)
        print("Iniciando prueba de generación de video")
        print("="*50)
        
        generator = VideoGenerator()
        
        print("\nDatos de la historia:")
        print(f"Título: {test_story['title']}")
        print(f"Autor: u/{test_story['author']}")
        print(f"Longitud del contenido: {len(test_story['content'])} caracteres")
        
        # Generar video
        print("\nGenerando video...")
        video_path = await generator.create_story_video(test_story)
        
        print("\n" + "="*50)
        print("Resultados:")
        print("="*50)
        print(f"\n✓ Video generado exitosamente")
        print(f"Ubicación: {video_path}")
        
        # Verificar el archivo
        if os.path.exists(video_path):
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            print(f"Tamaño del archivo: {size_mb:.2f} MB")
        else:
            print("\n⚠ El archivo de video no se encontró en la ubicación esperada")
        
    except Exception as e:
        print("\n" + "="*50)
        print("Error en la generación:")
        print("="*50)
        print(f"\n✗ {str(e)}")
        logging.exception("Detalles completos del error:")

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n\nError crítico: {e}")
        logging.exception("Error crítico durante la ejecución:")