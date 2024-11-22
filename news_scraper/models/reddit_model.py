"""
models/reddit_model.py: SQLAlchemy models for Reddit Stories Automation System

This module contains the complete model definitions for the Reddit Stories 
automation system, including all tables and their relationships.

Models:
    - RedditStories: Main stories from Reddit
    - ProcessedContent: Processed content for TTS and video
    - YoutubePublications: YouTube upload information
    - ErrorLogs: System error logging
    - SystemConfig: System configuration
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey, Boolean, Float, TIMESTAMP, JSON, or_
from datetime import datetime, timedelta
import json

# Configurar el path para importaciones
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey, Boolean, Float, TIMESTAMP, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.ext.declarative import declared_attr

from news_scraper.config.database import Base
from news_scraper.models.tiktok_model import TikTokPublications

class RedditStories(Base):
    """Model for storing Reddit stories scraped from r/HistoriasDeReddit."""
    
    __tablename__ = 'reddit_stories'
    __table_args__ = {'extend_existing': True}

    id = Column(BIGINT(20), primary_key=True, autoincrement=True)
    reddit_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(128), index=True)
    score = Column(Integer, default=0)
    upvote_ratio = Column(Float)
    num_comments = Column(Integer, default=0)
    post_flair = Column(String(50))
    is_nsfw = Column(TINYINT(1), default=False)
    awards_received = Column(Integer, default=0)
    url = Column(String(512), nullable=False)
    created_utc = Column(TIMESTAMP, index=True)
    collected_at = Column(TIMESTAMP, default=datetime.utcnow, index=True)
    language = Column(Enum('es', 'en'), default='es', nullable=False)
    status = Column(
        Enum('pending', 'processing', 'processed', 'failed', 'published'),
        default='pending',
        index=True
    )
    importance_score = Column(Integer, default=0, index=True)
    extra_data = Column(JSON)

    # Relationships
    processed_content = relationship(
        "ProcessedContent",
        back_populates="story",
        uselist=False,
        cascade="all, delete-orphan",
        lazy='joined'
    )

    def __repr__(self) -> str:
        return (
            f"<RedditStory(id={self.id}, "
            f"title='{self.title[:30]}...', "
            f"status='{self.status}', "
            f"score={self.importance_score})>"
        )

    def calculate_importance_score(self) -> int:
        """Calculate importance score based on various metrics."""
        base_score = 0
        
        # Score based on upvotes (max 40 points)
        if self.score > 150:
            base_score += 40
        elif self.score > 100:
            base_score += 30
        elif self.score > 50:
            base_score += 20
        elif self.score > 25:
            base_score += 10

        # Comments contribution (max 20 points)
        if self.num_comments > 50:
            base_score += 20
        elif self.num_comments > 30:
            base_score += 15
        elif self.num_comments > 10:
            base_score += 10
        
        # Upvote ratio contribution (max 20 points)
        if self.upvote_ratio:
            ratio_score = int(self.upvote_ratio * 20)
            base_score += ratio_score

        # Awards contribution (max 20 points)
        if self.awards_received > 3:
            base_score += 20
        elif self.awards_received > 2:
            base_score += 15
        elif self.awards_received > 0:
            base_score += 10

        return min(base_score, 100)

    def update_status(self, new_status: str) -> None:
        """Update the processing status of the story."""
        valid_statuses = ['pending', 'processing', 'processed', 'failed', 'published']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        self.status = new_status
        
    @property
    def is_ready_for_processing(self) -> bool:
        """Check if story is ready for video processing."""
        return (
            self.status == 'pending' and
            self.importance_score >= 60 and
            not self.is_nsfw and
            len(self.content) >= 200
        )
        
    @property
    def is_processable(self) -> bool:
        """Check if story can be processed."""
        return (
            self.status not in ['processed', 'failed'] and
            not self.is_nsfw and
            self.content is not None and
            self.title is not None
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert story to dictionary."""
        return {
            'reddit_id': self.reddit_id,
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'score': self.score,
            'importance_score': self.importance_score,
            'status': self.status,
            'url': self.url,
            'extra_data': self.extra_data
        }

