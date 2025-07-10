from flask import Flask
from flask_socketio import SocketIO
from app.config import Config
from app.utils.logger import setup_logger
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Initialize extensions
socketio = SocketIO()
logger = setup_logger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Configure for reverse proxy
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_prefix=1
    )

    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    socketio.init_app(app)
    
    # Register blueprints
    from app.routes import main_bp, api_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Error handlers
    from app.errors import init_error_handlers
    init_error_handlers(app)
    
    return app