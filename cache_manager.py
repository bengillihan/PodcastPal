"""
Advanced caching to reduce database compute usage
"""
import logging
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import pytz
from flask import g

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages application-level caching to reduce database queries"""
    
    _cache = {}
    _cache_timestamps = {}
    
    @classmethod
    def get(cls, key, default=None):
        """Get cached value if not expired"""
        if key in cls._cache and key in cls._cache_timestamps:
            # Check if cache is still valid (30 minutes default)
            cache_time = cls._cache_timestamps[key]
            if datetime.now() - cache_time < timedelta(minutes=30):
                return cls._cache[key]
            else:
                # Remove expired cache
                cls._cache.pop(key, None)
                cls._cache_timestamps.pop(key, None)
        return default
    
    @classmethod
    def set(cls, key, value, ttl_minutes=30):
        """Set cached value with TTL"""
        cls._cache[key] = value
        cls._cache_timestamps[key] = datetime.now()
        
        # Clean up old cache entries periodically
        if len(cls._cache) > 100:
            cls._cleanup_expired()
    
    @classmethod
    def _cleanup_expired(cls):
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, timestamp in cls._cache_timestamps.items()
            if now - timestamp > timedelta(minutes=10)
        ]
        
        for key in expired_keys:
            cls._cache.pop(key, None)
            cls._cache_timestamps.pop(key, None)
        
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    @classmethod
    def clear(cls):
        """Clear all cache"""
        cls._cache.clear()
        cls._cache_timestamps.clear()

def cache_result(ttl_minutes=5):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache first
            cached_result = CacheManager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            CacheManager.set(cache_key, result, ttl_minutes)
            return result
        return wrapper
    return decorator

# RSS feed caching with longer TTL
class RSSCacheManager:
    """Specialized caching for RSS feeds"""
    
    _rss_cache = {}
    _rss_timestamps = {}
    
    @classmethod
    def get_feed_cache(cls, feed_id):
        """Get cached RSS feed content"""
        if feed_id in cls._rss_cache and feed_id in cls._rss_timestamps:
            cache_time = cls._rss_timestamps[feed_id]
            # RSS feeds cached for 24 hours to minimize compute requests
            if datetime.now() - cache_time < timedelta(hours=24):
                return cls._rss_cache[feed_id]
            else:
                cls._rss_cache.pop(feed_id, None)
                cls._rss_timestamps.pop(feed_id, None)
        return None
    
    @classmethod
    def set_feed_cache(cls, feed_id, content):
        """Cache RSS feed content"""
        cls._rss_cache[feed_id] = content
        cls._rss_timestamps[feed_id] = datetime.now()
        
        # Limit cache size
        if len(cls._rss_cache) > 50:
            cls._cleanup_old_feeds()
    
    @classmethod
    def _cleanup_old_feeds(cls):
        """Remove oldest cached feeds"""
        if not cls._rss_timestamps:
            return
            
        # Remove oldest 10 entries
        sorted_feeds = sorted(cls._rss_timestamps.items(), key=lambda x: x[1])
        for feed_id, _ in sorted_feeds[:10]:
            cls._rss_cache.pop(feed_id, None)
            cls._rss_timestamps.pop(feed_id, None)
    
    @classmethod
    def invalidate_feed(cls, feed_id):
        """Invalidate specific feed cache"""
        cls._rss_cache.pop(feed_id, None)
        cls._rss_timestamps.pop(feed_id, None)