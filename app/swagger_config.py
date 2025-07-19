"""
Swagger/OpenAPI configuration for RedRat Proxy API
"""

from flasgger import Swagger
from flask import Flask

def init_swagger(app: Flask):
    """Initialize Swagger documentation for the Flask app."""
    
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/api/spec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/api/static",
        "swagger_ui": True,
        "specs_route": "/api/docs"
    }
    
    template = {
        "swagger": "2.0",
        "info": {
            "title": "RedRat Proxy API",
            "description": "API for controlling RedRat infrared devices and managing remotes, commands, and sequences",
            "version": "1.0.0",
            "contact": {
                "name": "RedRat Proxy",
                "url": "https://github.com/svdleer/redrat-proxy"
            }
        },
        "host": "localhost:5000",
        "basePath": "/api",
        "schemes": ["http", "https"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "securityDefinitions": {
            "SessionAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "session_id",
                "description": "Session-based authentication using login credentials"
            }
        },
        "security": [
            {"SessionAuth": []}
        ],
        "tags": [
            {
                "name": "Authentication",
                "description": "User authentication and session management"
            },
            {
                "name": "Dashboard",
                "description": "Dashboard statistics and activity feed"
            },
            {
                "name": "Remotes",
                "description": "Remote control device management"
            },
            {
                "name": "Commands", 
                "description": "IR command execution and management"
            },
            {
                "name": "Sequences",
                "description": "Command sequence creation and execution"
            },
            {
                "name": "Schedules",
                "description": "Scheduled command execution"
            },
            {
                "name": "RedRat Devices",
                "description": "RedRat hardware device management"
            },
            {
                "name": "Users",
                "description": "User account management (Admin only)"
            }
        ]
    }
    
    swagger = Swagger(app, config=swagger_config, template=template)
    return swagger
