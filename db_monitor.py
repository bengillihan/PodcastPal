"""
Database monitoring and optimization utilities
"""
import logging
import time
from datetime import datetime, timedelta
from app import db
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DatabaseMonitor:
    """Monitor database performance and usage"""
    
    _query_times = []
    _connection_count = 0
    
    @classmethod
    def log_query_time(cls, duration):
        """Log query execution time"""
        cls._query_times.append({
            'duration': duration,
            'timestamp': datetime.now()
        })
        
        # Keep only last 100 queries
        if len(cls._query_times) > 100:
            cls._query_times = cls._query_times[-100:]
    
    @classmethod
    def get_average_query_time(cls):
        """Get average query time for recent queries"""
        if not cls._query_times:
            return 0
        
        recent_queries = [
            q for q in cls._query_times 
            if datetime.now() - q['timestamp'] < timedelta(minutes=5)
        ]
        
        if not recent_queries:
            return 0
        
        return sum(q['duration'] for q in recent_queries) / len(recent_queries)
    
    @classmethod
    def get_slow_queries(cls, threshold=1.0):
        """Get queries slower than threshold (seconds)"""
        return [
            q for q in cls._query_times 
            if q['duration'] > threshold
        ]
    
    @classmethod
    def monitor_connections(cls):
        """Monitor active database connections"""
        try:
            result = db.session.execute(text("""
                SELECT count(*) as active_connections 
                FROM pg_stat_activity 
                WHERE application_name = 'PodcastPal'
            """))
            
            count = result.scalar()
            cls._connection_count = count
            
            if count > 5:
                logger.warning(f"High connection count: {count}")
            
            return count
            
        except Exception as e:
            logger.error(f"Error monitoring connections: {e}")
            return 0
    
    @classmethod
    def optimize_settings(cls):
        """Apply database optimization settings"""
        try:
            # Apply session-level optimizations
            optimizations = [
                "SET SESSION statement_timeout = '30s'",
                "SET SESSION idle_in_transaction_session_timeout = '60s'",
                "SET SESSION lock_timeout = '10s'",
                "SET SESSION work_mem = '1MB'",  # Limit memory per operation
            ]
            
            for setting in optimizations:
                db.session.execute(text(setting))
                
            logger.info("Applied database optimization settings")
            
        except Exception as e:
            logger.error(f"Error applying optimizations: {e}")
    
    @classmethod
    def cleanup_idle_connections(cls):
        """Terminate idle connections to reduce compute usage"""
        try:
            # Find and terminate idle connections older than 5 minutes
            result = db.session.execute(text("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE application_name = 'PodcastPal'
                AND state = 'idle'
                AND state_change < NOW() - INTERVAL '5 minutes'
            """))
            
            terminated = result.rowcount
            if terminated > 0:
                logger.info(f"Terminated {terminated} idle connections")
                
        except Exception as e:
            logger.error(f"Error cleaning up connections: {e}")

def create_monitoring_report():
    """Create a database performance report"""
    monitor = DatabaseMonitor()
    
    report = {
        'average_query_time': monitor.get_average_query_time(),
        'slow_queries_count': len(monitor.get_slow_queries()),
        'active_connections': monitor.monitor_connections(),
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"Database report: {report}")
    return report