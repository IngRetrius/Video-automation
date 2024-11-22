# Video Automation System

Sistema automatizado para la generación de videos cortos a partir de historias de Reddit, con publicación automática en TikTok y YouTube Shorts.

## 🚀 Características

- Recopilación automática de historias desde Reddit
- Conversión de texto a voz usando Edge TTS
- Generación automática de videos con efectos visuales
- Sistema de puntuación para selección de contenido
- Creación automática de miniaturas para TikTok
- Publicación automatizada en redes sociales
- Base de datos MySQL para gestión de contenido
- Sistema robusto de logging y monitoreo

## 📋 Requisitos del Sistema

- Python 3.8+
- MySQL Server
- FFmpeg
- ImageMagick
- Edge TTS
- Redis (opcional)

## ⚙️ Instalación

1. Clonar el repositorio
```bash
git clone https://github.com/IngRetrius/Video-automation.git
cd Video-automation
```

2. Crear y activar entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instalar dependencias
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

5. Crear estructura de directorios necesaria
```bash
# Crear directorios necesarios
mkdir -p storage/{backups,reports,temp}
mkdir -p storage/media/{audio,background_videos,background_videos1,backgrounds,pictures,video}
mkdir -p logs

# Crear archivos __init__.py necesarios
touch news_scraper/__init__.py
touch news_scraper/config/__init__.py
touch news_scraper/models/__init__.py
touch news_scraper/scrapers/__init__.py
touch news_scraper/utils/__init__.py
touch tests/__init__.py
```

6. Inicializar la base de datos
```bash
mysql -u root -p < Automation_database.sql
```

## 📁 Estructura del Proyecto

```
Video-automation/                # Directorio raíz
├── .gitignore                  # Configuración de git
├── .env                        # Variables de entorno (no incluido en git)
├── README.md                   # Este archivo
├── requirements.txt            # Dependencias del proyecto
├── main.py                     # Script principal
│
├── news_scraper/              # Módulo principal
│   ├── __init__.py
│   ├── config/               # Configuraciones
│   │   ├── __init__.py
│   │   ├── database.py      # Configuración de base de datos
│   │   └── settings.py      # Configuraciones generales
│   ├── models/              # Modelos de datos
│   │   ├── __init__.py
│   │   ├── reddit_model.py  # Modelo para historias de Reddit
│   │   └── tiktok_model.py  # Modelo para publicaciones TikTok
│   ├── scrapers/            # Scrapers
│   │   ├── __init__.py
│   │   ├── base_scraper.py
│   │   └── reddit_scraper.py
│   └── utils/               # Utilidades
│       ├── __init__.py
│       ├── video_generator.py
│       └── tiktok_cover_generator.py
│
├── storage/                 # Almacenamiento de archivos
│   ├── backups/            # Respaldos
│   ├── media/              # Archivos multimedia
│   │   ├── audio/          # Archivos de audio TTS
│   │   ├── background_videos/  # Videos de fondo
│   │   ├── background_videos1/ # Videos alternativos
│   │   ├── backgrounds/    # Imágenes de fondo
│   │   ├── pictures/       # Miniaturas generadas
│   │   └── video/         # Videos finales
│   ├── reports/           # Informes generados
│   └── temp/             # Archivos temporales
│
└── logs/                  # Archivos de registro
```

## ⚡ Uso

### Ejecución Principal
```bash
python main.py
```

### Generación Manual de Videos
```bash
python utils/manual_generator.py
```

## 🔧 Configuración

El sistema usa varios archivos de configuración:

1. `.env`: Variables de entorno y credenciales
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=reddit_stories_automation

REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=StoriesBot/1.0
```

2. `config/settings.py`: Configuración general del sistema
- Rutas de almacenamiento
- Configuración de video
- Configuración de TTS
- Configuración de publicación

## 📊 Base de Datos

El sistema utiliza MySQL con las siguientes tablas principales:

- `reddit_stories`: Historias recopiladas
- `processed_content`: Contenido procesado
- `youtube_publications`: Publicaciones en YouTube
- `tiktok_publications`: Publicaciones en TikTok
- `error_logs`: Registro de errores
- `system_config`: Configuración del sistema

## 🛠️ Desarrollo

### Configuración del Entorno de Desarrollo

1. Instalar dependencias de desarrollo
```bash
pip install -r requirements-dev.txt
```

2. Configurar pre-commit hooks
```bash
pre-commit install
```

### Ejecutar Tests
```bash
pytest
```

### Generar Reporte de Cobertura
```bash
pytest --cov=news_scraper tests/
```

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🤝 Contribuir

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit los cambios (`git commit -m 'Add: nueva característica'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## ✨ Créditos

Desarrollado por IngRetrius
