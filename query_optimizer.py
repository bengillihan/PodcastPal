"""
Query optimization utilities to reduce database compute usage
"""
import logging
from functools import lru_cache
from app import db
from models import Feed, Episode, User
from sqlalchemy import text, func
from flask_login import current_user

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Optimizes database queries to reduce compute time"""
    
    @staticmethod
    @lru_cache(maxsize=100)
    def get_user_feed_count(user_id):
        """Cached query for user's feed count"""
        return db.session.query(func.count(Feed.id)).filter(Feed.user_id == user_id).scalar()
    
    @staticmethod
    @lru_cache(maxsize=200)
    def get_feed_episode_count(feed_id):
        """Cached query for feed's episode count"""
        return db.session.query(func.count(Episode.id)).filter(Episode.feed_id == feed_id).scalar()
    
    @staticmethod
    def bulk_load_episode_counts(feed_ids):
        """Efficiently load episode counts for multiple feeds"""
        if not feed_ids:
            return {}
        
        # Single query to get all episode counts
        counts = db.session.query(
            Episode.feed_id,
            func.count(Episode.id).label('count')
        ).filter(Episode.feed_id.in_(feed_ids)) \
         .group_by(Episode.feed_id).all()
        
        return {feed_id: count for feed_id, count in counts}
    
    @staticmethod
    def optimize_rss_query(feed_id):
        """Optimized query for RSS feed generation - recurring episodes plus recent non-recurring"""
        query = text("""
            (SELECT id, title, description, audio_url, release_date, is_recurring
             FROM episode 
             WHERE feed_id = :feed_id AND is_recurring = true)
            UNION ALL
            (SELECT id, title, description, audio_url, release_date, is_recurring
             FROM episode 
             WHERE feed_id = :feed_id AND is_recurring = false
             AND release_date >= NOW() - INTERVAL '90 days' AND release_date <= NOW()
             ORDER BY release_date DESC
             LIMIT 100)
        """)
        
        result = db.session.execute(query, {'feed_id': feed_id})
        return result.fetchall()
    
    @staticmethod
    def cleanup_query_cache():
        """Clear the LRU cache to free memory"""
        QueryOptimizer.get_user_feed_count.cache_clear()
        QueryOptimizer.get_feed_episode_count.cache_clear()
        logger.info("Cleared query cache")

# Database maintenance queries
class MaintenanceQueries:
    """Database maintenance to reduce ongoing compute costs"""
    
    @staticmethod
    def analyze_tables():
        """Run ANALYZE on tables to update statistics"""
        try:
            # Use correct table names (SQLAlchemy creates 'user' not 'user_table')
            db.session.execute(text('ANALYZE "user"'))
            db.session.execute(text("ANALYZE feed"))
            db.session.execute(text("ANALYZE episode"))
            db.session.commit()
            logger.info("Database tables analyzed for better query planning")
        except Exception as e:
            logger.error(f"Error analyzing tables: {e}")
            db.session.rollback()
    
    @staticmethod
    def vacuum_tables():
        """Vacuum tables to reclaim space and improve performance"""
        try:
            # Note: VACUUM cannot be run inside a transaction in PostgreSQL
            db.session.commit()  # Ensure no active transaction
            
            # Run maintenance commands
            with db.engine.connect().execution_options(autocommit=True) as conn:
                conn.execute(text('VACUUM ANALYZE "user"'))
                conn.execute(text("VACUUM ANALYZE feed"))
                conn.execute(text("VACUUM ANALYZE episode"))
            
            logger.info("Database vacuum completed")
        except Exception as e:
            logger.error(f"Error vacuuming tables: {e}")