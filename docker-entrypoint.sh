#!/bin/bash
set -e

# Activate virtual environment
source /app/venv/bin/activate

# Print Python version and location
echo "Using Python: $(which python)"
python --version

# Print Flask version
echo "Flask version: $(pip show flask | grep Version)"
echo "Flask-SocketIO version: $(pip show flask-socketio | grep Version)"

# List all files in the app directory
echo "Files in /app directory:"
ls -la /app
echo "Files in /app/app directory:"
ls -la /app/app

# Check module paths
echo "Python path:"
python -c "import sys; print(sys.path)"

# Create a test Python file to verify imports
cat > /tmp/test_imports.py << EOF
try:
    import app
    print('✅ Successfully imported app package')
except ImportError as e:
    print('❌ Failed to import app package:', e)

try:
    import app.mysql_db
    print('✅ Successfully imported app.mysql_db')
except ImportError as e:
    print('❌ Failed to import app.mysql_db:', e)

try:
    import app.auth
    print('✅ Successfully imported app.auth')
except ImportError as e:
    print('❌ Failed to import app.auth:', e)

try:
    from app.app import app
    print('✅ Successfully imported Flask app')
except ImportError as e:
    print('❌ Failed to import Flask app:', e)
EOF

# Run the test file
echo "Testing imports..."
python /tmp/test_imports.py

# Test MySQL connection
echo "Testing MySQL connection..."
cat > /tmp/test_mysql.py << EOF
import os
import sys
import mysql.connector

try:
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'host.docker.internal'),
        user=os.getenv('MYSQL_USER', 'redrat'),
        password=os.getenv('MYSQL_PASSWORD', 'redratpass'),
        database=os.getenv('MYSQL_DB', 'redrat_proxy')
    )
    print("✅ Successfully connected to MySQL")
    conn.close()
except Exception as e:
    print("❌ Failed to connect to MySQL:", e)
    sys.exit(1)
EOF

python /tmp/test_mysql.py

# Continue with command execution
echo "Starting the application..."
exec "$@"

# Execute the command passed to docker run
echo "Running command: $@"
exec "$@"
"

# Run the command
exec "$@"
