"""
database.py: Configuración y utilidades de base de datos
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
import mysql.connector
from mysql.connector import Error
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configurar path para importaciones
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

# Configurar logging
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'reddit_stories_automation'),
    'port': os.getenv('DB_PORT', '3306'),
    'charset': 'utf8mb4'
}

# Crear metadata compartido y base declarativa
metadata = MetaData()
Base = declarative_base(metadata=metadata)

def get_db_connection():
    """
    Crear conexión a la base de datos usando mysql-connector
    
    Returns:
        Optional[mysql.connector.connection.MySQLConnection]: Conexión a la base de datos
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            logger.info('✓ Conexión exitosa a la base de datos')
            return connection
    except Error as e:
        logger.error(f'✗ Error al conectar a la base de datos: {e}')
        return None

def get_sqlalchemy_engine():
    """
    Crear engine de SQLAlchemy para ORM
    
    Returns:
        Optional[Engine]: Engine de SQLAlchemy
    """
    try:
        connection_string = (
            f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
            f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
            f"?charset={DB_CONFIG['charset']}"
        )
        engine = create_engine(
            connection_string,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True  # Verifica conexiones antes de usarlas
        )
        return engine
    except Exception as e:
        logger.error(f'✗ Error al crear engine de SQLAlchemy: {e}')
        return None

# Crear el engine
engine = get_sqlalchemy_engine()

# Crear la fábrica de sesiones
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Evita recargas innecesarias
)

def get_db_session():
    """
    Obtener una sesión de base de datos.
    Para usar como context manager.
    
    Returns:
        Session: Sesión de SQLAlchemy
    
    Raises:
        Exception: Si hay error al crear la sesión
    """
    session = SessionLocal()
    try:
        return session
    except Exception as e:
        session.close()
        raise e

def save_stories_to_db(stories: List[Dict[str, Any]], session) -> Dict[str, int]:
    """
    Guarda una lista de historias en la base de datos
    """
    from news_scraper.models.reddit_model import RedditStories
    
    stats = {
        'total': len(stories),
        'saved': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0
    }
    
    for story_data in stories:
        try:
            existing_story = session.query(RedditStories).filter_by(
                reddit_id=story_data['reddit_id']
            ).first()
            
            if existing_story:
                if (existing_story.score != story_data['score'] or 
                    existing_story.num_comments != story_data['num_comments']):
                    
                    existing_story.score = story_data['score']
                    existing_story.upvote_ratio = story_data['upvote_ratio']
                    existing_story.num_comments = story_data['num_comments']
                    existing_story.awards_received = story_data['awards_received']
                    existing_story.importance_score = story_data['importance_score']
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            else:
                new_story = RedditStories(
                    reddit_id=story_data['reddit_id'],
                    title=story_data['title'],
                    content=story_data['content'],
                    author=story_data['author'],
                    score=story_data['score'],
                    upvote_ratio=story_data['upvote_ratio'],
                    num_comments=story_data['num_comments'],
                    post_flair=story_data.get('post_flair'),
                    is_nsfw=story_data['is_nsfw'],
                    awards_received=story_data['awards_received'],
                    url=story_data['url'],
                    created_utc=story_data['created_utc'],
                    collected_at=story_data['collected_at'],
                    importance_score=story_data['importance_score'],
                    language=story_data['language'],
                    status=story_data['status'],
                    extra_data=story_data.get('extra_data', {})  # Cambiado metadata por extra_data
                )
                session.add(new_story)
                stats['saved'] += 1
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error guardando historia {story_data.get('title', 'Unknown')}: {e}")
            stats['failed'] += 1
            continue
    
    # Registrar resultados
    logger.info(f"Resumen de guardado:")
    logger.info(f"- Total procesadas: {stats['total']}")
    logger.info(f"- Nuevas guardadas: {stats['saved']}")
    logger.info(f"- Actualizadas: {stats['updated']}")
    logger.info(f"- Sin cambios: {stats['skipped']}")
    logger.info(f"- Fallidas: {stats['failed']}")
    
    return stats

def init_db():
    """
    Inicializar la base de datos creando todas las tablas
    
    Returns:
        bool: True si se crearon las tablas exitosamente
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Tablas creadas exitosamente")
        return True
    except Exception as e:
        logger.error(f"✗ Error al crear tablas: {e}")
        return False

def test_connection():
    """
    Probar la conexión a la base de datos
    
    Returns:
        bool: True si la conexión es exitosa
    """
    conn = get_db_connection()
    if conn and conn.is_connected():
        try:
            db_info = conn.get_server_info()
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE();")
            database_name = cursor.fetchone()
            logger.info(f"✓ Conectado a MySQL Server version {db_info}")
            logger.info(f"✓ Conectado a la base de datos: {database_name[0]}")
            return True
        finally:
            cursor.close()
            conn.close()
            logger.info("✓ Conexión cerrada")
    return False

if __name__ == "__main__":
    # Configurar logging para pruebas
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Probar conexión
    if test_connection():
        print("\n✓ Pruebas de conexión exitosas")
        
        # Inicializar base de datos
        if init_db():
            print("✓ Base de datos inicializada correctamente")
    else:
        print("\n✗ Error en las pruebas de conexión")