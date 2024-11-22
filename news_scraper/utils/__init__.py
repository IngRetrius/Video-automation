"""
utils/__init__.py: Inicializador del paquete de utilidades
"""

import os
import logging
from pathlib import Path

# Definir paths base
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORAGE_PATH = PROJECT_ROOT / 'storage'
TEMP_PATH = STORAGE_PATH / 'temp' 
MEDIA_PATH = STORAGE_PATH / 'media'
LOGS_PATH = PROJECT_ROOT / 'logs'

# Subdirectorios de media
AUDIO_PATH = MEDIA_PATH / 'audio'
VIDEO_PATH = MEDIA_PATH / 'video'
BACKGROUND_PATH = MEDIA_PATH / 'backgrounds'
BACKGROUND_VIDEOS_PATH = MEDIA_PATH / 'background_videos'
BACKUP_PATH = STORAGE_PATH / 'backups'
REPORTS_PATH = STORAGE_PATH / 'reports'

# Sistema de puntuación para historias
SCORING_CONFIG = {
    'upvotes': {
        'weight': 0.4,
        'thresholds': {
            1000: 100,  # 1000+ upvotes = 100 puntos
            500: 80,
            200: 60,
            100: 40,
            50: 20
        }
    },
    'comments': {
        'weight': 0.3,
        'thresholds': {
            100: 100,  # 100+ comentarios = 100 puntos
            50: 80,
            20: 60,
            10: 40,
            5: 20
        }
    },
    'awards': {
        'weight': 0.2,
        'thresholds': {
            5: 100,   # 5+ premios = 100 puntos
            3: 80,
            2: 60,
            1: 40
        }
    },
    'length': {
        'weight': 0.1,
        'optimal_range': (1000, 5000)  # Rango óptimo de caracteres
    }
}

# Configuración de Video
VIDEO_CONFIG = {
    'format': 'mp4',
    'codec': 'libx264',
    'resolution': '1080x1920',  # Resolución para Shorts
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
    },
    'transitions': {
        'fade_in': 0.2,
        'fade_out': 0.2,
        'cross_fade': 0.0
    }
}

# Configuración de TTS
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

def setup_logging():
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def ensure_directories():
    """Asegura que existan los directorios necesarios"""
    directories = [
        STORAGE_PATH,
        TEMP_PATH,
        MEDIA_PATH,
        AUDIO_PATH,
        VIDEO_PATH,
        BACKGROUND_PATH,
        BACKGROUND_VIDEOS_PATH,
        BACKUP_PATH,
        REPORTS_PATH,
        LOGS_PATH
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logging.debug(f"Directorio asegurado: {directory}")

def cleanup_temp_files():
    """Limpia los archivos temporales"""
    try:
        for file_path in TEMP_PATH.iterdir():
            if file_path.is_file():
                file_path.unlink()
        logging.info("Archivos temporales eliminados")
    except Exception as e:
        logging.error(f"Error eliminando archivos temporales: {e}")

# Configurar logging
setup_logging()

# Asegurar directorios al importar el módulo 
ensure_directories()

# Limpiar temporales al iniciar
cleanup_temp_files()