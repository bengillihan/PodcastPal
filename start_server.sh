#!/bin/bash

# Clear conflicting PostgreSQL environment variables to ensure Supabase is used exclusively
unset PGDATABASE
unset PGHOST  
unset PGPORT
unset PGUSER
unset PGPASSWORD

echo "Cleared conflicting PostgreSQL environment variables"
echo "Using DATABASE_URL for Supabase connection only"

# Start the Flask server
python main.py