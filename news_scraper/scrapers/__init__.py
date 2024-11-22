"""
scrapers/__init__.py: Base classes for web scrapers
"""

import os
import sys
import logging
import platform
from pathlib import Path
from typing import Optional

# Configurar el path para importaciones
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Configurar logging
logger = logging.getLogger(__name__)

class BaseWebDriver:
    """Base class for WebDriver configuration."""
    
    @staticmethod
    def get_chrome_options() -> Options:
        """
        Configures and returns Chrome options for scrapers.
        
        Returns:
            Options: Configured Chrome options
        """
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument("--headless=new")  # New headless syntax
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument('--lang=es-419')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Anti-detection options
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Performance options
        chrome_options.add_argument('--disable-features=NetworkService')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Custom user agent
        chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        return chrome_options

class ScraperBase:
    """Base class for all scrapers."""
    
    def __init__(self):
        """Initialize scraper with Chrome driver configuration."""
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.chrome_options = BaseWebDriver.get_chrome_options()

    def start_driver(self):
        """Initialize Chrome driver with Windows-specific configuration."""
        if not self.driver:
            try:
                # Windows-specific configuration
                if platform.system() == 'Windows':
                    driver_path = ChromeDriverManager(version="latest").install()
                    service = Service(executable_path=driver_path)
                else:
                    service = Service(ChromeDriverManager().install())

                self.driver = webdriver.Chrome(
                    service=service,
                    options=self.chrome_options
                )
                self.wait = WebDriverWait(self.driver, 10)
                
                # Configure cookies and localStorage
                self.driver.execute_cdp_cmd('Network.enable', {})
                self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                    'headers': {
                        'Accept-Language': 'es-419,es;q=0.9',
                    }
                })
                
                logger.info("✓ Driver started successfully")
                
            except Exception as e:
                logger.error(f"✗ Error starting driver: {str(e)}")
                if self.driver:
                    self.close_driver()
                raise

    def close_driver(self):
        """Close Chrome driver if active."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✓ Driver closed successfully")
            except Exception as e:
                logger.error(f"✗ Error closing driver: {str(e)}")
            finally:
                self.driver = None
                self.wait = None

    def __enter__(self):
        """Start context manager."""
        self.start_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End context manager."""
        self.close_driver()

# Export classes
__all__ = ['BaseWebDriver', 'ScraperBase']

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)