# setup.py
import os
from setuptools import setup, find_packages
setup(
    name="news_automation",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'sqlalchemy',
        'structlog',
        'tenacity',
        'mysqlclient',
        'requests',
        'python-dotenv'
    ]
)
def setup_project():
    # Crear directorios
    directories = [
        'models',
        'tests',
        'utils',
        'utils/tts',
        'storage/audio'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        init_file = os.path.join(directory, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                pass

    # Crear pytest.ini
    pytest_content = """[pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v
testpaths = tests
"""
    with open('pytest.ini', 'w') as f:
        f.write(pytest_content)

    # Crear conftest.py
    conftest_content = """import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""
    with open('conftest.py', 'w') as f:
        f.write(conftest_content)

    # Crear archivo de test básico para models
    test_models_content = """import pytest
from models.news_model import Base, News, ProcessedContent, Publication, ErrorLog, SystemConfig

def test_create_news():
    news = News(
        title="Test News",
        content="Test Content",
        language="es",
        source="Test Source",
        importance_score=8
    )
    assert news.title == "Test News"
    assert news.language == "es"
"""
    with open('tests/test_models.py', 'w') as f:
        f.write(test_models_content)

    # Crear archivo de test para TTS
    test_tts_content = """import pytest
import os
import sys
from utils.tts.tts_service import TTSService

def test_tts_service():
    tts = TTSService()
    
    try:
        # Probar texto en español
        text_es = "Esta es una prueba de texto a voz."
        path_es = tts.generate_audio(
            text=text_es,
            language='es',
            news_id=1
        )
        assert os.path.exists(path_es)
        
        # Probar texto en inglés
        text_en = "This is a text-to-speech test."
        path_en = tts.generate_audio(
            text=text_en,
            language='en',
            news_id=2,
            accent='us'
        )
        assert os.path.exists(path_en)
        
    except Exception as e:
        pytest.fail(f"Error en TTS: {str(e)}")
"""
    with open('tests/test_tts.py', 'w') as f:
        f.write(test_tts_content)

    print("Estructura del proyecto creada correctamente")

# Configuración del paquete
setup(
    name="news_scraper",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'sqlalchemy',
        'structlog',
        'tenacity',
        'requests',
        'pytest',
        'mysqlclient'
    ]
)

if __name__ == "__main__":
    setup_project()