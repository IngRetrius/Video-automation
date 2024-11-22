"""
utils/video_generator.py: Generador de videos verticales para historias de Reddit
"""

import os
import sys
import glob
import random
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Dict, List, Union, Tuple
from datetime import datetime, timedelta

# Añadir el directorio raíz al path de Python
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

# Importaciones científicas
import numpy as np
from scipy.ndimage import gaussian_filter

# Importaciones para procesamiento de imágenes
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
try:
    from PIL.ImageDraw import ImageDraw as PillowImageDraw
    has_rounded_rectangle = hasattr(PillowImageDraw, 'rounded_rectangle')
except ImportError:
    has_rounded_rectangle = False

# Importaciones para procesamiento multimedia
import edge_tts
import srt
from moviepy.editor import (
    AudioFileClip, 
    TextClip, 
    CompositeVideoClip,
    VideoFileClip,
    ImageClip,
    concatenate_videoclips,
    vfx
)

# Configuración específica de ImageMagick y MoviePy
from moviepy.config import change_settings
from moviepy.tools import subprocess_call
from news_scraper.utils.moviepy_conf import IMAGEMAGICK_BINARY

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Agregar handler para archivo
file_handler = logging.FileHandler('video_generator.log')
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(file_handler)

def verify_imagemagick():
    """Verifica y configura ImageMagick HDRI"""
    try:
        if not os.path.exists(IMAGEMAGICK_BINARY):
            logger.error(f"ImageMagick no encontrado en: {IMAGEMAGICK_BINARY}")
            return False
            
        # Configurar MoviePy
        change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})
        
        # Verificar que funciona
        test_clip = TextClip("Test", fontsize=30, font="Arial")
        test_clip.close()
        
        logger.info(f"✓ ImageMagick configurado correctamente: {IMAGEMAGICK_BINARY}")
        return True
        
    except Exception as e:
        logger.error(f"Error configurando ImageMagick: {e}")
        return False

# Verificar ImageMagick al inicio
if not verify_imagemagick():
    logger.error("""
    ✗ ImageMagick no configurado correctamente.
    Por favor verifica:
    1. Que ImageMagick esté instalado
    2. Que la ruta en moviepy_conf.py sea correcta
    3. Que los legacy utilities estén instalados
    """)
    sys.exit(1)

# Importaciones SQL
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

# Importaciones locales del proyecto
from news_scraper.config.database import get_db_session
from news_scraper.models.reddit_model import (
    RedditStories, 
    ProcessedContent, 
    YoutubePublications,
    ErrorLogs
)
from news_scraper.utils import (
    VIDEO_CONFIG,
    TTS_CONFIG,
    STORAGE_PATH,
    MEDIA_PATH,
    BACKGROUND_VIDEOS_PATH,
    TEMP_PATH,
    VIDEO_PATH,
    BACKGROUND_PATH,
    cleanup_temp_files
)


