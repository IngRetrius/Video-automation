"""
tests/test_tiktok_basic.py: Prueba básica del uploader
"""

import asyncio
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        from news_scraper.utils.tiktok_uploader import TikTokUploader
        
        print("\n=== Prueba básica de TikTok Uploader ===")
        
        # Crear instancia
        uploader = TikTokUploader()
        print("✓ Uploader instanciado correctamente")
        
        # Obtener estadísticas
        print("\nEstadísticas del sistema:")
        stats = uploader.get_upload_stats()
        for key, value in stats.items():
            print(f"- {key}: {value}")
            
        # Probar inicialización del navegador
        print("\nInicializando navegador...")
        await uploader.initialize_browser()
        print("✓ Navegador inicializado correctamente")
        
        # Limpiar recursos
        print("\nLimpiando recursos...")
        await uploader.cleanup()
        print("✓ Recursos liberados correctamente")
        
    except Exception as e:
        print(f"\n✗ Error durante la prueba: {e}")
        logger.exception("Error detallado:")
        
    print("\n=== Prueba finalizada ===")

if __name__ == "__main__":
    asyncio.run(main())