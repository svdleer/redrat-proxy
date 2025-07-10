import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the Flask app
from app.app import app

if __name__ == '__main__':
    # When running directly, use the development server
    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    # For production with Gunicorn
    # The app variable will be used by Gunicorn
    pass
