"""
Session management utilities to optimize database connections
"""
import logging
from contextlib import contextmanager
from app import db, app
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy import text
import time

logger = logging.getLogger(__name__)

class SessionManager:
    """Advanced session management for database optimization"""
    
    @staticmethod
    @contextmanager
    def get_optimized_session():
        """Get an optimized database session with automatic cleanup"""
        session = db.session
        start_time = time.time()
        
        try:
            # Configure session for optimal performance
            session.execute(text("SET SESSION statement_timeout = '30s'"))
            session.execute(text("SET SESSION lock_timeout = '10s'"))
            session.execute(text("SET SESSION idle_in_transaction_session_timeout = '60s'"))
            
            yield session
            session.commit()
            
        except (DisconnectionError, OperationalError) as e:
            logger.warning(f"Database connection issue, retrying: {e}")
            session.rollback()
            # Retry once with fresh connection
            try:
                db.engine.dispose()  # Clear connection pool
                session.commit()
            except Exception as retry_e:
                logger.error(f"Retry failed: {retry_e}")
                raise
                
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
            
        finally:
            duration = time.time() - start_time
            if duration > 5.0:
                logger.warning(f"Long database session: {duration:.2f}s")
    
    @staticmethod
    def cleanup_connections():
        """Cleanup idle database connections"""
        try:
            with app.app_context():
                # Remove session to return connection to pool
                db.session.remove()
                
                # Dispose connections that have been idle too long
                db.engine.dispose()
                
                logger.debug("Database connections cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up connections: {e}")

# Background cleanup task
def periodic_cleanup():
    """Periodic cleanup of database resources"""
    import threading
    import time
    
    def cleanup_worker():
        while True:
            time.sleep(1800)  # Every 30 minutes
            try:
                with app.app_context():
                    SessionManager.cleanup_connections()
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    return cleanup_thread