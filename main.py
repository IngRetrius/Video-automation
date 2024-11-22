"""
main.py: Script principal para la automatización completa de historias de Reddit
"""

import sys
import time
import asyncio
from pathlib import Path
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import structlog
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import Session, sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential

# Agregar el directorio al path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

# Importaciones locales
from news_scraper.config.database import Base, get_db_session, save_stories_to_db
from news_scraper.config.settings import DATABASE_CONFIG, SCRAPING_CONFIG
from news_scraper.models.reddit_model import RedditStories, ErrorLogs, ProcessedContent
from news_scraper.scrapers.reddit_scraper import RedditScraper
from news_scraper.utils.video_generator import VideoGenerator
from news_scraper.utils.tiktok_cover_generator import TikTokCoverGenerator
from news_scraper.utils import (
    STORAGE_PATH,
    BACKUP_PATH,
    REPORTS_PATH,
    VIDEO_CONFIG,
    SCORING_CONFIG,
    cleanup_temp_files
)

# Configurar logging estructurado
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory()
)

logger = structlog.get_logger(__name__)

class RedditManager:
    """Gestiona las operaciones de historias y base de datos"""
    
    def __init__(self):
        """Inicializa el gestor de historias"""
        self.engine = None
        self.SessionLocal = None
        self.video_generator = VideoGenerator()
        self.cover_generator = TikTokCoverGenerator()
        self.initialize_database()
        cleanup_temp_files()

    def initialize_database(self):
        """Configura la conexión a la base de datos"""
        try:
            connection_string = (
                f"mysql+mysqlconnector://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@"
                f"{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
            )
            self.engine = create_engine(
                connection_string,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            # Crear tablas si no existen
            Base.metadata.create_all(self.engine)
            logger.info("database_initialized", status="success")
        except Exception as e:
            logger.error("database_initialization_failed", error=str(e))
            raise

    def _get_shortened_title(self, title: str, max_length: int = 50) -> str:
        """
        Genera un título abreviado para el archivo
        
        Args:
            title: Título original
            max_length: Longitud máxima permitida
            
        Returns:
            str: Título abreviado y limpio
        """
        # Convertir a minúsculas y reemplazar caracteres no válidos
        clean_title = title.lower()
        clean_title = ''.join(c if c.isalnum() or c.isspace() else '-' for c in clean_title)
        
        # Reemplazar espacios múltiples por uno solo
        clean_title = '-'.join(filter(None, clean_title.split()))
        
        # Truncar si es necesario
        if len(clean_title) <= max_length:
            return clean_title
            
        # Cortar en el último espacio antes del límite
        return clean_title[:max_length].rsplit('-', 1)[0]

    def log_error(self, error_type: str, error_message: str, related_id: int = None):
        """Registra un error en la base de datos"""
        session = get_db_session()
        try:
            error_log = ErrorLogs(
                related_table='reddit_stories',
                related_id=related_id,
                error_type=error_type,
                error_message=error_message
            )
            session.add(error_log)
            session.commit()
            logger.error(error_type, error=error_message, related_id=related_id)
        except Exception as e:
            logger.error("error_logging_failed", error=str(e))
        finally:
            session.close()

    def cleanup_old_data(self, days: int = 30):
        """Limpia datos antiguos de la base de datos"""
        session = get_db_session()
        try:
            # Eliminar historias antiguas
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted_stories = session.query(RedditStories).filter(
                RedditStories.collected_at < cutoff_date
            ).delete()

            # Eliminar registros de error antiguos
            deleted_errors = session.query(ErrorLogs).filter(
                ErrorLogs.error_timestamp < cutoff_date
            ).delete()

            session.commit()
            logger.info("cleanup_completed", 
                       deleted_stories=deleted_stories,
                       deleted_errors=deleted_errors)
            
        except Exception as e:
            session.rollback()
            self.log_error("cleanup_error", str(e))
        finally:
            session.close()

    async def process_videos(self):
        """Procesa las historias pendientes y genera videos y covers"""
        try:
            videos = await self.video_generator.process_top_stories()
            processed_items = []
            
            if videos:
                session = get_db_session()
                try:
                    for video_path in videos:
                        try:
                            # Extraer el ID de Reddit del nombre del archivo
                            filename = os.path.basename(video_path)
                            reddit_id = filename.split('_')[-1].split('.')[0]  # Obtener el ID al final del nombre
                            
                            logger.info(f"Procesando video para reddit_id: {reddit_id}")
                            
                            # Buscar la historia en la base de datos usando reddit_id
                            story = session.query(RedditStories).filter(
                                RedditStories.reddit_id.contains(reddit_id)
                            ).first()
                            
                            if story:
                                # Generar nombre abreviado
                                short_title = self._get_shortened_title(story.title)
                                base_filename = f"{short_title}_{reddit_id}"
                                
                                logger.info(f"Generando cover para historia: {story.title}")
                                
                                # Generar cover
                                cover_path = self.cover_generator.create_cover(
                                    title=story.title,
                                    output_name=base_filename
                                )
                                
                                logger.info(f"Cover generado: {cover_path}")
                                
                                # Actualizar ProcessedContent
                                processed_content = session.query(ProcessedContent)\
                                    .filter_by(story_id=story.id)\
                                    .first()
                                    
                                if processed_content:
                                    processed_content.cover_path = cover_path
                                    session.commit()
                                    
                                    processed_items.append({
                                        'video': video_path,
                                        'cover': cover_path,
                                        'title': short_title,
                                        'original_title': story.title,
                                        'author': story.author,
                                        'score': story.importance_score,
                                        'reddit_id': reddit_id
                                    })
                                    
                                    logger.info(f"Procesamiento completo para historia {reddit_id}")
                            else:
                                logger.error(f"No se encontró la historia para el ID: {reddit_id}")
                                
                        except Exception as e:
                            logger.error(f"Error procesando video individual: {e}")
                            continue
                    
                    # Registrar resultado final
                    logger.info(f"Procesamiento completado. {len(processed_items)} items generados")
                    
                except Exception as e:
                    logger.error(f"Error en el procesamiento de la sesión: {e}")
                finally:
                    session.close()
            
            # Mostrar resumen detallado
            if processed_items:
                print("\nContenido generado:")
                print("-" * 50)
                for item in processed_items:
                    print(f"\nTítulo: {item['original_title']}")
                    print(f"ID: {item['reddit_id']}")
                    print(f"Título abreviado: {item['title']}")
                    print(f"Autor: u/{item['author']}")
                    print(f"Score: {item['score']}")
                    print(f"Video: {os.path.basename(item['video'])}")
                    print(f"Cover: {os.path.basename(item['cover'])}")
                    print("-" * 30)
            
            return len(processed_items), processed_items
            
        except Exception as e:
            logger.error(f"Error en process_videos: {str(e)}")
            return 0, []

    def get_system_stats(self) -> Dict:
        """Obtiene estadísticas del sistema"""
        session = get_db_session()
        try:
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            
            stats = {
                'total_stories': session.query(RedditStories).count(),
                'recent_stories': session.query(RedditStories).filter(
                    RedditStories.collected_at >= recent_cutoff
                ).count(),
                'high_importance_stories': session.query(RedditStories).filter(
                    RedditStories.importance_score >= SCORING_CONFIG['upvotes']['thresholds'][500]
                ).count(),
                'pending_processing': session.query(RedditStories).filter(
                    RedditStories.status == 'pending'
                ).count(),
                'processed_videos': session.query(ProcessedContent).filter(
                    ProcessedContent.final_video_path.isnot(None)
                ).count(),
                'recent_errors': session.query(ErrorLogs).filter(
                    ErrorLogs.error_timestamp >= recent_cutoff,
                    ErrorLogs.resolved == False
                ).count(),
            }
            
            return stats
        finally:
            session.close()

async def main():
    """Función principal del programa"""
    start_time = time.time()
    logger.info("process_started")
    
    try:
        # Inicializar el gestor de historias
        reddit_manager = RedditManager()
        
        # Limpiar datos antiguos
        reddit_manager.cleanup_old_data()
        
        # Obtener historias nuevas
        scraper = RedditScraper()
        stories = scraper.fetch_stories(limit=SCRAPING_CONFIG['MAX_STORIES'])
            
        if not stories:
            logger.warning("no_stories_found")
            saved_count = updated_count = 0
        else:
            # Guardar historias
            session = get_db_session()
            try:
                stats = save_stories_to_db(stories, session)
                saved_count = stats['saved']
                updated_count = stats['updated']
            finally:
                session.close()

        # Procesar videos y generar covers
        logger.info("starting_video_processing")
        videos_count, processed_items = await reddit_manager.process_videos()
            
        # Obtener estadísticas
        system_stats = reddit_manager.get_system_stats()
        
        # Registrar resultados
        execution_time = time.time() - start_time
        logger.info(
            "process_completed",
            execution_time=f"{execution_time:.2f}s",
            new_stories=saved_count,
            updated_stories=updated_count,
            videos_generated=videos_count,
            **system_stats
        )
        
        # Imprimir resumen para humanos
        print("\nResumen de ejecución:")
        print("-" * 50)
        print(f"Tiempo de ejecución: {execution_time:.2f} segundos")
        print(f"Nuevas historias guardadas: {saved_count}")
        print(f"Historias actualizadas: {updated_count}")
        print(f"Videos generados: {videos_count}")
        
        if processed_items:
            print("\nContenido generado:")
            print("-" * 50)
            for item in processed_items:
                print(f"\nTítulo original: {item['original_title']}")
                print(f"Título abreviado: {item['title']}")
                print(f"Autor: u/{item['author']}")
                print(f"Score: {item['score']}")
                print(f"Video: {os.path.basename(item['video'])}")
                print(f"Cover: {os.path.basename(item['cover'])}")
        
        print(f"\nEstadísticas del sistema:")
        print("-" * 50)
        print(f"Total de historias: {system_stats['total_stories']}")
        print(f"Historias recientes (24h): {system_stats['recent_stories']}")
        print(f"Historias de alta importancia: {system_stats['high_importance_stories']}")
        print(f"Pendientes de procesar: {system_stats['pending_processing']}")
        print(f"Videos procesados: {system_stats['processed_videos']}")
        print(f"Errores recientes: {system_stats['recent_errors']}")
        
        if stories:
            print("\nÚltimas historias importantes:")
            print("-" * 50)
            for story in sorted(stories, 
                             key=lambda x: x['importance_score'], 
                             reverse=True)[:5]:
                print(f"\n- {story['title']}")
                print(f"  Autor: u/{story['author']}")
                print(f"  Score: {story['importance_score']}")
                print(f"  Upvotes: {story['score']}")
                print(f"  Comentarios: {story['num_comments']}")
        
    except KeyboardInterrupt:
        logger.warning("process_interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error("process_failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())