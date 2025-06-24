"""
Advanced database connection management to minimize compute hours
"""
import logging
from contextlib import contextmanager
from functools import wraps
from app import db
from flask import g
from sqlalchemy import text
import time

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages database connections to reduce compute usage"""
    
    @staticmethod
    def close_idle_connections():
        """Close idle database connections to reduce compute time"""
        try:
            # Dispose of connection pool to force cleanup of idle connections
            db.engine.dispose()
            logger.info("Disposed idle database connections")
        except Exception as e:
            logger.error(f"Error disposing connections: {e}")
    
    @staticmethod
    @contextmanager
    def efficient_session():
        """Context manager for efficient database sessions"""
        session = db.session
        try:
            # Enable query optimizations at session level
            session.execute(text("SET SESSION statement_timeout = '30s'"))  # Prevent long-running queries
            session.execute(text("SET SESSION idle_in_transaction_session_timeout = '60s'"))  # Close idle transactions
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            # Don't explicitly close - let pool manage it
            pass
    
    @staticmethod
    def minimize_connection_decorator(func):
        """Decorator to minimize database connection time"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                # Only commit if we're not in a nested transaction
                if db.session.is_active and not db.session.in_transaction():
                    db.session.commit()
                return result
            except Exception as e:
                if db.session.is_active:
                    db.session.rollback()
                logger.error(f"Error in {func.__name__}: {e}")
                raise
            finally:
                duration = time.time() - start_time
                if duration > 1.0:  # Log slow operations
                    logger.warning(f"Slow database operation in {func.__name__}: {duration:.2f}s")
        return wrapper

# Connection cleanup utility
def cleanup_connections_middleware():
    """Middleware to cleanup connections after requests"""
    @wraps
    def cleanup():
        # Remove session after each request to prevent connection leaks
        db.session.remove()
    return cleanup