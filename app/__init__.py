import os
import sys
from flask import Flask
from flask_socketio import SocketIO

# Add the parent directory to sys.path if needed
app_dir = os.path.abspath(os.path.dirname(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(app_dir))

# Import the database instance
try:
    from .mysql_db import db
except ImportError:
    from app.mysql_db import db

try:
    from .config import Config
except ImportError:
    from app.config import Config

# Create extensions instances
socketio = SocketIO()

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)  # If your MySQLDatabase class has init_app method
    socketio.init_app(app)
    
    # Initialize routes
    from .routes import init_routes
    init_routes(app)
    
    # Import and register error handlers
    from .errors import init_error_handlers
    init_error_handlers(app)
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app

# Make these available when importing from package
__all__ = ['create_app', 'db', 'socketio']