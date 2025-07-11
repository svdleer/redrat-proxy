"""
Main routes module
"""
from flask import Blueprint

# Create main blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)
admin_bp = Blueprint('admin', __name__)

# Import blueprints from modules
from .sequences import sequences_bp
from .schedules import schedules_bp
from .templates import templates_bp

# Register route blueprints
def init_routes(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(sequences_bp)
    app.register_blueprint(schedules_bp)
    app.register_blueprint(templates_bp)

# Import views to register routes
from . import views
