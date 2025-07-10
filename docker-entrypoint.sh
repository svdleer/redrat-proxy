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

# Check if the app.app module can be imported
echo "Testing import of app.app..."
python -c "import app.app; print('Import successful!')"

# Check module paths
echo "Python path:"
python -c "import sys; print(sys.path)"

# Run the command
exec "$@"
