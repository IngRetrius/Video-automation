"""
models/tiktok_model.py: Modelo SQLAlchemy para publicaciones de TikTok
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship

from news_scraper.config.database import Base

class TikTokPublications(Base):
    """Model for managing TikTok publications."""
    
    __tablename__ = 'tiktok_publications'
    __table_args__ = {'extend_existing': True}

    id = Column(BIGINT(20), primary_key=True, autoincrement=True)
    processed_content_id = Column(
        BIGINT(20), 
        ForeignKey('processed_content.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    tiktok_video_id = Column(String(50), unique=True)
    tiktok_url = Column(String(255))
    scheduled_time = Column(DateTime, index=True)
    published_at = Column(TIMESTAMP)
    status = Column(
        Enum('pending', 'scheduled', 'published', 'failed'),
        default='pending',
        index=True
    )
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    error_message = Column(Text)
    extra_data = Column(JSON)

    # Relationships
    processed_content = relationship(
        "ProcessedContent",
        back_populates="tiktok_publication",
        lazy='joined'
    )

    def __repr__(self) -> str:
        return (
            f"<TikTokPublication("
            f"id={self.id}, "
            f"status='{self.status}', "
            f"video_id='{self.tiktok_video_id}'"
            f")>"
        )

    def update_metrics(self, metrics: Dict[str, int]) -> None:
        """
        Update publication metrics.
        
        Args:
            metrics: Dictionary containing metrics to update
                    (views, likes, shares, comments)
        """
        self.views_count = metrics.get('views', self.views_count)
        self.likes_count = metrics.get('likes', self.likes_count)
        self.shares_count = metrics.get('shares', self.shares_count)
        self.comments_count = metrics.get('comments', self.comments_count)

    @property
    def engagement_rate(self) -> float:
        """
        Calculate engagement rate as percentage.
        
        Returns:
            float: Engagement rate (interactions/views * 100)
        """
        if not self.views_count:
            return 0.0
        interactions = self.likes_count + self.comments_count + self.shares_count
        return (interactions / self.views_count) * 100

    @property
    def is_published(self) -> bool:
        """Check if video is published successfully."""
        return self.status == 'published' and bool(self.tiktok_video_id)

    @property
    def is_scheduled(self) -> bool:
        """Check if video is scheduled for future publication."""
        return (
            self.status == 'scheduled' and
            self.scheduled_time and
            self.scheduled_time > datetime.now()
        )

    @property
    def performance_metrics(self) -> Dict[str, Any]:
        """Get consolidated performance metrics."""
        return {
            'views': self.views_count,
            'likes': self.likes_count,
            'shares': self.shares_count,
            'comments': self.comments_count,
            'engagement_rate': self.engagement_rate
        }

    def log_error(self, error_message: str) -> None:
        """
        Log an error for this publication.
        
        Args:
            error_message: Error description
        """
        self.error_message = error_message
        self.status = 'failed'

    def schedule_publication(self, scheduled_time: datetime) -> None:
        """
        Schedule the publication for a future time.
        
        Args:
            scheduled_time: When to publish the video
        """
        self.scheduled_time = scheduled_time
        self.status = 'scheduled'

    def mark_as_published(self, video_id: str, video_url: str) -> None:
        """
        Mark the publication as successfully published.
        
        Args:
            video_id: TikTok video ID
            video_url: TikTok video URL
        """
        self.tiktok_video_id = video_id
        self.tiktok_url = video_url
        self.published_at = datetime.utcnow()
        self.status = 'published'

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert publication to dictionary.
        
        Returns:
            Dict: Publication data
        """
        return {
            'id': self.id,
            'video_id': self.tiktok_video_id,
            'url': self.tiktok_url,
            'status': self.status,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'views': self.views_count,
            'likes': self.likes_count,
            'shares': self.shares_count,
            'comments': self.comments_count,
            'engagement_rate': self.engagement_rate,
            'error_message': self.error_message,
            'extra_data': self.extra_data
        }