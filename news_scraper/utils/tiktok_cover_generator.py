import os
from pathlib import Path
import logging
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict

# Configurar logging
logger = logging.getLogger(__name__)

class TikTokCoverGenerator:
    """Generador de covers para videos de TikTok"""
    
    def __init__(self):
        """Inicializa el generador de covers"""
        self.width = 1080  # Ancho estándar para TikTok
        self.height = 1920  # Alto estándar para TikTok
        
        # Configurar fuentes
        self.impact_path = "C:\\Windows\\Fonts\\Impact.ttf"
        self.title_font_size = 96  # 96px para título
        self.watermark_font_size = 70  # 60px para watermark
        
        # Colores exactos de la muestra
        self.background_color = "#ff6712"  # Naranja exacto
        self.text_color = "black"
        self.stroke_color = "#bcc1c4"  # Gris exacto del contorno
        self.stroke_width = 5
        
        # Ruta base para los covers
        self.output_base_path = (
            "C:\\Users\\USUARIO1\\Documents\\Youtube Automation\\"
            "news_scraper\\storage\\media\\pictures"
        )
        os.makedirs(self.output_base_path, exist_ok=True)

    def create_cover(
        self,
        title: str,
        output_name: str,
        watermark: str = "@redditspirit_es"
    ) -> str:
        """
        Crea un cover para TikTok
        
        Args:
            title: Título para el cover
            output_name: Nombre del archivo de salida
            watermark: Marca de agua (usuario)
            
        Returns:
            str: Ruta del cover generado
        """
        try:
            # Crear imagen base
            image = Image.new('RGB', (self.width, self.height), self.background_color)
            draw = ImageDraw.Draw(image)

            # Cargar fuentes Impact
            try:
                title_font = ImageFont.truetype(self.impact_path, self.title_font_size)
                watermark_font = ImageFont.truetype(self.impact_path, self.watermark_font_size)
            except OSError:
                logger.error("Fuente Impact no encontrada")
                raise

            # Preparar texto del título
            title = title.upper()  # Convertir a mayúsculas
            words = title.split()
            lines = []
            current_line = []
            
            for word in words:
                current_line.append(word)
                test_line = ' '.join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=title_font)
                if bbox[2] - bbox[0] > self.width - 140:  
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))

            # Dibujar título centrado verticalmente
            total_height = len(lines) * (self.title_font_size + 20)  
            y = (self.height - total_height) // 2
            
            for line in lines:
                # Obtener dimensiones del texto
                bbox = draw.textbbox((0, 0), line, font=title_font)
                text_width = bbox[2] - bbox[0]
                x = (self.width - text_width) // 2

                # Dibujar stroke (contorno gris)
                for offset_x in range(-self.stroke_width, self.stroke_width + 1):
                    for offset_y in range(-self.stroke_width, self.stroke_width + 1):
                        if offset_x != 0 or offset_y != 0:
                            draw.text(
                                (x + offset_x, y + offset_y),
                                line,
                                font=title_font,
                                fill=self.stroke_color
                            )

                # Dibujar texto principal negro
                draw.text(
                    (x, y),
                    line,
                    font=title_font,
                    fill=self.text_color
                )
                
                y += self.title_font_size + 20

            # Dibujar watermark
            bbox = draw.textbbox((0, 0), watermark, font=watermark_font)
            watermark_width = bbox[2] - bbox[0]
            watermark_x = (self.width - watermark_width) // 2
            watermark_y = self.height - 120

            # Contorno gris para watermark
            for offset_x in range(-3, 4):
                for offset_y in range(-3, 4):
                    if offset_x != 0 or offset_y != 0:
                        draw.text(
                            (watermark_x + offset_x, watermark_y + offset_y),
                            watermark,
                            font=watermark_font,
                            fill=self.stroke_color
                        )

            # Texto del watermark en negro
            draw.text(
                (watermark_x, watermark_y),
                watermark,
                font=watermark_font,
                fill=self.text_color
            )

            # Guardar imagen con alta calidad
            output_path = os.path.join(self.output_base_path, f"{output_name}.jpg")
            image.save(output_path, quality=100)  # Calidad máxima para mejor definición
            logger.info(f"Cover generado exitosamente: {output_path}")
            
            return output_path

        except Exception as e:
            logger.error(f"Error generando cover: {e}")
            raise

    def generate_covers_batch(
        self,
        stories: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Genera covers para un lote de historias
        
        Args:
            stories: Diccionario de id:título
            
        Returns:
            Dict[str, str]: Mapeo de id:ruta_cover
        """
        covers = {}
        
        for story_id, title in stories.items():
            try:
                cover_path = self.create_cover(
                    title=title,
                    output_name=f"cover_{story_id}"
                )
                covers[story_id] = cover_path
            except Exception as e:
                logger.error(f"Error generando cover para historia {story_id}: {e}")
                continue
                
        return covers

if __name__ == "__main__":
    # Prueba básica
    generator = TikTokCoverGenerator()
    test_title = "LA VISITA INESPERADA QUE TERMINÓ CON UNA SORPRESA VECINAL"
    generator.create_cover(test_title, "test_cover")