import os
from app import app

import logging


logger = logging.getLogger(__name__)

# Clear conflicting PostgreSQL environment variables to ensure Supabase is used
pg_vars_to_clear = ['PGDATABASE', 'PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD']
for var in pg_vars_to_clear:
    if var in os.environ:
        del os.environ[var]
        logger.info(f"Cleared conflicting environment variable: {var}")

# Note: Database ping service removed - RSS feed access tracking keeps Supabase active

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
