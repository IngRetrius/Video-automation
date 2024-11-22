"""
manual_generator.py: Script para generar videos y covers manualmente
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import uuid
import logging
from typing import Dict, Optional

# Agregar el directorio raíz al path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

# Importaciones locales
from news_scraper.utils.video_generator import VideoGenerator
from news_scraper.utils.tiktok_cover_generator import TikTokCoverGenerator
from news_scraper.config.database import get_db_session
from news_scraper.models.reddit_model import RedditStories, ProcessedContent

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ManualContentGenerator:
    """Generador manual de contenido"""
    
    def __init__(self):
        self.video_generator = VideoGenerator()
        self.cover_generator = TikTokCoverGenerator()
        
        # Límites y configuraciones
        self.MAX_TITLE_LENGTH = 300
        self.MIN_CONTENT_LENGTH = 100
        self.MAX_CONTENT_LENGTH = 10000
        
    def _generate_reddit_id(self) -> str:
        """Genera un ID único similar a los de Reddit"""
        return str(uuid.uuid4())[:6]
    
    def _clean_filename(self, text: str, max_length: int = 50) -> str:
        """Genera un nombre de archivo limpio"""
        clean = text.lower()
        clean = ''.join(c if c.isalnum() or c.isspace() else '-' for c in clean)
        clean = '-'.join(filter(None, clean.split()))
        return clean[:max_length]

    def validate_input(self, title: str, content: str, author: str) -> tuple[bool, str]:
        """
        Valida los datos de entrada
        
        Returns:
            tuple[bool, str]: (es_válido, mensaje_error)
        """
        if not title or len(title.strip()) < 5:
            return False, "El título debe tener al menos 5 caracteres"
            
        if len(title) > self.MAX_TITLE_LENGTH:
            return False, f"El título no debe exceder {self.MAX_TITLE_LENGTH} caracteres"
            
        if not content or len(content.strip()) < self.MIN_CONTENT_LENGTH:
            return False, f"El contenido debe tener al menos {self.MIN_CONTENT_LENGTH} caracteres"
            
        if len(content) > self.MAX_CONTENT_LENGTH:
            return False, f"El contenido no debe exceder {self.MAX_CONTENT_LENGTH} caracteres"
            
        if not author or len(author.strip()) < 3:
            return False, "El autor debe tener al menos 3 caracteres"
            
        return True, ""

    async def generate_content(
        self,
        title: str,
        content: str,
        author: str,
        save_to_db: bool = True
    ) -> Optional[Dict]:
        """
        Genera video y cover para una historia manual
        
        Args:
            title: Título de la historia
            content: Contenido de la historia
            author: Nombre del autor
            save_to_db: Si se debe guardar en la base de datos
            
        Returns:
            Optional[Dict]: Información del contenido generado o None si hay error
        """
        # Validar entrada
        is_valid, error_message = self.validate_input(title, content, author)
        if not is_valid:
            logger.error(f"Datos inválidos: {error_message}")
            raise ValueError(error_message)
        
        try:
            # Generar ID único
            reddit_id = self._generate_reddit_id()
            clean_title = self._clean_filename(title)
            base_filename = f"{clean_title}_{reddit_id}"
            
            print("\nGenerando contenido:")
            print("-" * 50)
            print(f"ID: {reddit_id}")
            print(f"Título: {title}")
            print(f"Autor: {author}")
            print(f"Nombre base: {base_filename}")
            
            # Preparar datos de la historia
            story_data = {
                'reddit_id': reddit_id,
                'title': title.strip(),
                'content': content.strip(),
                'author': author.strip(),
                'score': 100,
                'upvote_ratio': 1.0,
                'num_comments': 0,
                'url': f"https://reddit.com/r/HistoriasDeReddit/{reddit_id}",
                'created_utc': datetime.utcnow(),
                'collected_at': datetime.utcnow(),
                'importance_score': 100,
                'language': 'es',
                'status': 'pending'
            }
            
            # Proceso de generación con feedback
            story_id = None
            
            if save_to_db:
                print("\nGuardando en base de datos...")
                session = get_db_session()
                try:
                    story = RedditStories(**story_data)
                    session.add(story)
                    session.commit()
                    story_id = story.id
                    print(f"✓ Historia guardada con ID: {story_id}")
                finally:
                    session.close()
            
            print("\nGenerando video...")
            video_path = await self.video_generator.create_story_video(story_data)
            print(f"✓ Video generado: {os.path.basename(video_path)}")
            
            print("\nGenerando cover...")
            cover_path = self.cover_generator.create_cover(
                title=title,
                output_name=base_filename
            )
            print(f"✓ Cover generado: {os.path.basename(cover_path)}")
            
            if save_to_db and story_id:
                print("\nActualizando base de datos...")
                session = get_db_session()
                try:
                    processed_content = ProcessedContent(
                        story_id=story_id,
                        final_video_path=video_path,
                        cover_path=cover_path,
                        processing_date=datetime.utcnow()
                    )
                    session.add(processed_content)
                    session.commit()
                    print("✓ Base de datos actualizada")
                finally:
                    session.close()
            
            print("\n✓ Proceso completado exitosamente!")
            return {
                'reddit_id': reddit_id,
                'video_path': video_path,
                'cover_path': cover_path,
                'story_id': story_id
            }
            
        except Exception as e:
            logger.error(f"Error generando contenido: {e}")
            raise

    def print_story_preview(self, title: str, content: str, author: str):
        """Muestra una vista previa de la historia con estadísticas"""
        print("\nVista previa de la historia:")
        print("-" * 50)
        print(f"Título: {title}")
        print(f"Longitud del título: {len(title)} caracteres")
        print(f"Autor: u/{author}")
        print(f"\nContenido ({len(content)} caracteres):")
        print("-" * 30)
        print(content)
        print("-" * 50)
    async def generate_from_id(self, story_id: int) -> Optional[Dict]:
            """
            Genera video y cover para una historia existente por su ID
            
            Args:
                story_id: ID de la historia en la base de datos
                
            Returns:
                Optional[Dict]: Información del contenido generado o None si hay error
            """
            try:
                session = get_db_session()
                try:
                    # Buscar la historia
                    story = session.query(RedditStories).filter_by(id=story_id).first()
                    
                    if not story:
                        raise ValueError(f"No se encontró historia con ID: {story_id}")
                    
                    # Verificar si ya fue procesada
                    existing_content = session.query(ProcessedContent)\
                        .filter_by(story_id=story_id)\
                        .first()
                        
                    if existing_content and existing_content.final_video_path:
                        print(f"\n⚠️ Esta historia ya tiene contenido generado:")
                        print(f"Video: {existing_content.final_video_path}")
                        print(f"Cover: {existing_content.cover_path}")
                        
                        if input("\n¿Desea regenerar el contenido? (s/n): ").lower() != 's':
                            return None
                    
                    # Preparar datos
                    story_data = {
                        'reddit_id': story.reddit_id,
                        'title': story.title,
                        'content': story.content,
                        'author': story.author,
                        'score': story.score,
                        'upvote_ratio': story.upvote_ratio,
                        'num_comments': story.num_comments,
                        'url': story.url,
                        'created_utc': story.created_utc,
                        'collected_at': story.collected_at,
                        'importance_score': story.importance_score,
                        'language': story.language,
                        'status': story.status
                    }
                    
                    # Generar video
                    print("\nGenerando video...")
                    video_path = await self.video_generator.create_story_video(story_data)
                    print(f"✓ Video generado: {os.path.basename(video_path)}")
                    
                    # Generar cover
                    print("\nGenerando cover...")
                    base_filename = f"{self._clean_filename(story.title)}_{story.reddit_id}"
                    cover_path = self.cover_generator.create_cover(
                        title=story.title,
                        output_name=base_filename
                    )
                    print(f"✓ Cover generado: {os.path.basename(cover_path)}")
                    
                    # Actualizar o crear ProcessedContent
                    if existing_content:
                        existing_content.final_video_path = video_path
                        existing_content.cover_path = cover_path
                        existing_content.processing_date = datetime.utcnow()
                    else:
                        processed_content = ProcessedContent(
                            story_id=story_id,
                            final_video_path=video_path,
                            cover_path=cover_path,
                            processing_date=datetime.utcnow()
                        )
                        session.add(processed_content)
                    
                    session.commit()
                    print("✓ Base de datos actualizada")
                    
                    return {
                        'story_id': story_id,
                        'reddit_id': story.reddit_id,
                        'video_path': video_path,
                        'cover_path': cover_path
                    }
                    
                finally:
                    session.close()
                    
            except Exception as e:
                logger.error(f"Error generando contenido para ID {story_id}: {e}")
                raise

async def main():
    """Función principal para pruebas manuales"""
    generator = ManualContentGenerator()
    
    print("\nGenerador Manual de Contenido")
    print("-" * 50)
    print("\nOpciones:")
    print("1. Generar nuevo contenido")
    print("2. Generar a partir de ID existente")
    
    option = input("\nSeleccione una opción (1/2): ").strip()
    
    try:
        if option == "1":
            # Solicitar datos al usuario
            title = input("\nIngrese el título de la historia: ").strip()
            author = input("Ingrese el nombre del autor: ").strip()
            
            print("\nIngrese el contenido de la historia (presione Enter dos veces para finalizar):")
            content_lines = []
            while True:
                line = input()
                if line:
                    content_lines.append(line)
                elif content_lines:
                    break
            content = "\n".join(content_lines)
            
            # Mostrar vista previa
            generator.print_story_preview(title, content, author)
            
            # Confirmar generación
            if input("\n¿Los datos son correctos? (s/n): ").lower() != 's':
                print("Operación cancelada")
                return
            
            save_db = input("¿Guardar en la base de datos? (s/n): ").lower() == 's'
            
            result = await generator.generate_content(
                title=title,
                content=content,
                author=author,
                save_to_db=save_db
            )
            
            print("\nResultado final:")
            print("-" * 50)
            print(f"ID generado: {result['reddit_id']}")
            print(f"Video: {os.path.basename(result['video_path'])}")
            print(f"Cover: {os.path.basename(result['cover_path'])}")
            
        elif option == "2":
            # Generar a partir de ID
            try:
                story_id = int(input("\nIngrese el ID de la historia: "))
                
                print("\nBuscando historia...")
                result = await generator.generate_from_id(story_id)
                
                if result:
                    print("\nResultado final:")
                    print("-" * 50)
                    print(f"ID en base de datos: {result['story_id']}")
                    print(f"ID de Reddit: {result['reddit_id']}")
                    print(f"Video: {os.path.basename(result['video_path'])}")
                    print(f"Cover: {os.path.basename(result['cover_path'])}")
                
            except ValueError:
                print("\n✗ Error: El ID debe ser un número válido")
                
        else:
            print("\n✗ Opción no válida")
            
    except Exception as e:
        print(f"\n✗ Error durante la generación: {e}")
        logger.exception("Error detallado:")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
        logger.exception("Error detallado del sistema:")