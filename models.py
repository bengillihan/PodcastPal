from datetime import datetime
from app import db
from flask_login import UserMixin
from slugify import slugify
import random
import string
import logging

logger = logging.getLogger(__name__)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    feeds = db.relationship('Feed', backref='owner', lazy=True)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))  # New field for podcast image
    website_url = db.Column(db.String(500))  # New field for optional website URL
    url_slug = db.Column(db.String(200), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_rss_access = db.Column(db.DateTime, nullable=True)
    episodes = db.relationship('Episode', backref='feed', lazy='dynamic', cascade='all, delete-orphan')  # Use dynamic loading and cascade deletes
    
    __table_args__ = (
        db.Index('ix_feed_user_id', 'user_id'),
        db.Index('ix_feed_url_slug', 'url_slug'),
        db.Index('ix_feed_user_created', 'user_id', 'created_at'),  # Composite index for dashboard queries
    )

    def regenerate_url_slug(self):
        """Regenerate the URL slug for the feed"""
        base_slug = slugify(self.name)

        # Add random suffix to ensure uniqueness
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        new_slug = f"{base_slug}-{suffix}"

        # Update the slug
        self.url_slug = new_slug
        db.session.commit()

        return new_slug

class Episode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    audio_url = db.Column(db.String(500), nullable=False)
    release_date = db.Column(db.DateTime, nullable=False)
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_episode_feed_id', 'feed_id'),
        db.Index('ix_episode_release_date', 'release_date'),
        db.Index('ix_episode_feed_date', 'feed_id', 'release_date'),  # Composite index for feed episode queries
    )

