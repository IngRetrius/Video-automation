"""
Script para actualizar el esquema de la base de datos
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from sqlalchemy import text
from news_scraper.config.database import engine

def update_schema():
    """Actualiza el esquema de la base de datos añadiendo las columnas necesarias"""
    
    # Queries para añadir las columnas extra_data
    alter_queries = [
        """
        ALTER TABLE reddit_stories 
        ADD COLUMN IF NOT EXISTS extra_data JSON NULL
        """,
        """
        ALTER TABLE processed_content 
        ADD COLUMN IF NOT EXISTS extra_data JSON NULL
        """,
        """
        ALTER TABLE youtube_publications 
        ADD COLUMN IF NOT EXISTS extra_data JSON NULL
        """,
        """
        ALTER TABLE error_logs 
        ADD COLUMN IF NOT EXISTS extra_data JSON NULL
        """,
        """
        ALTER TABLE system_config 
        ADD COLUMN IF NOT EXISTS extra_data JSON NULL
        """
    ]
    
    try:
        connection = engine.connect()
        
        for query in alter_queries:
            try:
                connection.execute(text(query))
                print(f"✓ Ejecutada query: {query.strip()}")
            except Exception as e:
                print(f"✗ Error en query: {str(e)}")
                
        connection.commit()
        print("\n✓ Esquema actualizado correctamente")
        
    except Exception as e:
        print(f"\n✗ Error actualizando esquema: {str(e)}")
        
    finally:
        connection.close()

if __name__ == "__main__":
    update_schema()