"""
reddit_scraper.py: Scraper específico para r/HistoriasDeReddit
"""

import os
import sys
from pathlib import Path
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional

# Configurar el path para importaciones
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Importaciones de terceros
import praw
from praw.models import Submission
from tenacity import retry, stop_after_attempt, wait_exponential

# Importaciones locales
from config.settings import (
    SCRAPING_CONFIG,
    SCORING_CONFIG,
)

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedditScraper:
    """Scraper optimizado para r/HistoriasDeReddit"""
    
    def __init__(self):
        """Inicializa el scraper de Reddit con la configuración de PRAW"""
        self.subreddit_name = "HistoriasDeReddit"
        self.logger = logger
        
        # Inicializar cliente de Reddit
        try:
            self.reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                user_agent=os.getenv('REDDIT_USER_AGENT', 'HistoriasBot/1.0')
            )
            self.logger.info("Reddit client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit client: {e}")
            raise

    def calculate_importance_score(self, submission: Submission) -> tuple[float, dict]:
        """
        Calcula el score de importancia de una historia
        
        Args:
            submission: Objeto Submission de PRAW
            
        Returns:
            tuple[float, dict]: Score de importancia (0-100) y desglose
        """
        score = 0.0
        breakdown = {}

        try:
            # 1. Puntuación por upvotes
            upvotes_weight = SCORING_CONFIG['upvotes']['weight']
            for threshold, points in sorted(SCORING_CONFIG['upvotes']['thresholds'].items(), reverse=True):
                if submission.score >= threshold:
                    score += points * upvotes_weight
                    breakdown['upvotes'] = points * upvotes_weight
                    break

            # 2. Puntuación por comentarios
            comments_weight = SCORING_CONFIG['comments']['weight']
            for threshold, points in sorted(SCORING_CONFIG['comments']['thresholds'].items(), reverse=True):
                if submission.num_comments >= threshold:
                    score += points * comments_weight
                    breakdown['comments'] = points * comments_weight
                    break

            # 3. Puntuación por premios
            awards_weight = SCORING_CONFIG['awards']['weight']
            total_awards = len(submission.all_awardings) if hasattr(submission, 'all_awardings') else 0
            for threshold, points in sorted(SCORING_CONFIG['awards']['thresholds'].items(), reverse=True):
                if total_awards >= threshold:
                    score += points * awards_weight
                    breakdown['awards'] = points * awards_weight
                    break

            # 4. Puntuación por longitud
            length_weight = SCORING_CONFIG['length']['weight']
            content_length = len(submission.selftext)
            optimal_min, optimal_max = SCORING_CONFIG['length']['optimal_range']
            
            if optimal_min <= content_length <= optimal_max:
                length_score = 100
            elif content_length < optimal_min:
                length_score = (content_length / optimal_min) * 100
            else:
                length_score = max(0, 100 - ((content_length - optimal_max) / optimal_max) * 50)
            
            score += length_score * length_weight
            breakdown['length'] = length_score * length_weight

        except Exception as e:
            self.logger.error(f"Error calculating importance score: {e}")
            return 0.0, {'error': str(e)}

        return round(min(max(score, 0), 100), 2), breakdown

    def clean_submission(self, submission: Submission) -> Optional[Dict]:
        """
        Limpia y estructura los datos de una submission
        
        Args:
            submission: Objeto Submission de PRAW
            
        Returns:
            Optional[Dict]: Datos limpios de la historia o None si es inválida
        """
        try:
            # Validar contenido mínimo
            if len(submission.selftext.strip()) < SCRAPING_CONFIG['MIN_LENGTH']:
                self.logger.warning(f"Submission too short: {submission.id}")
                return None

            # Calcular score
            importance_score, score_breakdown = self.calculate_importance_score(submission)

            # Estructurar datos
            cleaned_data = {
                'reddit_id': submission.id,
                'title': submission.title.strip(),
                'content': submission.selftext.strip(),
                'author': str(submission.author) if submission.author else '[deleted]',
                'score': submission.score,
                'upvote_ratio': submission.upvote_ratio,
                'num_comments': submission.num_comments,
                'post_flair': submission.link_flair_text if submission.link_flair_text else None,
                'is_nsfw': submission.over_18,
                'awards_received': len(submission.all_awardings) if hasattr(submission, 'all_awardings') else 0,
                'url': f"https://reddit.com{submission.permalink}",
                'created_utc': datetime.fromtimestamp(submission.created_utc),
                'collected_at': datetime.utcnow(),
                'importance_score': importance_score,
                'language': 'es',
                'status': 'pending',
                'metadata': {
                    'score_breakdown': score_breakdown,
                    'content_length': len(submission.selftext),
                    'edited': bool(submission.edited),
                    'distinguished': submission.distinguished,
                }
            }

            return cleaned_data

        except Exception as e:
            self.logger.error(f"Error cleaning submission {submission.id}: {e}")
            return None

    @retry(
        stop=stop_after_attempt(SCRAPING_CONFIG['MAX_RETRIES']),
        wait=wait_exponential(multiplier=SCRAPING_CONFIG['RETRY_DELAY'], min=4, max=10)
    )
    def fetch_stories(self, limit: int = SCRAPING_CONFIG['MAX_STORIES']) -> List[Dict]:
        """
        Obtiene las historias más relevantes del subreddit
        
        Args:
            limit: Número máximo de historias a obtener
            
        Returns:
            List[Dict]: Lista de historias procesadas
        """
        try:
            self.logger.info(f"Fetching stories from r/{self.subreddit_name}")
            subreddit = self.reddit.subreddit(self.subreddit_name)
            stories = []

            # Obtener historias usando diferentes ordenamientos
            for sort_method in ['hot', 'top', 'new']:
                try:
                    if sort_method == 'top':
                        submissions = subreddit.top(time_filter='week', limit=limit)
                    elif sort_method == 'hot':
                        submissions = subreddit.hot(limit=limit)
                    else:
                        submissions = subreddit.new(limit=limit)

                    for submission in submissions:
                        # Ignorar posts que no son historias
                        if submission.is_self and not submission.stickied:
                            cleaned_story = self.clean_submission(submission)
                            if cleaned_story:
                                stories.append(cleaned_story)
                
                except Exception as e:
                    self.logger.error(f"Error fetching {sort_method} stories: {e}")
                    continue

            # Eliminar duplicados por reddit_id
            unique_stories = {story['reddit_id']: story for story in stories}
            stories = list(unique_stories.values())

            # Ordenar por importance_score y limitar
            stories.sort(key=lambda x: x['importance_score'], reverse=True)
            top_stories = stories[:limit]

            self.logger.info(f"Fetched {len(top_stories)}/{len(stories)} stories")
            return top_stories

        except Exception as e:
            self.logger.error(f"Error fetching stories: {e}")
            return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

if __name__ == "__main__":
    try:
        # Probar el scraper
        scraper = RedditScraper()
        stories = scraper.fetch_stories()
        
        print(f"\nHistorias obtenidas: {len(stories)}")
        if stories:
            print("\nTop 3 historias:")
            for i, story in enumerate(stories[:3], 1):
                print(f"\n{i}. {story['title']}")
                print(f"Score: {story['importance_score']}")
                print(f"Upvotes: {story['score']}")
                print(f"Comentarios: {story['num_comments']}")
                print(f"Longitud: {story['metadata']['content_length']} caracteres")
    except Exception as e:
        logger.error(f"Error running scraper: {e}")