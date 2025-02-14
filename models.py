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
    episodes = db.relationship('Episode', backref='feed', lazy=True)

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

class DropboxTraffic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    request_count = db.Column(db.Integer, default=0)
    total_bytes = db.Column(db.BigInteger, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def log_request(cls, bytes_transferred=0):
        """Log a Dropbox request with optional bytes transferred"""
        today = datetime.utcnow().date()
        traffic = cls.query.filter_by(date=today).first()

        if not traffic:
            traffic = cls(date=today)
            db.session.add(traffic)

        traffic.request_count += 1
        traffic.total_bytes += bytes_transferred
        traffic.updated_at = datetime.utcnow()

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error logging Dropbox traffic: {e}")

    @classmethod
    def import_historical_data(cls, date, request_count, total_bytes):
        """Import historical traffic data for a specific date"""
        try:
            traffic = cls.query.filter_by(date=date).first()
            if not traffic:
                traffic = cls(
                    date=date,
                    request_count=request_count,
                    total_bytes=total_bytes,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(traffic)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing historical traffic data: {e}")
            return False