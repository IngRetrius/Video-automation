"""
settings.py: Configuración centralizada del sistema de automatización de Reddit Stories.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging.config
import json

# Cargar variables de entorno
load_dotenv()

# Paths base
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_PATH = os.path.join(BASE_DIR, 'storage')
MEDIA_PATH = os.path.join(STORAGE_PATH, 'media')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Paths específicos para media
AUDIO_PATH = os.path.join(MEDIA_PATH, 'audio')
VIDEO_PATH = os.path.join(MEDIA_PATH, 'video')
BACKGROUND_PATH = os.path.join(MEDIA_PATH, 'backgrounds')
BACKGROUND_VIDEOS_PATH = os.path.join(MEDIA_PATH, 'background_videos')
TEMP_PATH = os.path.join(STORAGE_PATH, 'temp')
BACKUP_PATH = os.path.join(STORAGE_PATH, 'backups')
REPORTS_PATH = os.path.join(STORAGE_PATH, 'reports')

# Crear directorios necesarios
REQUIRED_PATHS = [
    STORAGE_PATH,
    MEDIA_PATH,
    LOGS_DIR,
    AUDIO_PATH,
    VIDEO_PATH,
    BACKGROUND_PATH,
    BACKGROUND_VIDEOS_PATH,
    TEMP_PATH,
    BACKUP_PATH,
    REPORTS_PATH
]

for path in REQUIRED_PATHS:
    os.makedirs(path, exist_ok=True)

# Configuración de Base de Datos
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'reddit_stories_automation'),
    'charset': 'utf8mb4'
}

# Configuración de Redis para caché
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('REDIS_PASSWORD', None),
}

# Configuración de Sentry para monitoreo
SENTRY_DSN = os.getenv('SENTRY_DSN')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Configuración de Reddit
REDDIT_CONFIG = {
    'client_id': os.getenv('REDDIT_CLIENT_ID'),
    'client_secret': os.getenv('REDDIT_CLIENT_SECRET'),
    'user_agent': os.getenv('REDDIT_USER_AGENT', 'HistoriasBot/1.0'),
    'username': os.getenv('REDDIT_USERNAME'),
    'password': os.getenv('REDDIT_PASSWORD'),
    'subreddit': 'HistoriasDeReddit',
    'post_limit': 100
}

# Configuración de Scraping
SCRAPING_CONFIG = {
    'MAX_STORIES': 50,
    'MIN_LENGTH': 200,
    'MAX_LENGTH': 10000,
    'MIN_SCORE': 10,
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 2,
    'TIMEOUT': 30,
    'INTERVAL': 3600,
    'USER_AGENT_ROTATION': True,
    'PROXIES_ENABLED': False
}

# Sistema de puntuación para historias
SCORING_CONFIG = {
    'upvotes': {
        'weight': 0.4,
        'thresholds': {
            1000: 100,
            500: 80,
            200: 60,
            100: 40,
            50: 20
        }
    },
    'comments': {
        'weight': 0.3,
        'thresholds': {
            100: 100,
            50: 80,
            20: 60,
            10: 40,
            5: 20
        }
    },
    'awards': {
        'weight': 0.2,
        'thresholds': {
            5: 100,
            3: 80,
            2: 60,
            1: 40
        }
    },
    'length': {
        'weight': 0.1,
        'optimal_range': (1000, 5000)
    }
}

# Configuración de Text-to-Speech
TTS_CONFIG = {
    'provider': 'edge',
    'language': 'es-ES',
    'voice': 'es-ES-AlvaroNeural',
    'audio_format': 'wav',
    'sample_rate': 24000,
    'speaking_rate': 1.0,
    'pitch': 0,
    'volume_gain_db': 2,
    'max_concurrent': 3,
    'chunk_size': 4096,
    'subtitle_words_per_line': 4,
    'duration_per_line': 3.0,
    'voice_options': {
        'default': 'es-ES-AlvaroNeural',
        'alternative': 'es-ES-ElviraNeural',
        'emotion': 'dramatic'
    }
}

# Configuración de Video
VIDEO_CONFIG = {
    'format': 'mp4',
    'codec': 'libx264',
    'resolution': '1080x1920',
    'fps': 30,
    'audio_codec': 'aac',
    'audio_bitrate': '192k',
    'video_bitrate': '4M',
    'background_blur': 5,
    'text_config': {
        'font_size': 60,
        'font_color': 'white',
        'font': 'Impact',
        'bg_color': 'rgba(0,0,0,0.6)',
        'position': 'center',
        'duration': 4,
        'margin_top': 50,
        'stroke_color': 'black',
        'stroke_width': 3,
        'outer_stroke_width': 5,
        'outer_stroke_color': 'black'
    },
    'title_config': {
        'font_size': 60,
        'font_color': 'white',
        'font': 'Impact',
        'bg_color': 'rgba(0,0,0,0.6)',
        'position': 'center',
        'duration': 4,
        'margin_top': 50,
        'stroke_color': 'black',
        'stroke_width': 3,
        'outer_stroke_width': 5,
        'outer_stroke_color': 'black'
    },
    'transitions': {
        'fade_in': 0.2,
        'fade_out': 0.2,
        'cross_fade': 0.0
    },
    'background': {
        'video_path': BACKGROUND_VIDEOS_PATH,
        'allowed_extensions': ['.mp4', '.mov', '.avi'],
        'volume': 0.0,
        'loop': True,
        'blur': 0,
        'brightness': 0.5,
        'resize_mode': 'cover',
        'position': 'center',
        'scale': 1.2,
        'zoom_effect': {
            'enabled': True,
            'speed': 0.1,
            'max_zoom': 1.3
        }
    }
}

# Configuración de TikTok
TIKTOK_STORAGE = {
    'session_file': os.path.join(STORAGE_PATH, 'tiktok', 'session.json'),
    'cookies_file': os.path.join(STORAGE_PATH, 'tiktok', 'cookies.json'),
    'temp_dir': os.path.join(TEMP_PATH, 'tiktok')
}

TIKTOK_CONFIG = {
    'email': os.getenv('TIKTOK_EMAIL', 'http://redditspirit.es'),
    'password': os.getenv('TIKTOK_PASSWORD', 'R3dd1t.es'),
    'username': os.getenv('TIKTOK_USERNAME', '@redditspirit_es'),
    'session_id': os.getenv('TIKTOK_SESSION_ID', ''),
    'ms_token': os.getenv('TIKTOK_MS_TOKEN', ''),
    'upload_settings': {
        'max_daily_uploads': int(os.getenv('TIKTOK_MAX_DAILY_UPLOADS', 10)),
        'upload_delay': int(os.getenv('TIKTOK_UPLOAD_DELAY', 60)),
        'start_hour': int(os.getenv('TIKTOK_UPLOAD_START_HOUR', 9)),
        'end_hour': int(os.getenv('TIKTOK_UPLOAD_END_HOUR', 23))
    },
    'default_tags': [
        'reddit',
        'historias',
        'viral',
        'storytelling',
        'reddithistorias'
    ]
}

# Crear directorios necesarios para TikTok
TIKTOK_DIRECTORIES = [
    os.path.dirname(TIKTOK_STORAGE['session_file']),
    os.path.dirname(TIKTOK_STORAGE['cookies_file']),
    TIKTOK_STORAGE['temp_dir']
]

for path in TIKTOK_DIRECTORIES:
    os.makedirs(path, exist_ok=True)

# Configuración de YouTube
YOUTUBE_CONFIG = {
    'api_key': os.getenv('YOUTUBE_API_KEY'),
    'client_secrets_file': os.path.join(BASE_DIR, 'client_secrets.json'),
    'credentials_file': os.path.join(STORAGE_PATH, 'youtube_credentials.json'),
    'channel_id': os.getenv('YOUTUBE_CHANNEL_ID'),
    'upload_defaults': {
        'category': '22',
        'privacy': 'private',
        'language': 'es',
        'tags': ['historias', 'reddit', 'HistoriasDeReddit', 'stories', 'shorts'],
        'title_template': "Historia de Reddit: {title} #shorts",
        'description_template': """
{title}

Historia original por u/{author} en r/HistoriasDeReddit
{url}

#shorts #historias #reddit #viral #trending
        """.strip(),
        'monetization': {
            'enable_ads': True,
            'self_declared_made_for_kids': False
        }
    },
    'max_retries': 3,
    'chunk_size': 1024 * 1024,
    'schedule_time': {
        'enabled': True,
        'interval_hours': 3,
        'start_time': '09:00',
        'end_time': '23:00',
        'time_zone': 'America/Bogota'
    }
}

# Inicializar logging
def setup_logging():
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

setup_logging()

if __name__ == "__main__":
    print("✓ Configuración cargada correctamente")