class ProcessedContent(Base):
    """Model for storing processed content including TTS and video files."""
    
    __tablename__ = 'processed_content'
    __table_args__ = {'extend_existing': True}

    id = Column(BIGINT(20), primary_key=True, autoincrement=True)
    story_id = Column(BIGINT(20), ForeignKey('reddit_stories.id', ondelete='CASCADE'), nullable=False, index=True)
    cleaned_content = Column(Text)
    tts_script = Column(Text)
    audio_path = Column(String(255))
    background_video_path = Column(String(255))
    final_video_path = Column(String(255))
    cover_path = Column(String(255))
    duration_seconds = Column(Integer)
    processing_date = Column(TIMESTAMP, default=datetime.utcnow, index=True)
    status = Column(
        Enum('pending', 'processing', 'processed', 'published', 'failed'),
        default='pending',
        index=True
    )
    extra_data = Column(JSON)

    # Relationships
    story = relationship("RedditStories", back_populates="processed_content", lazy='joined')
    youtube_publication = relationship(
        "YoutubePublications",
        back_populates="processed_content",
        uselist=False,
        cascade="all, delete-orphan",
        lazy='joined'
    )
    tiktok_publication = relationship(
        "TikTokPublications",
        back_populates="processed_content",
        uselist=False,
        cascade="all, delete-orphan",
        lazy='joined'
    )

    def __repr__(self) -> str:
        return f"<ProcessedContent(id={self.id}, story_id={self.story_id}, status='{self.status}')>"

    @property
    def is_complete(self) -> bool:
        """Check if all required files exist and are valid."""
        return all([
            self.audio_path and os.path.exists(self.audio_path),
            self.final_video_path and os.path.exists(self.final_video_path),
            self.cover_path and os.path.exists(self.cover_path),
            self.duration_seconds and self.duration_seconds > 0
        ])

    def is_ready_for_publication(self) -> bool:
        """Check if content is ready for social media publication."""
        return all([
            self.status == 'processed',
            self.cleaned_content,
            self.tts_script,
            self.is_complete,
            not self.youtube_publication,
            not self.tiktok_publication
        ])

    def update_status(self, new_status: str) -> None:
        """Update processing status."""
        valid_statuses = ['pending', 'processing', 'processed', 'published', 'failed']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        self.status = new_status

    def verify_files(self) -> List[str]:
        """Verify all required files exist and return missing ones."""
        missing_files = []
        
        for path_attr in ['audio_path', 'final_video_path', 'cover_path']:
            file_path = getattr(self, path_attr)
            if not file_path or not os.path.exists(file_path):
                missing_files.append(path_attr)
                
        return missing_files

    def to_dict(self) -> Dict[str, Any]:
        """Convert processed content to dictionary."""
        return {
            'story_id': self.story_id,
            'status': self.status,
            'duration': self.duration_seconds,
            'audio_path': self.audio_path,
            'video_path': self.final_video_path,
            'cover_path': self.cover_path,
            'processing_date': self.processing_date.isoformat() if self.processing_date else None,
            'is_complete': self.is_complete,
            'missing_files': self.verify_files(),
            'extra_data': self.extra_data,
            'youtube_published': bool(self.youtube_publication and self.youtube_publication.youtube_video_id),
            'tiktok_published': bool(self.tiktok_publication and self.tiktok_publication.tiktok_video_id)
        }

