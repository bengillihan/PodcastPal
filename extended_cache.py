"""
Extended caching system for maximum database compute reduction
"""
import logging
import pickle
import os
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

class PersistentCache:
    """File-based persistent cache for long-term storage"""
    
    CACHE_DIR = "/tmp/podcast_cache"
    
    @classmethod
    def _ensure_cache_dir(cls):
        """Ensure cache directory exists"""
        if not os.path.exists(cls.CACHE_DIR):
            os.makedirs(cls.CACHE_DIR)
    
    @classmethod
    def _get_cache_path(cls, key):
        """Get file path for cache key"""
        cls._ensure_cache_dir()
        safe_key = key.replace('/', '_').replace(':', '_')
        return os.path.join(cls.CACHE_DIR, f"{safe_key}.cache")
    
    @classmethod
    def get(cls, key, max_age_hours=24):
        """Get cached value from file if not too old"""
        try:
            cache_path = cls._get_cache_path(key)
            
            if not os.path.exists(cache_path):
                return None
            
            # Check file age
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
            if file_age > timedelta(hours=max_age_hours):
                os.remove(cache_path)
                return None
            
            # Load cached data
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
                
        except Exception as e:
            logger.error(f"Error reading persistent cache: {e}")
            return None
    
    @classmethod
    def set(cls, key, value):
        """Save value to persistent cache"""
        try:
            cache_path = cls._get_cache_path(key)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
                
            logger.debug(f"Saved to persistent cache: {key}")
            
        except Exception as e:
            logger.error(f"Error writing persistent cache: {e}")
    
    @classmethod
    def clear_old(cls, max_age_hours=48):
        """Clear cache files older than specified hours"""
        try:
            if not os.path.exists(cls.CACHE_DIR):
                return
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            removed_count = 0
            
            for filename in os.listdir(cls.CACHE_DIR):
                filepath = os.path.join(cls.CACHE_DIR, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_time < cutoff_time:
                    os.remove(filepath)
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old cache files")
                
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")

def long_term_cache(hours=24):
    """Decorator for long-term persistent caching"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try persistent cache first
            cached_result = PersistentCache.get(cache_key, max_age_hours=hours)
            if cached_result is not None:
                logger.debug(f"Hit persistent cache for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            PersistentCache.set(cache_key, result)
            
            return result
        return wrapper
    return decorator

class UltraLongCache:
    """Ultra-long term caching for rarely changing data"""
    
    _ultra_cache = {}
    _ultra_timestamps = {}
    
    @classmethod
    def get(cls, key, max_age_days=7):
        """Get ultra-long cached value (default 7 days)"""
        if key in cls._ultra_cache and key in cls._ultra_timestamps:
            cache_time = cls._ultra_timestamps[key]
            if datetime.now() - cache_time < timedelta(days=max_age_days):
                return cls._ultra_cache[key]
            else:
                cls._ultra_cache.pop(key, None)
                cls._ultra_timestamps.pop(key, None)
        return None
    
    @classmethod
    def set(cls, key, value):
        """Set ultra-long cached value"""
        cls._ultra_cache[key] = value
        cls._ultra_timestamps[key] = datetime.now()
        
        # Limit cache size
        if len(cls._ultra_cache) > 50:
            cls._cleanup_oldest()
    
    @classmethod
    def _cleanup_oldest(cls):
        """Remove oldest entries"""
        if not cls._ultra_timestamps:
            return
        
        # Remove oldest 10 entries
        sorted_items = sorted(cls._ultra_timestamps.items(), key=lambda x: x[1])
        for key, _ in sorted_items[:10]:
            cls._ultra_cache.pop(key, None)
            cls._ultra_timestamps.pop(key, None)
    
    @classmethod
    def invalidate(cls, key):
        """Manually invalidate specific cache entry"""
        cls._ultra_cache.pop(key, None)
        cls._ultra_timestamps.pop(key, None)