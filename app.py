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
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 5,         # Limit max connections
    "max_overflow": 10,     # Allow temporary overflow connections
    "pool_timeout": 30      # Wait 30 seconds before timing out
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