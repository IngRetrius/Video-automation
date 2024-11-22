"""
tests/test_tiktok_upload.py: Script de prueba completo para el uploader de TikTok
"""

import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Configurar path del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_VIDEOS_PATH = PROJECT_ROOT / 'storage' / 'test_videos'
TEST_COVERS_PATH = PROJECT_ROOT / 'storage' / 'test_covers'

# Crear directorios de prueba si no existen
TEST_VIDEOS_PATH.mkdir(parents=True, exist_ok=True)
TEST_COVERS_PATH.mkdir(parents=True, exist_ok=True)

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title: str):
    """Imprime una sección con formato"""
    print(f"\n{'-' * 50}")
    print(f"{title}")
    print(f"{'-' * 50}\n")

def generate_test_files():
    """Genera archivos de prueba si no existen"""
    from news_scraper.utils.video_generator import VideoGenerator
    from PIL import Image, ImageDraw, ImageFont
    
    # Generar video de prueba si no existe
    video_path = TEST_VIDEOS_PATH / 'test_video.mp4'
    if not video_path.exists():
        print("Generando video de prueba...")
        generator = VideoGenerator()
        # Generar un video simple de prueba
        # Aquí puedes usar la lógica de generación que prefieras
    
    # Generar cover de prueba si no existe
    cover_path = TEST_COVERS_PATH / 'test_cover.jpg'
    if not cover_path.exists():
        print("Generando cover de prueba...")
        img = Image.new('RGB', (1080, 1920), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
            
        text = "Video de prueba TikTok"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (1080 - text_width) // 2
        y = (1920 - text_height) // 2
        
        draw.text((x, y), text, fill='black', font=font)
        img.save(str(cover_path), quality=95)
        print(f"✓ Cover generado: {cover_path}")

async def test_tiktok_config():
    """Prueba la configuración de TikTok"""
    from news_scraper.config.settings import TIKTOK_CONFIG, TIKTOK_STORAGE
    
    print_section("Verificación de Configuración")
    
    required_configs = [
        'email', 'password', 'username'
    ]
    
    missing_configs = [
        config for config in required_configs 
        if not TIKTOK_CONFIG.get(config)
    ]
    
    if missing_configs:
        print("✗ Configuraciones faltantes:")
        for config in missing_configs:
            print(f"  - {config}")
        return False
    
    print("✓ Configuraciones básicas presentes")
    
    # Verificar directorios
    for name, path in TIKTOK_STORAGE.items():
        if os.path.exists(path):
            print(f"✓ {name}: {path}")
        else:
            print(f"✗ {name} no encontrado: {path}")
    
    return True

async def test_login(uploader):
    """Prueba el proceso de login"""
    print_section("Proceso de Login")
    
    print("\n⚡ IMPORTANTE:")
    print("1. Se abrirá una ventana del navegador")
    print("2. Espere a que aparezca el CAPTCHA")
    print("3. Complete el CAPTCHA manualmente")
    print("4. El script esperará hasta 60 segundos")
    print("\nNota: Si ya existe una sesión válida, se usará automáticamente.")
    
    input("\nPresione Enter cuando esté listo para continuar...")
    
    login_success = await uploader.login()
    
    if login_success:
        print("\n✓ Login completado exitosamente")
        print("  Las cookies han sido guardadas para futuras sesiones")
        return True
    else:
        print("\n✗ Login fallido")
        return False

async def main():
    try:
        from news_scraper.utils.tiktok_uploader import TikTokUploader
        
        print_section("Test de TikTok Uploader")
        
        # Verificar configuración
        if not await test_tiktok_config():
            print("\n✗ Por favor complete la configuración en .env")
            return
        
        # Generar archivos de prueba
        generate_test_files()
        
        # Crear instancia del uploader
        uploader = TikTokUploader()
        print("✓ Uploader instanciado correctamente")
        
        # Mostrar estadísticas iniciales
        print("\nEstadísticas iniciales:")
        stats = uploader.get_upload_stats()
        for key, value in stats.items():
            print(f"- {key}: {value}")
        
        # Inicializar navegador
        print("\nInicializando navegador...")
        await uploader.initialize_browser()
        print("✓ Navegador inicializado correctamente")
        
        # Probar login
        if not await test_login(uploader):
            print("\n✗ No se pudo completar el login. Abortando pruebas.")
            return
        
        # Si llegamos aquí, el login fue exitoso
        print("\nPrueba de funcionalidades adicionales...")
        
        # Verificar estado de la sesión
        session_valid = await uploader.check_login_status()
        print(f"\nEstado de la sesión: {'✓ Válida' if session_valid else '✗ Inválida'}")
        
        # Intentar subir video de prueba si existe
        test_video = TEST_VIDEOS_PATH / 'test_video.mp4'
        test_cover = TEST_COVERS_PATH / 'test_cover.jpg'
        
        if test_video.exists() and test_cover.exists():
            print("\nProbando subida de video...")
            success, video_url = await uploader.upload_video(
                video_path=str(test_video),
                cover_path=str(test_cover),
                title="Video de prueba automatizado",
                tags=["test", "automatizacion", "python"]
            )
            
            if success:
                print(f"✓ Video subido exitosamente: {video_url}")
            else:
                print("✗ Error subiendo video")
        
        # Obtener estadísticas finales
        print("\nEstadísticas finales:")
        final_stats = uploader.get_upload_stats()
        for key, value in final_stats.items():
            print(f"- {key}: {value}")
        
    except Exception as e:
        print(f"\n✗ Error durante la prueba: {e}")
        logger.exception("Error detallado:")
        
    finally:
        if 'uploader' in locals():
            print("\nLimpiando recursos...")
            await uploader.cleanup()
            print("✓ Recursos liberados correctamente")
        
        print("\n=== Prueba finalizada ===")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nPrueba interrumpida por el usuario")
    except Exception as e:
        print(f"\nError crítico: {e}")
        logger.exception("Error detallado del sistema:")