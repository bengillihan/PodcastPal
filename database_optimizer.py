"""
Database optimization utilities to reduce compute usage
"""
import logging
from functools import wraps
from app import db
from flask import g
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Utility class for database optimization strategies"""
    
    @staticmethod
    def batch_commit_decorator(func):
        """Decorator to batch database commits and reduce transaction overhead"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # Commit the transaction
                db.session.commit()
                return result
            except Exception as e:
                db.session.rollback()
                logger.error(f"Database error in {func.__name__}: {str(e)}")
                raise
        return wrapper
    
    @staticmethod
    def lazy_load_episode_counts(feeds):
        """Efficiently load episode counts for multiple feeds"""
        if not feeds:
            return
        
        from models import Episode
        from sqlalchemy import func
        
        feed_ids = [feed.id for feed in feeds]
        episode_counts = db.session.query(
            Episode.feed_id,
            func.count(Episode.id).label('count')
        ).filter(Episode.feed_id.in_(feed_ids)) \
         .group_by(Episode.feed_id).all()
        
        count_map = {feed_id: count for feed_id, count in episode_counts}
        
        for feed in feeds:
            feed.episode_count = count_map.get(feed.id, 0)
    
    @staticmethod
    def optimize_query_for_pagination(query, page, per_page):
        """Optimize query execution for pagination"""
        # Use query.options() to control loading behavior
        return query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False,
            count=True  # Enable count for pagination info
        )
    
    @staticmethod
    def bulk_insert_episodes(episodes_data):
        """Bulk insert episodes to reduce database round trips"""
        from models import Episode
        
        try:
            episodes = [Episode(**data) for data in episodes_data]
            db.session.add_all(episodes)
            db.session.flush()  # Flush to get IDs without committing
            return episodes
        except Exception as e:
            logger.error(f"Error in bulk insert: {str(e)}")
            db.session.rollback()
            raise

# Context manager for optimized database sessions
class OptimizedDBSession:
    """Context manager for database sessions with optimization"""
    
    def __enter__(self):
        # Enable query optimizations (skip this for PostgreSQL as it doesn't have query_cache_type)
        # db.session.execute(text("SET SESSION query_cache_type = ON"))  # MySQL only
        return db.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            try:
                db.session.commit()
            except Exception as e:
                logger.error(f"Error committing session: {str(e)}")
                db.session.rollback()
                raise
        else:
            db.session.rollback()