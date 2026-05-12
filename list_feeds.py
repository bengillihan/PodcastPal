"""One-time script to list feeds for review before setting all_recurring."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import Feed

with app.app_context():
    feeds = Feed.query.order_by(Feed.name).all()
    print(f"{'ID':<6} {'all_recurring':<14} {'Name'}")
    print("-" * 60)
    for f in feeds:
        print(f"{f.id:<6} {str(f.all_recurring):<14} {f.name}")
