import os
import logging
import pytz
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure timezone
TIMEZONE = pytz.timezone('America/Los_Angeles')
logger.info(f"Configured timezone: {TIMEZONE}")

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 3600,    # Increase to 1 hour to reduce connection overhead
    "pool_pre_ping": True,   # Verify connections before use
    "pool_size": 2,          # Further reduce pool size for low-traffic app
    "max_overflow": 3,       # Reduce overflow connections 
    "pool_timeout": 30,      # Increase timeout to avoid rapid reconnections
    "connect_args": {
        "connect_timeout": 15,      # Slightly longer connection timeout
        "application_name": "PodcastPal"  # Help identify app in DB logs
    }
}
app.config['TIMEZONE'] = TIMEZONE

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "google_auth.login"

# Import routes after app initialization to avoid circular imports
with app.app_context():
    from models import User, Feed, Episode
    db.create_all()

    from google_auth import google_auth
    app.register_blueprint(google_auth)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    import routes
    
    # Add connection cleanup middleware
    @app.teardown_appcontext
    def cleanup_db_connections(error):
        """Clean up database connections after each request"""
        db.session.remove()
        
    # Setup periodic maintenance (Flask 2.2+ compatible)
    def setup_maintenance():
        """Setup periodic database maintenance"""
        from query_optimizer import MaintenanceQueries
        import threading
        import time
        
        def maintenance_worker():
            """Background maintenance worker"""
            while True:
                time.sleep(3600)  # Run every hour
                try:
                    with app.app_context():
                        MaintenanceQueries.analyze_tables()
                except Exception as e:
                    logger.error(f"Maintenance error: {e}")
        
        # Start maintenance in background thread
        maintenance_thread = threading.Thread(target=maintenance_worker, daemon=True)
        maintenance_thread.start()
    
    # Initialize maintenance on startup
    setup_maintenance()
    
    # Start periodic cleanup
    from session_manager import periodic_cleanup
    periodic_cleanup()