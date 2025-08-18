"""
Database ping utility to keep Supabase active with daily health checks
"""
import logging
import threading
import time
from datetime import datetime, timedelta
import pytz
from app import app, db
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DatabasePinger:
    """Manages periodic database pings to prevent Supabase from going inactive"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.timezone = pytz.timezone('America/Los_Angeles')
        
    def start_daily_ping(self):
        """Start the daily ping service in a background thread"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.thread.start()
        logger.info("Database ping service started - pings every 24 hours")
        
    def stop_ping(self):
        """Stop the ping service"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Database ping service stopped")
        
    def _ping_loop(self):
        """Main loop that pings the database every 24 hours"""
        while self.running:
            try:
                self._perform_ping()
                # Wait 24 hours (86400 seconds) before next ping
                time.sleep(86400)
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")
                # Wait 1 hour before retrying on error
                time.sleep(3600)
                
    def _perform_ping(self):
        """Perform a lightweight database ping"""
        try:
            with app.app_context():
                # Simple query to keep connection active
                result = db.session.execute(text("SELECT 1 as ping"))
                ping_time = datetime.now(self.timezone)
                
                logger.info(f"Database ping successful at {ping_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                
                # Optional: Log to a simple ping table if you want to track pings
                try:
                    db.session.execute(text("""
                        CREATE TABLE IF NOT EXISTS database_pings (
                            id SERIAL PRIMARY KEY,
                            ping_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            status TEXT DEFAULT 'success'
                        )
                    """))
                    
                    db.session.execute(text("""
                        INSERT INTO database_pings (ping_time, status) 
                        VALUES (:ping_time, 'success')
                    """), {"ping_time": ping_time})
                    
                    # Keep only last 30 days of ping records to prevent bloat
                    cutoff_date = ping_time - timedelta(days=30)
                    db.session.execute(text("""
                        DELETE FROM database_pings 
                        WHERE ping_time < :cutoff_date
                    """), {"cutoff_date": cutoff_date})
                    
                    db.session.commit()
                    
                except Exception as e:
                    logger.warning(f"Could not log ping to database: {e}")
                    db.session.rollback()
                
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            raise
            
    def get_last_ping_status(self):
        """Get the status of the last ping"""
        try:
            with app.app_context():
                result = db.session.execute(text("""
                    SELECT ping_time, status 
                    FROM database_pings 
                    ORDER BY ping_time DESC 
                    LIMIT 1
                """))
                row = result.fetchone()
                if row:
                    return {
                        'last_ping': row[0],
                        'status': row[1]
                    }
                return None
        except Exception as e:
            logger.error(f"Could not get ping status: {e}")
            return None

# Global instance
database_pinger = DatabasePinger()

def start_database_ping_service():
    """Start the database ping service"""
    database_pinger.start_daily_ping()

def stop_database_ping_service():
    """Stop the database ping service"""
    database_pinger.stop_ping()