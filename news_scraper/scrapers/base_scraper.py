# scrapers/base_scraper.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import logging
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from . import ScraperBase
from config.settings import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    DEFAULT_COUNTRY,
    RELIABLE_SOURCES,
    PRIORITY_KEYWORDS,
    PRIORITY_CATEGORIES,
    IMPORTANCE_SCORING,
    MAX_RETRIES,
    RETRY_DELAY,
    MAX_NEWS_ITEMS
)

logger = structlog.get_logger(__name__)

class BaseScraper(ScraperBase, ABC):
    """Clase base mejorada para todos los scrapers de noticias"""
    
    def __init__(self, language: str = DEFAULT_LANGUAGE, country: str = DEFAULT_COUNTRY):
        """
        Inicializa el scraper con configuración mejorada
        
        Args:
            language (str): Idioma objetivo para noticias
            country (str): País objetivo para noticias
        """
        super().__init__()  # Inicializa ScraperBase
        
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Idioma {language} no soportado. Use uno de {SUPPORTED_LANGUAGES}")
        
        self.language = language
        self.country = country
        self._setup_logging()

    def _setup_logging(self):
        """Configura logging estructurado específico para el scraper"""
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def fetch_news(self) -> List[Dict]:
        """
        Obtiene noticias de la fuente
        
        Returns:
            List[Dict]: Lista de noticias con sus metadatos
        """
        pass

    def calculate_importance_score(self, article: Dict) -> float:
        """
        Calcula el score de importancia usando el nuevo sistema de pesos
        
        Args:
            article (Dict): Datos del artículo
            
        Returns:
            float: Score de importancia (0-10)
        """
        score = 0.0
        
        # 1. Puntuación por fuente confiable
        source = article.get('source', '').strip()
        source_score = RELIABLE_SOURCES.get(source, 0)
        score += source_score * IMPORTANCE_SCORING['SOURCE_WEIGHT']
        
        # 2. Puntuación por palabras clave
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        keyword_matches = sum(
            PRIORITY_KEYWORDS.get(keyword, 0)
            for keyword in PRIORITY_KEYWORDS
            if keyword in text
        )
        normalized_keyword_score = min(keyword_matches / 10, 1) * 10
        score += normalized_keyword_score * IMPORTANCE_SCORING['KEYWORDS_WEIGHT']
        
        # 3. Puntuación por longitud de contenido
        content = article.get('description', '')
        content_length = len(content)
        length_score = min(content_length / 1000, 1) * 10  # Normalizar a 10
        score += length_score * IMPORTANCE_SCORING['CONTENT_LENGTH_WEIGHT']
        
        # 4. Puntuación por categorías
        category_score = 0
        for category, weight in PRIORITY_CATEGORIES.items():
            if category.lower() in text:
                category_score = max(category_score, weight)
        score += category_score * IMPORTANCE_SCORING['RELEVANCE_WEIGHT']
        
        # 5. Puntuación por actualidad
        collection_time = article.get('collection_date', datetime.utcnow())
        hours_old = (datetime.utcnow() - collection_time).total_seconds() / 3600
        recency_score = max(0, 10 - (hours_old / 2))  # -1 punto cada 2 horas
        score += recency_score * IMPORTANCE_SCORING['RECENCY_WEIGHT']
        
        return round(min(max(score, 0), 10), 2)

    def clean_article(self, article: Dict) -> Optional[Dict]:
        """
        Limpia y valida un artículo antes de guardarlo
        
        Args:
            article (Dict): Datos del artículo sin procesar
            
        Returns:
            Optional[Dict]: Artículo limpio o None si es inválido
        """
        try:
            # Validar campos requeridos
            required_fields = ['title', 'url']
            if not all(field in article for field in required_fields):
                self.logger.warning("missing_required_fields", 
                                  url=article.get('url', 'No URL'))
                return None

            # Limpiar y estructurar el artículo
            cleaned_article = {
                'title': article['title'].strip(),
                'url': article['url'].strip(),
                'source': article.get('source', 'Unknown').strip(),
                'description': article.get('description', '').strip(),
                'language': self.language,
                'country': self.country,
                'collection_date': datetime.utcnow(),
                'metadata': {
                    'original_url': article.get('original_url'),
                    'keywords': article.get('keywords', []),
                    'categories': article.get('categories', []),
                    'has_image': article.get('has_image', False),
                }
            }
            
            # Calcular score de importancia
            cleaned_article['importance_score'] = self.calculate_importance_score(cleaned_article)
            
            return cleaned_article
            
        except Exception as e:
            self.logger.error("article_cleaning_failed", error=str(e))
            return None

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_DELAY, min=4, max=10)
    )
    async def process_batch(self, articles: List[Dict]) -> List[Dict]:
        """
        Procesa un lote de artículos con reintentos
        
        Args:
            articles (List[Dict]): Lista de artículos sin procesar
            
        Returns:
            List[Dict]: Lista de artículos limpios y validados
        """
        processed_articles = []
        
        for article in articles:
            try:
                cleaned_article = self.clean_article(article)
                if cleaned_article:
                    processed_articles.append(cleaned_article)
            except Exception as e:
                self.logger.error("article_processing_failed", 
                                title=article.get('title', 'Unknown'),
                                error=str(e))
                continue
        
        # Ordenar por importancia y limitar a MAX_NEWS_ITEMS
        processed_articles.sort(key=lambda x: x['importance_score'], reverse=True)
        return processed_articles[:MAX_NEWS_ITEMS]