class VideoGenerator:
    """Generador de videos optimizado"""
    
    def __init__(self):
        """Inicializa el generador de videos"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configurar rutas usando las variables importadas directamente
        self.temp_dir = TEMP_PATH
        self.video_dir = VIDEO_PATH
        self.background_dir = BACKGROUND_PATH
        self.background_videos_dir = BACKGROUND_VIDEOS_PATH
        
        # Dimensiones de video
        self.width = 1080
        self.height = 1920
        
        # Configuraciones
        self.MIN_SCORE = 25
        self.MAX_VIDEOS = 3
        self.SIMILARITY_THRESHOLD = 0.85
        
        # Rutas de fuentes y configuración
        self.font_paths = {

            'nunito': (
                r"C:\Windows\Fonts\NunitoSans-Black.ttf",  # Para los subtítulos
                r"C:\Windows\Fonts\NunitoSans-ExtraBold.ttf",  # Alternativa
                r"C:\Windows\Fonts\arial.ttf",  # Fallback
            ),
            'lexend': (
                r"C:\Windows\Fonts\Lexend-SemiBold.ttf",  # Principal
                r"C:\Windows\Fonts\Lexend-Bold.ttf",      # Alternativa
                r"C:\Windows\Fonts\arial.ttf",
            ),
            'bebas': (

                r"C:\Windows\Fonts\BebasNeue-Regular.ttf",
                r"C:\Windows\Fonts\Impact.ttf",
                   
            ),
            'impact': (
                r"C:\Windows\Fonts\Impact.ttf",
                r"C:\Windows\Fonts\arial.ttf",

            ),
            'Ebisu': (
                r"C:\Windows\Fonts\Ebisu-Bold.ttf",
                r"C:\Windows\Fonts\Impact.ttf",

            ),
        }
        self.font_size = {
            'title': 72,      # Tamaño para título
            'username': 60,   # Tamaño para @redditspirit_es
            'subtitles': 60   # Tamaño para subtítulos
        }
        
        # Rutas de assets
        self.assets_dir = os.path.join(project_root, "assets")
        self.logo_path = os.path.join(self.assets_dir, "reddit_spirit_logo.png")
        
        # Verificar fuentes y assets
        self.available_fonts = self._verify_fonts()
        self._ensure_assets()
        
        # Limpiar temporales y asegurar directorios
        cleanup_temp_files()
        self._ensure_directories()

    def round_corners(self, image: Image, radius: int) -> Image:
        """Redondea las esquinas de una imagen manteniendo la opacidad original"""
        # Asegurar que la imagen está en modo RGBA
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # Crear máscara para las esquinas redondeadas
        mask = Image.new('L', (radius * 2, radius * 2), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, radius * 2 - 1, radius * 2 - 1], fill=255)

        # Crear una nueva imagen con el mismo tamaño y un fondo transparente
        output = Image.new('RGBA', image.size, (0, 0, 0, 0))
        
        # Copiar la imagen original
        output.paste(image, (0, 0))
        
        # Obtener los canales alpha originales
        original_alpha = image.split()[3]
        
        # Crear nueva máscara del tamaño de la imagen
        full_mask = Image.new('L', output.size, 255)
        
        # Pegar las esquinas redondeadas en la máscara
        full_mask.paste(mask.crop((0, 0, radius, radius)), (0, 0))
        full_mask.paste(mask.crop((radius, 0, radius * 2, radius)), (output.width - radius, 0))
        full_mask.paste(mask.crop((0, radius, radius, radius * 2)), (0, output.height - radius))
        full_mask.paste(mask.crop((radius, radius, radius * 2, radius * 2)), 
                    (output.width - radius, output.height - radius))
        
        # Combinar la máscara original con la nueva
        final_mask = Image.new('L', output.size, 255)
        final_mask.paste(full_mask, (0, 0))
        final_mask = ImageChops.multiply(final_mask, original_alpha)
        
        # Aplicar la máscara final
        output.putalpha(final_mask)
        
        return output
    
    def _verify_fonts(self) -> Dict[str, str]:
        """Verifica y retorna las fuentes disponibles"""
        available = {}
        for font_name, paths in self.font_paths.items():
            for path in paths:
                if os.path.exists(path):
                    available[font_name] = path
                    self.logger.info(f"Fuente {font_name} encontrada: {path}")
                    break
            if font_name not in available:
                self.logger.warning(f"No se encontró la fuente {font_name}, usando default")
        return available

    def _get_font(self, font_name: str, size: int) -> ImageFont:
        """Obtiene una fuente con fallback"""
        try:
            if font_name in self.available_fonts:
                return ImageFont.truetype(self.available_fonts[font_name], size)
            return ImageFont.load_default()
        except Exception as e:
            self.logger.warning(f"Error cargando fuente {font_name}: {e}")
            return ImageFont.load_default()

    def _ensure_assets(self):
        """Verifica y asegura la existencia de assets necesarios"""
        try:
            # Verificar directorio de assets
            if not os.path.exists(self.assets_dir):
                os.makedirs(self.assets_dir)
                self.logger.info(f"Directorio de assets creado: {self.assets_dir}")
            
            # Verificar logo
            if not os.path.exists(self.logo_path):
                self.logger.error(f"Logo no encontrado en: {self.logo_path}")
                raise FileNotFoundError(f"Logo no encontrado: {self.logo_path}")
            
            # Verificar fuentes disponibles
            if not self.available_fonts:
                self.logger.warning("No se encontraron fuentes configuradas")
                
        except Exception as e:
            self.logger.error(f"Error verificando assets: {e}")
            raise

    def _ensure_directories(self):
        """Verifica que existan todos los directorios necesarios"""
        REQUIRED_PATHS = [
            STORAGE_PATH,
            MEDIA_PATH,
            BACKGROUND_VIDEOS_PATH,
            TEMP_PATH,
            VIDEO_PATH,
            BACKGROUND_PATH,
            self.assets_dir
        ]
        
        for path in REQUIRED_PATHS:
            try:
                os.makedirs(path, exist_ok=True)
                self.logger.debug(f"Directorio asegurado: {path}")
            except Exception as e:
                self.logger.error(f"Error creando directorio {path}: {e}")

    def _get_random_background_video(self) -> str:
        """
        Selecciona aleatoriamente un video de fondo
        
        Returns:
            str: Ruta al video seleccionado
        """
        try:
            self.logger.info(f"Buscando videos en: {self.background_videos_dir}")
            
            allowed_extensions = ['.mp4', '.mov', '.avi']
            video_files = []
            
            for ext in allowed_extensions:
                pattern = os.path.join(self.background_videos_dir, f"*{ext}")
                found = glob.glob(pattern)
                video_files.extend(found)
                self.logger.debug(f"Buscando {pattern}: encontrados {len(found)} archivos")

            if video_files:
                selected = random.choice(video_files)
                self.logger.info(f"Video seleccionado: {selected}")
                return selected
                
            raise FileNotFoundError(f"No se encontraron videos en {self.background_videos_dir}")
                
        except Exception as error:
            self.logger.error(f"Error seleccionando video de fondo: {error}")
            raise

    async def text_to_audio(
        self, 
        text: str, 
        output_path: str,
        voice: Optional[str] = None
    ) -> tuple[str, List[Dict]]:
        """
        Convierte texto a audio y obtiene los tiempos de cada frase
        
        Args:
            text: Texto a convertir
            output_path: Ruta donde guardar el archivo de audio
            voice: Voz a utilizar (opcional)
            
        Returns:
            tuple[str, List[Dict]]: Ruta del audio y lista de tiempos
        """
        try:
            voice = voice or TTS_CONFIG['voice']
            communicate = edge_tts.Communicate(text, voice=voice)
            
            timings = []
            
            with open(output_path, "wb") as file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        timings.append({
                            'text': chunk["text"],
                            'start': chunk["offset"] / 10000000,
                            'end': (chunk["offset"] + chunk["duration"]) / 10000000
                        })
            
            self.logger.info(f"Audio generado: {output_path}")
            return output_path, timings
            
        except Exception as error:
            self.logger.error(f"Error generando audio: {error}")
            raise

    def create_subtitles(
        self,
        text: str,
        timings: List[Dict],
        words_per_line: int = 4
    ) -> str:
        """
        Genera subtítulos agrupados por palabras
        """
        try:
            lines = []
            current_words = []
            start_time = None
            
            for timing in timings:
                if timing['text'].strip():
                    if not start_time:
                        start_time = timing['start']
                    
                    current_words.append(timing['text'])
                    
                    if (len(current_words) >= words_per_line or 
                        timing['text'].strip().endswith(('.', ',', '?', '!', ':'))):
                        lines.append({
                            'text': ' '.join(current_words).strip().upper(),
                            'start': start_time,
                            'end': timing['end'] + 0.3
                        })
                        current_words = []
                        start_time = None

            if current_words:
                lines.append({
                    'text': ' '.join(current_words).strip().upper(),
                    'start': start_time,
                    'end': timings[-1]['end'] + 0.3
                })

            # Crear subtítulos SRT
            subs = []
            for i, line in enumerate(lines, 1):
                subs.append(srt.Subtitle(
                    index=i,
                    start=timedelta(seconds=line['start']),
                    end=timedelta(seconds=line['end']),
                    content=line['text']
                ))

            return srt.compose(subs)

        except Exception as e:
            self.logger.error(f"Error creando subtítulos: {e}")
            raise

    def _format_time(self, seconds: float) -> str:
        """Formatea tiempo para SRT"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def create_intro_clip(self, title: str, duration: float = 4.0) -> VideoFileClip:
        """
        Crea un clip de introducción con el estilo personalizado
        
        Args:
            title: Título a mostrar
            duration: Duración en segundos
            
        Returns:
            VideoFileClip: Clip de introducción
        """
        try:
            # Crear imagen base con PIL
            img = Image.new('RGB', (self.width, self.height), 'white')
            draw = ImageDraw.Draw(img)

            try:
                # Cargar y verificar logo
                logo_path = os.path.join(self.assets_dir, "reddit_spirit_logo.png")
                if not os.path.exists(logo_path):
                    self.logger.error(f"Logo no encontrado en: {logo_path}")
                    raise FileNotFoundError(f"Logo no encontrado: {logo_path}")
                    
                logo = Image.open(logo_path)
                logo_size = 200
                logo = logo.resize((logo_size, logo_size))
                
                # Posición del logo
                logo_x = (self.width - logo_size) // 2
                logo_y = self.height // 4 - logo_size
                
                # Pegar logo con manejo de transparencia
                if logo.mode == 'RGBA':
                    img.paste(logo, (logo_x, logo_y), logo)
                else:
                    img.paste(logo, (logo_x, logo_y))

                # Cargar fuentes
                try:
                    title_font = ImageFont.truetype(self.font_path, 96)
                    username_font = ImageFont.truetype(self.font_path, 72)
                except Exception as e:
                    self.logger.error(f"Error cargando fuentes: {e}")
                    raise
                
                # Agregar nombre de usuario
                username = "@redditspirit_es"
                username_bbox = draw.textbbox((0, 0), username, font=username_font)
                username_width = username_bbox[2] - username_bbox[0]
                username_x = (self.width - username_width) // 2
                username_y = logo_y + logo_size + 30
                
                # Dibujar sombra del username
                for offset in range(3):
                    draw.text(
                        (username_x + offset, username_y + offset),
                        username,
                        font=username_font,
                        fill="#bcc1c4"
                    )
                    
                # Dibujar username
                draw.text(
                    (username_x, username_y),
                    username,
                    font=username_font,
                    fill="black"
                )
                
                # Procesar título
                title = title.upper()
                words = title.split()
                lines = []
                current_line = []
                
                # Dividir título en líneas
                for word in words:
                    current_line.append(word)
                    test_line = ' '.join(current_line)
                    bbox = draw.textbbox((0, 0), test_line, font=title_font)
                    if bbox[2] - bbox[0] > self.width - 100:
                        current_line.pop()
                        lines.append(' '.join(current_line))
                        current_line = [word]
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Dibujar título
                title_y = self.height // 2
                for i, line in enumerate(lines):
                    bbox = draw.textbbox((0, 0), line, font=title_font)
                    line_width = bbox[2] - bbox[0]
                    x = (self.width - line_width) // 2
                    y = title_y + i * (title_font.size + 20)
                    
                    # Dibujar sombra del título
                    for offset in range(5):
                        draw.text(
                            (x + offset, y + offset),
                            line,
                            font=title_font,
                            fill="#bcc1c4"
                        )
                        
                    # Dibujar línea del título
                    draw.text(
                        (x, y),
                        line,
                        font=title_font,
                        fill="black"
                    )
                
                # Guardar imagen temporalmente
                temp_path = os.path.join(self.temp_dir, "temp_intro.png")
                img.save(temp_path, quality=95)
                
                # Crear clip de video
                intro_clip = (ImageClip(temp_path)
                            .set_duration(duration)
                            .fadein(0.5)
                            .fadeout(0.5))
                
                # Limpiar archivo temporal
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                return intro_clip
                
            except Exception as e:
                self.logger.error(f"Error procesando imagen de intro: {e}")
                raise
                
        except Exception as error:
            self.logger.error(f"Error creando clip de intro: {error}")
            raise


    async def _create_video(
        self,
        text: str,
        audio_path: str,
        background_video: str,
        output_path: str,
        timings: List[Dict]
    ) -> str:
        """Crea el video final con overlay y subtítulos"""
        clips = []
        try:
            # Cargar audio y video de fondo
            audio_clip = AudioFileClip(audio_path)
            total_duration = audio_clip.duration

            # Preparar video de fondo
            background_clip = VideoFileClip(background_video)
            if background_clip.duration < total_duration:
                n_loops = int(np.ceil(total_duration / background_clip.duration))
                background_clip = vfx.loop(background_clip, n=n_loops)
            background_clip = background_clip.subclip(0, total_duration)
            
            # Ajustar tamaño del video de fondo
            bg_aspect = background_clip.size[0] / background_clip.size[1]
            target_aspect = self.width / self.height
            
            if bg_aspect > target_aspect:
                new_width = int(self.height * bg_aspect)
                background_clip = background_clip.resize(height=self.height)
                background_clip = background_clip.crop(
                    x1=(new_width-self.width)/2,
                    x2=(new_width+self.width)/2,
                    y1=0,
                    y2=self.height
                )
            else:
                new_height = int(self.width / bg_aspect)
                background_clip = background_clip.resize(width=self.width)
                background_clip = background_clip.crop(
                    x1=0,
                    x2=self.width,
                    y1=(new_height-self.height)/2,
                    y2=(new_height+self.height)/2
                )
            
            # Crear overlay de introducción
            intro_duration = 4.0
            overlay_clip = self.create_intro_overlay(
                title=text.split('\n')[0],  # Solo el título principal
                size=(200, 200),  # Tamaño más pequeño del logo
                position=('center', 100),  # Más arriba en la pantalla
                duration=intro_duration
            ).set_start(0)  # Comenzar desde el inicio
            
            # Crear clips de texto para el contenido
            text_clips = []
            start_time = intro_duration  # Comenzar subtítulos después de la intro
            
            for timing in timings:
                if timing['text'].strip():
                    clip = (TextClip(
                        txt=timing['text'],
                        font='impact',
                        fontsize=60,
                        color='white',
                        stroke_color='black',
                        stroke_width=2,
                        size=(self.width - 100, None),
                        method='caption'
                    )
                    .set_position(('center', 'center'))
                    .set_start(timing['start'])
                    .set_duration(timing['end'] - timing['start'])
                    .crossfadein(0.2)
                    .crossfadeout(0.2))
                    
                    text_clips.append(clip)
            
            # Combinar todos los clips
            clips = [
                background_clip,  # Fondo
                overlay_clip,     # Overlay de introducción
                *text_clips      # Subtítulos
            ]
            
            # Crear video final
            final_clip = (CompositeVideoClip(clips, size=(self.width, self.height))
                        .set_duration(total_duration)
                        .set_audio(audio_clip))
            
            # Renderizar video
            final_clip.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                bitrate='4M',
                threads=4,
                preset='medium'
            )
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error creando video: {e}")
            raise
            
        finally:
            # Limpiar clips
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
            
            if 'audio_clip' in locals():
                audio_clip.close()
            if 'background_clip' in locals():
                background_clip.close()
            if 'final_clip' in locals():
                final_clip.close()

    def _prepare_text(self, story_data: Dict[str, str]) -> str:
        """
        Prepara el texto para TTS incluyendo el título
        """
        title = story_data['title'].strip()
        content = story_data['content'].strip()
        author = story_data['author'].strip()
        
        # Incluir el título al principio
        text_parts = [
            title,  # Título primero
            "",
            f"Por u/{author}",
            "",
            content,
            "",
            "Historia compartida en r/HistoriasDeReddit"
        ]
        
        return "\n".join(text_parts)

    async def create_story_video(
        self,
        story_data: Dict[str, str],
        background_video: Optional[str] = None
    ) -> str:
        """
        Crea un video completo para una historia
        
        Args:
            story_data: Diccionario con los datos de la historia
            background_video: Ruta opcional a un video de fondo
        """
        temp_files = []
        clips_to_close = []
        try:
            # Generar un nombre de archivo seguro basado en el título
            safe_title = self._sanitize_filename(story_data['title'])
            safe_title = f"{safe_title[:50]}_{story_data['reddit_id']}"
            
            temp_audio = os.path.join(self.temp_dir, f"{safe_title}_audio.wav")
            temp_subs = os.path.join(self.temp_dir, f"{safe_title}_subs.srt")
            output_video = os.path.join(self.video_dir, f"{safe_title}.mp4")
            
            temp_files.extend([temp_audio, temp_subs])
            
            if not background_video:
                background_video = self._get_random_background_video()
            elif not os.path.exists(background_video):
                self.logger.warning(f"Video de fondo no encontrado: {background_video}")
                background_video = self._get_random_background_video()

            # Generar audio y timings
            text = self._prepare_text(story_data)
            audio_path, timings = await self.text_to_audio(text, temp_audio)
            
            # Encontrar cuando se menciona al autor
            author_start_time = None
            for timing in timings:
                if f"Por u/{story_data['author']}" in timing['text']:
                    author_start_time = timing['end']
                    break

            if author_start_time is None:
                self.logger.warning(f"No se encontró la mención del autor para {story_data['reddit_id']}")
                author_start_time = 4.0  # Duración por defecto
                
            # Crear clip principal
            main_audio_clip = AudioFileClip(audio_path)
            clips_to_close.append(main_audio_clip)
            
            background_clip = VideoFileClip(background_video)
            clips_to_close.append(background_clip)
            
            # Ajustar duración del video de fondo
            total_duration = main_audio_clip.duration
            if background_clip.duration < total_duration:
                background_clip = vfx.loop(background_clip, duration=total_duration)
            else:
                background_clip = background_clip.subclip(0, total_duration)

            # Ajustar tamaño del video de fondo
            bg_aspect = background_clip.size[0] / background_clip.size[1]
            target_aspect = self.width / self.height
            
            if bg_aspect > target_aspect:
                new_width = int(self.height * bg_aspect)
                background_clip = background_clip.resize(height=self.height)
                background_clip = background_clip.crop(
                    x1=(new_width-self.width)/2,
                    x2=(new_width+self.width)/2,
                    y1=0,
                    y2=self.height
                )
            else:
                new_height = int(self.width / bg_aspect)
                background_clip = background_clip.resize(width=self.width)
                background_clip = background_clip.crop(
                    x1=0,
                    x2=self.width,
                    y1=(new_height-self.height)/2,
                    y2=(new_height+self.height)/2
                )

            # Crear overlay que dura hasta la mención del autor
            intro_overlay = self.create_intro_overlay(
                title=story_data['title'],
                size=(200, 200),
                duration=author_start_time
            ).set_start(0)  # Comienza en 0
            clips_to_close.append(intro_overlay)
            
            # Crear clips de texto en grupos de 4 palabras
            text_clips = []
            current_words = []
            start_time = None
            
            for timing in timings:
                if timing['start'] < author_start_time:
                    continue  # Saltar texto antes de la mención del autor
                    
                if timing['text'].strip():
                    if not start_time:
                        start_time = timing['start']
                    
                    current_words.append(timing['text'])
                    
                    if len(current_words) >= 4 or timing['text'].strip().endswith(('.', ',', '?', '!', ':')):
                        text = ' '.join(current_words).strip()
                        end_time = timing['end'] + 0.3
                        
                        text_clip = (self.create_text_with_tiktok_style(text)
                                    .set_position('center')
                                    .set_start(start_time)
                                    .set_duration(end_time - start_time)
                                    .crossfadein(0.2)
                                    .crossfadeout(0.2))
                        
                        text_clips.append(text_clip)
                        clips_to_close.append(text_clip)
                        current_words = []
                        start_time = None
                        
            # Procesar palabras restantes
            if current_words:
                text = ' '.join(current_words).strip()
                text_clip = (TextClip(
                    txt=text.upper(),
                    font='impact',
                    fontsize=60,
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    size=(self.width - 100, None),
                    method='caption'
                )
                .set_position('center')
                .set_start(start_time)
                .set_duration(timings[-1]['end'] - start_time + 0.3)
                .crossfadein(0.2)
                .crossfadeout(0.2))
                
                text_clips.append(text_clip)
                clips_to_close.append(text_clip)
            
            # Crear video final con el orden correcto de las capas
            final_clip = CompositeVideoClip(
                [
                    background_clip,  # Fondo
                    intro_overlay,    # Overlay que desaparece con la mención del autor
                    *text_clips      # Subtítulos que comienzan después
                ],
                size=(self.width, self.height)
            ).set_audio(main_audio_clip)
            clips_to_close.append(final_clip)
            
            # Añadir fade in/out
            final_clip = final_clip.fadein(0.5).fadeout(0.5)
            
            # Renderizar video
            final_clip.write_videofile(
                output_video,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                bitrate='4M',
                threads=4,
                preset='medium'
            )
            
            return output_video
            
        except Exception as error:
            self.logger.error(f"Error creando video para historia {story_data.get('reddit_id')}: {error}")
            raise
            
        finally:
            # Limpiar archivos temporales
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        self.logger.warning(f"Error eliminando archivo temporal {temp_file}: {e}")
            
            # Cerrar clips
            for clip in clips_to_close:
                try:
                    clip.close()
                except Exception as e:
                    self.logger.warning(f"Error cerrando clip: {e}")

    def create_text_with_tiktok_style(self, text: str) -> TextClip:
        """Crea texto con estilo TikTok"""
        # Capa de sombra exterior
        shadow = TextClip(
            txt=text.upper(),
            font='impact',
            fontsize=60,
            color='black',
            stroke_color='#323232',
            stroke_width=4,
            size=(self.width - 80, None),
            method='caption'
        )
        
        # Capa de texto principal
        main_text = TextClip(
            txt=text.upper(),
            font='impact',
            fontsize=60,
            color='white',
            stroke_color='#323232',
            stroke_width=2,
            size=(self.width - 80, None),
            method='caption'
        )
        
        return CompositeVideoClip([shadow, main_text])

    def _sanitize_filename(self, filename: str) -> str:
        """
        Convierte un título en un nombre de archivo seguro
        
        Args:
            filename: Título original
            
        Returns:
            str: Nombre de archivo seguro
        """
        # Eliminar caracteres no permitidos en nombres de archivo
        invalid_chars = '<>:"/\\|?*'
        safe_name = ''.join(c for c in filename if c not in invalid_chars)
        
        # Reemplazar espacios y símbolos por guiones
        safe_name = safe_name.replace(' ', '-')
        safe_name = ''.join(c if c.isalnum() or c == '-' else '-' for c in safe_name)
        
        # Eliminar múltiples guiones seguidos
        while '--' in safe_name:
            safe_name = safe_name.replace('--', '-')
        
        # Eliminar guiones al inicio y final
        safe_name = safe_name.strip('-')
        
        # Convertir a minúsculas para consistencia
        safe_name = safe_name.lower()
        
        return safe_name

    async def process_top_stories(self) -> List[str]:
        """
        Procesa las historias con mejor score de la base de datos
        
        Returns:
            List[str]: Lista de rutas de los videos generados
        """
        generated_videos = []
        processed_count = 0
        
        try:
            with get_db_session() as session:
                # Obtener historias pendientes con mejor score
                pending_stories = (
                    session.query(RedditStories)
                    .filter(RedditStories.status == 'pending')
                    .filter(RedditStories.importance_score >= self.MIN_SCORE)
                    .order_by(desc(RedditStories.importance_score))
                    .limit(self.MAX_VIDEOS * 2)  # Obtenemos el doble para tener margen
                    .all()
                )
                
                if not pending_stories:
                    self.logger.info("No hay historias pendientes que cumplan los criterios")
                    return []

                for story in pending_stories:
                    if processed_count >= self.MAX_VIDEOS:
                        break
                    
                    try:
                        # Verificar si ya fue procesada recientemente
                        if self._check_recent_processing(session, story.reddit_id):
                            continue

                        # Actualizar estado
                        story.status = 'processing'
                        session.commit()

                        # Preparar datos
                        story_data = {
                            'reddit_id': story.reddit_id,
                            'title': story.title,
                            'content': story.content,
                            'author': story.author,
                            'url': story.url,
                            'importance_score': story.importance_score
                        }

                        # Generar video
                        video_path = await self.create_story_video(story_data)
                        
                        if video_path and os.path.exists(video_path):
                            # Registrar contenido procesado
                            processed_content = ProcessedContent(
                                story_id=story.id,
                                cleaned_content=story.content,
                                final_video_path=video_path,
                                processing_date=datetime.utcnow()
                            )
                            session.add(processed_content)
                            
                            # Actualizar estado
                            story.status = 'processed'
                            session.commit()
                            
                            # Programar publicación
                            next_slot = self._get_next_publication_slot(session)
                            youtube_pub = YoutubePublications(
                                processed_content_id=processed_content.id,
                                youtube_title=f"Historia de Reddit: {story.title[:50]}... #shorts",
                                youtube_description=self._generate_youtube_description(story),
                                scheduled_time=next_slot,
                                publication_status='scheduled'
                            )
                            session.add(youtube_pub)
                            session.commit()
                            
                            generated_videos.append(video_path)
                            processed_count += 1
                            
                            self.logger.info(
                                f"Video {processed_count}/{self.MAX_VIDEOS} generado: "
                                f"{story.reddit_id} (Score: {story.importance_score})"
                            )
                    
                    except Exception as e:
                        self.logger.error(f"Error procesando historia {story.reddit_id}: {e}")
                        story.status = 'failed'
                        session.commit()
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error en proceso de historias: {e}")
            
        finally:
            # Limpiar archivos temporales
            for temp_file in os.listdir(self.temp_dir):
                try:
                    os.remove(os.path.join(self.temp_dir, temp_file))
                except Exception as e:
                    self.logger.warning(f"Error limpiando archivo temporal {temp_file}: {e}")
            
        return generated_videos

    def _check_recent_processing(self, session: Session, reddit_id: str) -> bool:
        """Verifica si la historia fue procesada recientemente"""
        yesterday = datetime.utcnow() - timedelta(days=1)
        return session.query(RedditStories).filter(
            RedditStories.reddit_id == reddit_id,
            RedditStories.status.in_(['processed', 'published']),
            RedditStories.collected_at >= yesterday
        ).first() is not None

    def _get_next_publication_slot(self, session: Session) -> datetime:
        """Determina el próximo slot disponible para publicación"""
        config = VIDEO_CONFIG.get('publication_schedule', {
            'start_hour': 9,    # 9 AM
            'end_hour': 23,     # 11 PM
            'interval_hours': 3  # Cada 3 horas
        })
        
        last_scheduled = (
            session.query(YoutubePublications)
            .order_by(desc(YoutubePublications.scheduled_time))
            .first()
        )
        
        now = datetime.now()
        if last_scheduled:
            next_slot = last_scheduled.scheduled_time + timedelta(hours=config['interval_hours'])
        else:
            next_slot = now.replace(
                hour=config['start_hour'],
                minute=0,
                second=0,
                microsecond=0
            )
            
        while (next_slot.hour < config['start_hour'] or 
               next_slot.hour > config['end_hour'] or 
               next_slot < now):
            next_slot += timedelta(hours=config['interval_hours'])
            
            if next_slot.hour > config['end_hour']:
                next_slot = (next_slot + timedelta(days=1)).replace(
                    hour=config['start_hour'],
                    minute=0,
                    second=0,
                    microsecond=0
                )
        
        return next_slot

    def _generate_youtube_description(self, story: RedditStories) -> str:
        """Genera la descripción para YouTube"""
        return f"""
{story.title}

Historia original por u/{story.author} en r/HistoriasDeReddit
{story.url}

#shorts #historias #reddit #viral #trending
        """.strip()

    def create_intro_overlay(
        self,
        title: str,
        size: Tuple[int, int] = (160, 160),  # Tamaño reducido del logo
        duration: float = 4.0
    ) -> ImageClip:
        """
        Crea un overlay mejorado con efectos visuales y profundidad
        """
        try:
            self.logger.info(f"Creando overlay para título: {title}")
            self.logger.info(f"Dimensiones de pantalla: {self.width}x{self.height}")

            # Crear imagen base con canal alfa
            img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Configuración
            margin = 50  
            padding = 20  
            
            # Fuentes con tamaño reducido
            title_font_size = 62  
            username_font_size = 48  
            
            title_font = ImageFont.truetype(self.available_fonts['bebas'], title_font_size)
            username_font = ImageFont.truetype(self.available_fonts['bebas'], username_font_size)

            # Procesar título
            title = title.upper()
            words = title.split()
            lines = []
            current_line = []

            for word in words:
                current_line.append(word)
                test_line = ' '.join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=title_font)
                if bbox[2] - bbox[0] > self.width - (margin * 2):
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))

            # Calcular dimensiones
            text_line_height = title_font_size + padding
            text_height = (len(lines) * text_line_height) + username_font_size
            box_height = text_height + (padding * 2)
            total_height = size[1] + padding + box_height

            # Calcular posición inicial para centrado vertical ajustado
            start_y = int(self.height / 2.1) - (total_height // 2)

            # Crear efecto de glow para el logo
            logo = Image.open(self.logo_path).convert('RGBA')
            logo = logo.resize(size, Image.Resampling.LANCZOS)
            
            # Crear efecto de glow
            glow_size = size[0] + 30  
            glow = Image.new('RGBA', (glow_size, glow_size), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            
            # Capas de glow con diferentes tamaños y opacidades
            for offset in range(8, 0, -1):  
                alpha = int(255 * (1 - offset/8))
                glow_draw.ellipse(
                    [offset, offset, glow_size-offset, glow_size-offset],
                    fill=(255, 97, 18, alpha)
                )
            
            # Círculo blanco con efecto de elevación
            circle_size = size[0] + 16  
            circle = Image.new('RGBA', (circle_size, circle_size), (0, 0, 0, 0))
            circle_draw = ImageDraw.Draw(circle)
            
            # Sombras más suaves para elevación
            for i in range(4):  
                offset = i * 2
                alpha = int(80 * (1 - i/4))
                circle_draw.ellipse(
                    [offset, offset, circle_size-offset, circle_size-offset],
                    fill=(0, 0, 0, alpha)
                )
            
            # Círculo principal
            circle_draw.ellipse(
                [2, 2, circle_size-3, circle_size-3],
                fill='white',
                outline='black',
                width=2  
            )

            # Combinar capas del logo
            logo_offset = (circle_size - size[0]) // 2
            circle.paste(logo, (logo_offset, logo_offset), logo)

            # Posicionar y pegar el glow
            glow_x = (self.width - glow_size) // 2
            glow_y = start_y
            img.paste(glow, (glow_x, glow_y), glow)

            # Posicionar y pegar el círculo con el logo
            circle_x = (self.width - circle_size) // 2
            circle_y = start_y + (glow_size - circle_size) // 2
            img.paste(circle, (circle_x, circle_y), circle)

            # Calcular posición del cuadro de texto (más cerca del logo)
            box_y = circle_y + circle_size + padding - 10
    # Crear gradiente para el cuadro con glass morphism (más sutil)
            gradient = Image.new('RGBA', (self.width - margin*2, box_height), (255, 255, 255, 220))  # Reducida opacidad base
            gradient_draw = ImageDraw.Draw(gradient)

            # Aplicar gradiente vertical para glass effect con menos contraste
            for y in range(box_height):
                # Gradiente más suave
                alpha = int(200 - (20 * y/box_height))  # Va de 200 a 180 para un cambio más sutil
                gradient_draw.line(
                    [(0, y), (self.width-margin*2, y)],
                    fill=(255, 255, 255, alpha)
                )

            # Crear borde más fino
            border = Image.new('RGBA', (self.width - margin*2 + 4, box_height + 4), (0, 0, 0, 0))
            border_draw = ImageDraw.Draw(border)
            border_draw.rectangle(
                [0, 0, border.width-1, border.height-1],
                outline=(0, 0, 0, 200),  # Borde semi-transparente
                width=5  # Borde más fino
            )

            # Aplicar esquinas redondeadas
            gradient = self.round_corners(gradient, 20)
            border = self.round_corners(border, 20)

            # Aplicar blur muy sutil
            gradient = gradient.filter(ImageFilter.GaussianBlur(radius=0.5))

            # Sombras más suaves
            for i in range(3):  # Reducido a 3 capas
                offset = i * 2
                alpha = int(80 * (1 - i/3))  # Sombras más sutiles
                shadow = Image.new('RGBA', (self.width - margin*2, box_height), (0, 0, 0, alpha))
                shadow = self.round_corners(shadow, 20)
                img.paste(shadow, (margin + offset, int(box_y + offset)), shadow)

            # Pegar gradiente y borde
            img.paste(gradient, (margin, int(box_y)), gradient)
            img.paste(border, (margin-2, int(box_y)-2), border)

            # Dibujar texto con sombras más suaves
            text_y = box_y + padding
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                text_width = bbox[2] - bbox[0]
                x = (self.width - text_width) // 2

                # Sombras más sutiles para el texto
                for offset in range(3):
                    alpha = int(160 * (1 - offset/3))
                    draw.text(
                        (x + offset, text_y + offset),
                        line,
                        font=title_font,
                        fill=(0, 0, 0, alpha)
                    )

                # Texto principal
                draw.text((x, text_y), line, font=title_font, fill=(20, 20, 20, 255))
                text_y += text_line_height

            # Username con efectos similares
            username = "@redditspirit_es"
            bbox = draw.textbbox((0, 0), username, font=username_font)
            username_width = bbox[2] - bbox[0]
            username_x = (self.width - username_width) // 2

            # Sombras más sutiles para username
            for offset in range(2):
                alpha = int(160 * (1 - offset/2))
                draw.text(
                    (username_x + offset, text_y + offset),
                    username,
                    font=username_font,
                    fill=(0, 0, 0, alpha)
                )

            # Username principal
            draw.text((username_x, text_y), username, font=username_font, fill='black')

            # Guardar imagen temporal
            temp_path = os.path.join(self.temp_dir, "temp_overlay.png")
            img.save(temp_path, format='PNG', quality=95)

            # Crear clip de video
            overlay_clip = ImageClip(temp_path)
            
            # Configurar duración y efectos
            overlay_clip = (overlay_clip
                            .set_duration(duration)
                            .fadein(0.3)
                            .fadeout(0.3))

            # Posicionar en el centro ajustado verticalmente
            clip_w, clip_h = overlay_clip.size
            position = ((self.width - clip_w)//2, int(self.height/2.1) - clip_h//2)
            overlay_clip = overlay_clip.set_position(position)

            # Limpiar archivo temporal
            try:
                os.remove(temp_path)
            except Exception as e:
                self.logger.warning(f"Error eliminando archivo temporal: {e}")

            return overlay_clip

        except Exception as e:
            self.logger.error(f"Error creando overlay: {e}")
            raise
        
    def _draw_text_with_shadow(
        self,
        draw: ImageDraw,
        text: str,
        position: Tuple[int, int],
        font: ImageFont,
        shadow_color: str = "#bcc1c4",
        text_color: str = "black",
        shadow_offset: int = 3
    ):
        """
        Dibuja texto con sombra
        """
        x, y = position
        
        # Dibujar sombra
        for offset in range(shadow_offset):
            draw.text(
                (x + offset, y + offset),
                text,
                font=font,
                fill=shadow_color
            )
        
        # Dibujar texto principal
        draw.text(
            position,
            text,
            font=font,
            fill=text_color
        )
    def get_generation_stats(self) -> Dict[str, Union[int, str]]:
        """Obtiene estadísticas de generación de videos"""
        try:
            with get_db_session() as session:
                stats = {
                    'total_videos': len(os.listdir(self.video_dir)),
                    'storage_used_mb': sum(
                        os.path.getsize(os.path.join(self.video_dir, f))
                        for f in os.listdir(self.video_dir)
                    ) / (1024 * 1024),
                    'pending_stories': session.query(RedditStories)
                        .filter(RedditStories.status == 'pending')
                        .filter(RedditStories.importance_score >= self.MIN_SCORE)
                        .count(),
                    'processed_today': session.query(RedditStories)
                        .filter(RedditStories.status == 'processed')
                        .filter(func.DATE(RedditStories.collected_at) == func.DATE(func.NOW()))
                        .count(),
                    'failed_today': session.query(RedditStories)
                        .filter(RedditStories.status == 'failed')
                        .filter(func.DATE(RedditStories.collected_at) == func.DATE(func.NOW()))
                        .count()
                }
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return {}

# Solo si se ejecuta directamente
if __name__ == "__main__":
    async def main():
        try:
            generator = VideoGenerator()
            
            # Mostrar estadísticas iniciales
            print("\nEstadísticas iniciales:")
            stats = generator.get_generation_stats()
            for key, value in stats.items():
                print(f"{key}: {value}")
            
            # Procesar historias
            print("\nProcesando historias top...")
            videos = await generator.process_top_stories()
            
            # Mostrar resultados
            print(f"\nVideos generados: {len(videos)}")
            for video in videos:
                print(f"- {os.path.basename(video)}")
            
            # Estadísticas finales
            print("\nEstadísticas finales:")
            stats = generator.get_generation_stats()
            for key, value in stats.items():
                print(f"{key}: {value}")
            
        except Exception as e:
            print(f"Error en la ejecución: {e}")
            logging.exception("Error detallado:")

    asyncio.run(main())