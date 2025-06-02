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
    "pool_recycle": 1800,    # Recycle connections every 30 minutes (was 5 min)
    "pool_pre_ping": True,   # Verify connections before use
    "pool_size": 3,          # Reduce default connection pool size
    "max_overflow": 5,       # Reduce overflow connections 
    "pool_timeout": 20,      # Reduce timeout to fail faster
    "connect_args": {
        "connect_timeout": 10,      # Connection timeout
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