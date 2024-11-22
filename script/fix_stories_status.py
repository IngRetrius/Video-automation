"""
Script para corregir el estado de las historias y sus scores
"""

import sys
from pathlib import Path
from datetime import datetime

# Añadir el directorio raíz al path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from news_scraper.config.database import get_db_session
from news_scraper.models.reddit_model import RedditStories

def fix_stories_status():
    """Corrige el estado de las historias y recalcula scores"""
    try:
        with get_db_session() as session:
            # Resetear historias a pending si no tienen video procesado
            stories = session.query(RedditStories).all()
            
            updated = 0
            for story in stories:
                # Recalcular score
                story.importance_score = story.calculate_importance_score()
                
                # Si no tiene contenido procesado, marcar como pending
                if not story.processed_content:
                    if story.status not in ['failed', 'pending']:
                        story.status = 'pending'
                        updated += 1
                
                # Actualizar historias con score alto
                if story.importance_score >= 25 and story.status == 'processed':
                    story.status = 'pending'
                    updated += 1

            session.commit()
            
            # Mostrar estadísticas actualizadas
            stats = {
                'pending': session.query(RedditStories)
                    .filter(RedditStories.status == 'pending')
                    .count(),
                'processing': session.query(RedditStories)
                    .filter(RedditStories.status == 'processing')
                    .count(),
                'processed': session.query(RedditStories)
                    .filter(RedditStories.status == 'processed')
                    .count(),
                'failed': session.query(RedditStories)
                    .filter(RedditStories.status == 'failed')
                    .count(),
                'high_score': session.query(RedditStories)
                    .filter(RedditStories.importance_score >= 25)
                    .count()
            }
            
            print(f"\n✓ Actualizadas {updated} historias")
            print("\nEstadísticas actuales:")
            print(f"- Pendientes: {stats['pending']}")
            print(f"- En proceso: {stats['processing']}")
            print(f"- Procesadas: {stats['processed']}")
            print(f"- Fallidas: {stats['failed']}")
            print(f"- Score alto (>=25): {stats['high_score']}")
            
            # Mostrar top 5 historias pendientes
            print("\nTop 5 historias pendientes:")
            top_stories = (session.query(RedditStories)
                         .filter(RedditStories.status == 'pending')
                         .order_by(RedditStories.importance_score.desc())
                         .limit(5)
                         .all())
            
            for story in top_stories:
                print(f"\n- {story.title}")
                print(f"  Score: {story.importance_score}")
                print(f"  Status: {story.status}")
                print(f"  Upvotes: {story.score}")
                print(f"  Comentarios: {story.num_comments}")
            
    except Exception as e:
        print(f"✗ Error actualizando historias: {e}")

if __name__ == "__main__":
    print("Iniciando actualización de historias...")
    fix_stories_status()