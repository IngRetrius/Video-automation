"""
Test de obtención de historias de Reddit con contenido completo
"""
import praw
from dotenv import load_dotenv
import os
from datetime import datetime
import time
import json

# Cargar variables de entorno
load_dotenv()

def format_timestamp(timestamp):
    """Convierte un timestamp de Reddit a fecha legible"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def clean_content(content):
    """Limpia y formatea el contenido de la historia"""
    if not content:
        return ""
    # Eliminar saltos de línea múltiples pero mantener párrafos
    paragraphs = [line.strip() for line in content.split('\n') if line.strip()]
    return '\n\n'.join(paragraphs)

def get_story_details(post):
    """Obtiene los detalles completos de una historia"""
    try:
        story = {
            'id': post.id,
            'title': post.title,
            'author': str(post.author),
            'score': post.score,
            'upvote_ratio': post.upvote_ratio,
            'num_comments': post.num_comments,
            'created_utc': format_timestamp(post.created_utc),
            'url': post.url,
            'content': clean_content(post.selftext),
            'is_nsfw': post.over_18,
            'awards': len(post.all_awardings) if hasattr(post, 'all_awardings') else 0,
        }
        
        # Guardar la historia en un archivo JSON
        filename = f"historia_{post.id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(story, f, ensure_ascii=False, indent=4)
            print(f"\nHistoria guardada en: {filename}")
            
        return story
    except Exception as e:
        print(f"Error obteniendo detalles de la historia: {e}")
        return None

def main():
    print("=== Test de HistoriasDeReddit con Contenido Completo ===")
    
    # Crear instancia de Reddit
    reddit = praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID').strip(),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET').strip(),
        user_agent=os.getenv('REDDIT_USER_AGENT').strip()
    )

    print(f"\nConectado en modo: {'solo lectura' if reddit.read_only else 'lectura/escritura'}")
    
    try:
        # Obtener el subreddit
        subreddit = reddit.subreddit('HistoriasDeReddit')
        print(f"\nAccediendo a r/{subreddit.display_name}")
        print(f"Suscriptores: {subreddit.subscribers:,}")
        
        # Obtener las últimas historias
        print("\nObteniendo últimas 3 historias...")
        
        for i, post in enumerate(subreddit.hot(limit=3), 1):
            # Añadir pequeña pausa para evitar rate limiting
            time.sleep(1)
            
            print(f"\nProcesando Historia #{i}: {post.title}")
            story = get_story_details(post)
            
            if not story:
                continue
                
            print(f"- Autor: u/{story['author']}")
            print(f"- Score: {story['score']} (ratio: {story['upvote_ratio']})")
            print(f"- Comentarios: {story['num_comments']}")
            print(f"- Longitud del contenido: {len(story['content'])} caracteres")
            print(f"- URL: {story['url']}")
        
        return True
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✓ Test completado exitosamente")
            print("\nLas historias completas han sido guardadas en archivos JSON individuales.")
            print("Puedes abrir estos archivos para ver el contenido completo de cada historia.")
        else:
            print("\n✗ El test falló")
    except KeyboardInterrupt:
        print("\nTest interrumpido por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {e}")