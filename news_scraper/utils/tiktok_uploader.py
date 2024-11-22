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
        self.session_file = TIKTOK_STORAGE['session_file']
        self.cookies_file = TIKTOK_STORAGE['cookies_file']
        
        # Límites y configuración
        self.MAX_RETRIES = 3
        self.RETRY_DELAY = 5
        self.MAX_DAILY_UPLOADS = TIKTOK_CONFIG['upload_settings']['max_daily_uploads']
        self.UPLOAD_TIMEOUT = 300
        
        # Asegurar que existen los directorios
        os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)

    async def initialize_browser(self):
        """Inicializa el navegador con Playwright"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--start-maximized'
                ]
            )
            
            # Configurar contexto del navegador
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # Crear nueva página
            self.page = await self.context.new_page()
            
            # Ir a la página de login
            await self.page.goto('https://www.tiktok.com/login')
            await self.page.wait_for_timeout(2000)
            
            logger.info("✓ Navegador inicializado correctamente")
            
        except Exception as e:
            logger.error(f"✗ Error inicializando navegador: {e}")
            await self.cleanup()
            raise

    async def save_cookies(self):
        """Guarda las cookies del navegador"""
        try:
            cookies = await self.context.cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            logger.info("✓ Cookies guardadas correctamente")
        except Exception as e:
            logger.error(f"✗ Error guardando cookies: {e}")

    async def check_login_status(self) -> bool:
        """Verifica si estamos logueados en TikTok"""
        try:
            # Verificar elementos que solo aparecen cuando estamos logueados
            try:
                await self.page.wait_for_selector('div[data-e2e="profile-icon"]', timeout=3000)
                logger.info("✓ Sesión válida encontrada")
                return True
            except:
                logger.info("✗ No hay sesión válida")
                return False
        except Exception as e:
            logger.error(f"Error verificando login: {e}")
            return False


    async def login(self):
        """Realiza el login en TikTok usando Google"""
        try:
            logger.info("Iniciando proceso de login con Google...")
            
            # Buscar y hacer clic en el botón de "Continuar con Google"
            google_button = await self.page.wait_for_selector('button:has-text("Continuar con Google")')
            await google_button.click()
            
            # Esperar a que aparezca la ventana de Google
            await self.page.wait_for_timeout(2000)
            
            # Obtener todas las páginas/ventanas
            pages = self.context.pages
            google_popup = pages[-1]  # La última página debería ser el popup de Google
            
            # Esperar y llenar el email
            email_input = await google_popup.wait_for_selector('input[type="email"]')
            await email_input.fill(TIKTOK_CONFIG['email'])
            await google_popup.click('button:has-text("Siguiente")')
            
            # Esperar y llenar la contraseña
            password_input = await google_popup.wait_for_selector('input[type="password"]')
            await password_input.fill(TIKTOK_CONFIG['password'])
            await google_popup.click('button:has-text("Siguiente")')
            
            # Esperar a que se complete el login y se cierre el popup
            await self.page.wait_for_timeout(5000)
            
            # Verificar si el login fue exitoso
            if await self.check_login_status():
                await self.save_cookies()
                logger.info("✓ Login con Google exitoso")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error durante login con Google: {e}")
            return False

    def get_upload_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas de subidas (versión sin DB para pruebas)"""
        return {
            'total_uploads': 0,
            'uploads_today': 0,
            'pending_uploads': 0,
            'failed_uploads': 0
        }

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

    # Método ejemplo para subir video
    async def upload_video(
        self,
        video_path: str,
        title: str,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Sube un video a TikTok
        
        Args:
            video_path: Ruta al video
            title: Título del video
            tags: Lista de hashtags
            
        Returns:
            Tuple[bool, Optional[str]]: (éxito, url_del_video)
        """
        if not os.path.exists(video_path):
            logger.error(f"Video no encontrado: {video_path}")
            return False, None
            
        try:
            # Aquí iría la lógica de subida real
            logger.info("Función de subida en desarrollo")
            return True, "https://www.tiktok.com/@usuario/video/123456789"
        except Exception as e:
            logger.error(f"Error subiendo video: {e}")
            return False, None