import os
from flask import Flask
from flask_socketio import SocketIO
from .mysql_db import db  # Import the database instance
from .config import Config

# Create extensions instances
socketio = SocketIO()

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)  # If your MySQLDatabase class has init_app method
    socketio.init_app(app)
    
    # Import and register blueprints
    from .routes import main_bp, api_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Import and register error handlers
    from .errors import init_error_handlers
    init_error_handlers(app)
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app

# Make these available when importing from package
__all__ = ['create_app', 'db', 'socketio']