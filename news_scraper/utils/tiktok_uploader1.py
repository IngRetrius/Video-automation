"""
utils/tiktok_uploader.py: Módulo para subidas a TikTok
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from playwright.async_api import async_playwright

# Configurar path para importaciones
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

# Importaciones locales
from news_scraper.config.settings import TIKTOK_CONFIG, TIKTOK_STORAGE
from news_scraper.config.database import get_db_session
from news_scraper.models.reddit_model import ProcessedContent
from news_scraper.models.tiktok_model import TikTokPublications

# Configurar logging
logger = logging.getLogger(__name__)

class TikTokUploader:
    """Gestiona subidas de videos a TikTok usando automatización con Playwright"""
    
    def __init__(self):
            """Inicializa el uploader de TikTok"""
            self.browser = None
            self.context = None
            self.page = None
            
            # Usar las rutas de configuración desde settings.py
            self.session_file = TIKTOK_STORAGE['session_file']
            self.cookies_file = TIKTOK_STORAGE['cookies_file']
            self.temp_dir = TIKTOK_STORAGE['temp_dir']
            
            # Límites y configuración
            self.MAX_RETRIES = 3
            self.RETRY_DELAY = 5
            self.MAX_DAILY_UPLOADS = TIKTOK_CONFIG['upload_settings']['max_daily_uploads']
            self.UPLOAD_TIMEOUT = 300
            
            # Asegurar que existen los directorios
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
            os.makedirs(self.temp_dir, exist_ok=True)

    async def initialize_browser(self):
        """Inicializa el navegador con Playwright"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # False para ver el proceso durante el desarrollo
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            # Configurar contexto del navegador
            self.context = await self.browser.new_context(
                viewport={'width': 412, 'height': 915},  # Viewport móvil
                user_agent=(
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) '
                    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 '
                    'Mobile/15E148 Safari/604.1'
                )
            )
            
            # Cargar cookies si existen
            if os.path.exists(self.cookies_file):
                try:
                    with open(self.cookies_file, 'r') as f:
                        cookies = json.load(f)
                    await self.context.add_cookies(cookies)
                    logger.info("✓ Cookies cargadas correctamente")
                except Exception as e:
                    logger.warning(f"⚠️ Error cargando cookies: {e}")
            
            self.page = await self.context.new_page()
            logger.info("✓ Navegador inicializado correctamente")
            
        except Exception as e:
            logger.error(f"✗ Error inicializando navegador: {e}")
            await self.cleanup()
            raise

    async def login(self):
        """Realiza el login en TikTok usando credenciales configuradas"""
        try:
            await self.page.goto('https://www.tiktok.com/login')
            
            # Aquí implementarías el proceso de login según el método que uses
            # (puede ser por email, teléfono, etc.)
            
            # Ejemplo básico (ajustar según el método de autenticación):
            await self.page.fill('input[name="email"]', TIKTOK_CONFIG['email'])
            await self.page.fill('input[name="password"]', TIKTOK_CONFIG['password'])
            await self.page.click('button[type="submit"]')
            
            # Esperar a que el login sea exitoso
            await self.page.wait_for_selector('div[data-e2e="profile-icon"]')
            
            # Guardar cookies
            cookies = await self.context.cookies()
            with open(self.session_file, 'w') as f:
                json.dump(cookies, f)
                
            logger.info("✓ Login exitoso")
            
        except Exception as e:
            logger.error(f"✗ Error en login: {e}")
            raise

    async def upload_video(
        self,
        video_path: str,
        cover_path: str,
        title: str,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Sube un video a TikTok usando Playwright
        
        Args:
            video_path: Ruta al video
            cover_path: Ruta a la miniatura
            title: Título del video
            tags: Lista de hashtags
            
        Returns:
            Tuple[bool, Optional[str]]: (éxito, url_del_video)
        """
        try:
            # Verificar archivos
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video no encontrado: {video_path}")
            if not os.path.exists(cover_path):
                raise FileNotFoundError(f"Cover no encontrado: {cover_path}")

            # Ir a la página de subida
            await self.page.goto('https://www.tiktok.com/upload')
            
            # Esperar al input de archivo
            file_input = await self.page.wait_for_selector('input[type="file"]')
            
            # Subir video
            await file_input.set_input_files(video_path)
            
            # Esperar a que el video se procese
            await self.page.wait_for_selector('div[data-e2e="upload-video-preview"]')
            
            # Establecer título
            title_input = await self.page.wait_for_selector('div[data-e2e="video-caption"] textarea')
            await title_input.fill('')  # Limpiar primero
            await title_input.fill(f"{title}\n\n{' '.join(f'#{tag}' for tag in (tags or ['reddit', 'historias', 'viral']))}")
            
            # Subir cover (si el selector está disponible)
            try:
                cover_input = await self.page.wait_for_selector('input[accept="image/*"]', timeout=5000)
                await cover_input.set_input_files(cover_path)
            except Exception as e:
                logger.warning(f"No se pudo establecer el cover: {e}")
            
            # Configurar privacidad (público)
            await self.page.click('div[data-e2e="upload-privacy-public"]')
            
            # Publicar
            post_button = await self.page.wait_for_selector('div[data-e2e="upload-post"]')
            await post_button.click()
            
            # Esperar a que la subida se complete
            success_message = await self.page.wait_for_selector(
                'div[data-e2e="upload-success-message"]',
                timeout=self.UPLOAD_TIMEOUT * 1000
            )
            
            # Obtener URL del video
            video_url = await self.get_video_url()
            
            logger.info(f"✓ Video subido exitosamente: {video_url}")
            return True, video_url
            
        except Exception as e:
            logger.error(f"✗ Error subiendo video: {e}")
            return False, None

    async def get_video_url(self) -> Optional[str]:
        """Obtiene la URL del video recién subido"""
        try:
            # Ir al perfil
            await self.page.goto('https://www.tiktok.com/profile')
            
            # Esperar y obtener el primer video
            video_link = await self.page.wait_for_selector('a[data-e2e="user-post-item-1"]')
            return await video_link.get_attribute('href')
            
        except Exception as e:
            logger.error(f"Error obteniendo URL del video: {e}")
            return None

    async def cleanup(self):
        """Limpia recursos del navegador"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")

    async def process_pending_uploads(self) -> Dict[str, int]:
        """Procesa videos pendientes de subir a TikTok"""
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            # Inicializar navegador
            await self.initialize_browser()
            
            # Login si es necesario
            if not os.path.exists(self.session_file):
                await self.login()
            
            session = get_db_session()
            try:
                # Obtener videos pendientes
                pending_content = (
                    session.query(ProcessedContent)
                    .filter(ProcessedContent.status == 'processed')
                    .filter(ProcessedContent.final_video_path.isnot(None))
                    .filter(ProcessedContent.cover_path.isnot(None))
                    .limit(self.MAX_DAILY_UPLOADS)
                    .all()
                )
                
                stats['total'] = len(pending_content)
                
                for content in pending_content:
                    try:
                        # Verificar archivos
                        if not os.path.exists(content.final_video_path) or \
                           not os.path.exists(content.cover_path):
                            logger.error(f"Archivos faltantes para ID {content.id}")
                            stats['skipped'] += 1
                            continue
                        
                        # Obtener datos de la historia
                        story = content.story
                        
                        # Preparar título y tags
                        title = f"{story.title[:100]}..." if len(story.title) > 100 else story.title
                        tags = ['reddit', 'historias', 'viral', 'storytelling']
                        
                        # Intentar subir
                        success, video_url = await self.upload_video(
                            video_path=content.final_video_path,
                            cover_path=content.cover_path,
                            title=title,
                            tags=tags
                        )
                        
                        if success and video_url:
                            # Registrar publicación
                            tiktok_pub = TikTokPublications(
                                processed_content_id=content.id,
                                tiktok_url=video_url,
                                published_at=datetime.utcnow(),
                                status='published'
                            )
                            session.add(tiktok_pub)
                            
                            # Actualizar estado
                            content.status = 'published'
                            story.status = 'published'
                            
                            session.commit()
                            stats['success'] += 1
                            
                            logger.info(f"✓ Publicación completada: {video_url}")
                        else:
                            stats['failed'] += 1
                            
                        # Esperar entre subidas
                        await asyncio.sleep(TIKTOK_CONFIG.get('upload_delay', 60))
                        
                    except Exception as e:
                        logger.error(f"Error procesando contenido {content.id}: {e}")
                        stats['failed'] += 1
                        continue
                        
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error en proceso de subidas: {e}")
        finally:
            await self.cleanup()
            
        return stats

    def get_upload_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas de subidas"""
        session = get_db_session()
        try:
            today = datetime.utcnow().date()
            
            stats = {
                'total_uploads': session.query(TikTokPublications).count(),
                'uploads_today': session.query(TikTokPublications)
                    .filter(TikTokPublications.published_at >= today)
                    .count(),
                'pending_uploads': session.query(ProcessedContent)
                    .filter(ProcessedContent.status == 'processed')
                    .count(),
                'failed_uploads': session.query(TikTokPublications)
                    .filter(TikTokPublications.status == 'failed')
                    .count()
            }
            
            return stats
        finally:
            session.close()

if __name__ == "__main__":
    async def test_upload():
        uploader = TikTokUploader()
        
        # Mostrar estadísticas iniciales
        print("\nEstadísticas iniciales:")
        stats = uploader.get_upload_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # Procesar subidas pendientes
        print("\nProcesando subidas pendientes...")
        results = await uploader.process_pending_uploads()
        
        print("\nResultados del proceso:")
        for key, value in results.items():
            print(f"{key}: {value}")
        
        # Estadísticas finales
        print("\nEstadísticas finales:")
        stats = uploader.get_upload_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
    
    asyncio.run(test_upload())