class YoutubePublications(Base):
    """Model for managing YouTube publications."""
    
    __tablename__ = 'youtube_publications'
    __table_args__ = {'extend_existing': True}

    id = Column(BIGINT(20), primary_key=True, autoincrement=True)
    processed_content_id = Column(BIGINT(20), ForeignKey('processed_content.id', ondelete='CASCADE'), nullable=False, index=True)
    youtube_video_id = Column(String(50), unique=True)
    youtube_url = Column(String(255))
    youtube_title = Column(String(255))
    youtube_description = Column(Text)
    youtube_tags = Column(Text)
    scheduled_time = Column(DateTime, nullable=False, index=True)
    publication_status = Column(Enum('scheduled', 'published', 'failed'), default='scheduled', index=True)
    published_at = Column(TIMESTAMP)
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    extra_data = Column(JSON)

    # Relationships
    processed_content = relationship("ProcessedContent", back_populates="youtube_publication", lazy='joined')

    def __repr__(self) -> str:
        return f"<YoutubePublication(id={self.id}, status='{self.publication_status}', video_id='{self.youtube_video_id}')>"

    def update_metrics(self, views: int, likes: int) -> None:
        """Update video performance metrics."""
        self.views_count = views
        self.likes_count = likes

    @property
    def is_published(self) -> bool:
        """Check if video is published."""
        return self.publication_status == 'published' and bool(self.youtube_video_id)

    @property
    def is_scheduled(self) -> bool:
        """Check if video is scheduled."""
        return (
            self.publication_status == 'scheduled' and
            self.scheduled_time and
            self.scheduled_time > datetime.now()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert publication to dictionary."""
        return {
            'video_id': self.youtube_video_id,
            'url': self.youtube_url,
            'title': self.youtube_title,
            'status': self.publication_status,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'views': self.views_count,
            'likes': self.likes_count,
            'extra_data': self.extra_data
        }

class ErrorLogs(Base):
    """Model for system error logging."""
    
    __tablename__ = 'error_logs'
    __table_args__ = {'extend_existing': True}

    id = Column(BIGINT(20), primary_key=True, autoincrement=True)
    related_table = Column(String(50), index=True)
    related_id = Column(BIGINT(20), index=True)
    error_type = Column(String(50), index=True)
    error_message = Column(Text)
    error_timestamp = Column(TIMESTAMP, default=datetime.utcnow, index=True)
    resolved = Column(TINYINT(1), default=False, index=True)
    extra_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<ErrorLog(id={self.id}, type='{self.error_type}', resolved={self.resolved})>"

    def resolve(self) -> None:
        """Mark error as resolved."""
        self.resolved = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert error log to dictionary."""
        return {
            'related_table': self.related_table,
            'related_id': self.related_id,
            'error_type': self.error_type,
            'message': self.error_message,
            'timestamp': self.error_timestamp.isoformat() if self.error_timestamp else None,
            'resolved': bool(self.resolved),
            'extra_data': self.extra_data
        }

class SystemConfig(Base):
    """
    Model for system configuration management.
    
    Attributes:
        id: Primary key
        config_key: Unique configuration key
        config_value: Configuration value (stored as text)
        description: Description of the configuration
        last_updated: Timestamp of last update
        extra_data: Additional JSON data for complex configurations
    """
    
    __tablename__ = 'system_config'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(50), unique=True, nullable=False, index=True)
    config_value = Column(Text)
    description = Column(Text)
    last_updated = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    extra_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<SystemConfig(key='{self.config_key}', updated='{self.last_updated}')>"

    @classmethod
    def get_config(cls, session, key: str) -> Optional[str]:
        """
        Get configuration value by key.
        
        Args:
            session: Database session
            key: Configuration key to retrieve
            
        Returns:
            Optional[str]: Configuration value if found, None otherwise
        """
        config = session.query(cls).filter_by(config_key=key).first()
        return config.config_value if config else None

    @classmethod
    def get_configs(cls, session, keys: List[str]) -> Dict[str, str]:
        """
        Get multiple configuration values by keys.
        
        Args:
            session: Database session
            keys: List of configuration keys to retrieve
            
        Returns:
            Dict[str, str]: Dictionary of found configurations
        """
        configs = session.query(cls).filter(cls.config_key.in_(keys)).all()
        return {config.config_key: config.config_value for config in configs}

    @classmethod
    def set_config(
        cls,
        session,
        key: str,
        value: str,
        description: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ) -> None:
        """
        Set or update configuration value.
        
        Args:
            session: Database session
            key: Configuration key
            value: Configuration value
            description: Optional description
            extra_data: Optional additional data
        """
        config = session.query(cls).filter_by(config_key=key).first()
        if config:
            config.config_value = value
            if description:
                config.description = description
            if extra_data:
                config.extra_data = extra_data
        else:
            config = cls(
                config_key=key,
                config_value=value,
                description=description,
                extra_data=extra_data
            )
            session.add(config)
        session.commit()

    @classmethod
    def set_configs(cls, session, configs: Dict[str, Dict[str, Any]]) -> None:
        """
        Set multiple configuration values at once.
        
        Args:
            session: Database session
            configs: Dictionary of configurations to set
                    Format: {
                        'key': {
                            'value': str,
                            'description': Optional[str],
                            'extra_data': Optional[Dict]
                        }
                    }
        """
        for key, config_data in configs.items():
            cls.set_config(
                session,
                key,
                config_data['value'],
                config_data.get('description'),
                config_data.get('extra_data')
            )

    @classmethod
    def delete_config(cls, session, key: str) -> bool:
        """
        Delete configuration by key.
        
        Args:
            session: Database session
            key: Configuration key to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        deleted = session.query(cls).filter_by(config_key=key).delete()
        session.commit()
        return bool(deleted)

    @classmethod
    def get_configs_by_prefix(cls, session, prefix: str) -> List[Dict[str, Any]]:
        """
        Get all configurations that start with a specific prefix.
        
        Args:
            session: Database session
            prefix: Configuration key prefix to search for
            
        Returns:
            List[Dict]: List of matching configurations
        """
        configs = session.query(cls).filter(
            cls.config_key.like(f"{prefix}%")
        ).all()
        return [config.to_dict() for config in configs]

    @classmethod
    def search_configs(
        cls,
        session,
        search_term: str,
        search_description: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search configurations by key or description.
        
        Args:
            session: Database session
            search_term: Term to search for
            search_description: Whether to search in descriptions
            
        Returns:
            List[Dict]: List of matching configurations
        """
        query = session.query(cls)
        if search_description:
            query = query.filter(
                or_(
                    cls.config_key.like(f"%{search_term}%"),
                    cls.description.like(f"%{search_term}%")
                )
            )
        else:
            query = query.filter(cls.config_key.like(f"%{search_term}%"))
        
        return [config.to_dict() for config in query.all()]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert config to dictionary.
        
        Returns:
            Dict: Configuration data
        """
        return {
            'key': self.config_key,
            'value': self.config_value,
            'description': self.description,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'extra_data': self.extra_data
        }

    @classmethod
    def get_all_configs(cls, session) -> List[Dict[str, Any]]:
        """
        Get all system configurations.
        
        Args:
            session: Database session
            
        Returns:
            List[Dict]: List of all configurations
        """
        configs = session.query(cls).all()
        return [config.to_dict() for config in configs]

    @classmethod
    def clean_old_configs(cls, session, days: int = 30) -> int:
        """
        Remove configurations not updated in specified days.
        
        Args:
            session: Database session
            days: Number of days to consider old
            
        Returns:
            int: Number of configurations removed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = session.query(cls).filter(
            cls.last_updated < cutoff_date
        ).delete()
        session.commit()
        return deleted

    @classmethod
    def backup_configs(cls, session, backup_path: str) -> str:
        """
        Backup all configurations to JSON file.
        
        Args:
            session: Database session
            backup_path: Path to save backup
            
        Returns:
            str: Path to backup file
        """
        configs = cls.get_all_configs(session)
        backup_file = os.path.join(
            backup_path,
            f"config_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2)
            
        return backup_file

    @classmethod
    def restore_configs(cls, session, backup_file: str) -> int:
        """
        Restore configurations from backup file.
        
        Args:
            session: Database session
            backup_file: Path to backup file
            
        Returns:
            int: Number of configurations restored
        """
        with open(backup_file, 'r', encoding='utf-8') as f:
            configs = json.load(f)
            
        for config in configs:
            cls.set_config(
                session,
                config['key'],
                config['value'],
                config.get('description'),
                config.get('extra_data')
            )
            
        return len(configs)