from app import app
import atexit
import logging
from models import DropboxTraffic

logger = logging.getLogger(__name__)

# Register function to commit any remaining batched traffic data on shutdown
@atexit.register
def commit_traffic_data_on_shutdown():
    logger.info("Server shutting down - committing any remaining traffic data")
    try:
        DropboxTraffic._commit_batch()
    except Exception as e:
        logger.error(f"Error committing traffic data on shutdown: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
