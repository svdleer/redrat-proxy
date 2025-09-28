#!/bin/bash
# Docker Entrypoint for RedRat Proxy
# This script initializes the database and starts the Flask application

set -e

echo "🐳 Docker Entrypoint: Starting RedRat Proxy setup..."

# Wait for MySQL to be ready if using external database
if [ "$MYSQL_HOST" != "localhost" ] && [ "$MYSQL_HOST" != "127.0.0.1" ]; then
    echo "🔍 Waiting for MySQL at $MYSQL_HOST:$MYSQL_PORT..."
    /app/wait-for-it.sh "$MYSQL_HOST:$MYSQL_PORT" --timeout=60 --strict -- echo "✅ MySQL is ready"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source /app/venv/bin/activate

# Set Python path
export PYTHONPATH="/app"
export PATH="/app/venv/bin:$PATH"

# Create necessary directories
echo "📁 Creating application directories..."
mkdir -p /app/app/static/uploads
mkdir -p /app/app/static/remote_images
mkdir -p /app/logs

# Set proper permissions
chmod -R 777 /app/app/static
chmod -R 777 /app/logs

# Initialize database if needed
echo "🗃️ Initializing database..."
/app/venv/bin/python -c "
import sys
sys.path.append('/app')
try:
    from app.mysql_db import db
    db.init_db()
    print('✅ Database initialized successfully')
except Exception as e:
    print(f'⚠️  Database initialization failed: {e}')
    print('🔧 Application will continue - database might need manual setup')
"

# Start the application
echo "🚀 Starting Flask application..."
echo "🌐 Application will be available at http://localhost:5000"
echo "📝 Logs will be written to /app/logs/"

# Ensure we're using the virtual environment's Python
echo "🐍 Using Python from venv: $(which python)"
echo "📦 Checking if dotenv is installed..."
/app/venv/bin/python -c "import dotenv; print('✅ dotenv is available')" || echo "❌ dotenv not found"

# Start Flask app with venv python
/app/venv/bin/python app.py
~           
