import bcrypt
from functools import wraps
from flask import request, jsonify, redirect, url_for
# Fix imports to work both in local development and in Docker
try:
    # Try local import first (when running as a module)
    from app.mysql_db import db
except ImportError:
    # Fall back to relative import (when importing within the package)
    from .mysql_db import db
from datetime import datetime, timedelta

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(hashed, input_password):
    return bcrypt.checkpw(input_password.encode('utf-8'), hashed.encode('utf-8'))

def get_current_user():
    """Get current user from session or API key."""
    # Try session authentication first
    session_id = request.cookies.get('session_id')
    if session_id:
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT u.* FROM users u
                JOIN sessions s ON u.id = s.user_id
                WHERE s.session_id = %s AND s.expires_at > UTC_TIMESTAMP()
            ''', (session_id,))
            user = cursor.fetchone()
            if user:
                return user
    
    # Try API key authentication
    api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if api_key:
        try:
            from app.models.api_key import APIKey
            api_key_obj = APIKey.get_by_key(api_key)
            if api_key_obj and not api_key_obj.is_expired():
                with db.get_connection() as conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute('SELECT * FROM users WHERE id = %s', (api_key_obj.user_id,))
                    user = cursor.fetchone()
                    if user:
                        return user
        except Exception:
            pass  # Continue to return None
    
    return None

def login_required(admin_only=False):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                # Check if this is an API request
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('login_page'))
            if admin_only and not user['is_admin']:
                # Check if this is an API request
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Admin access required'}), 403
                # Redirect to dashboard with an error message
                return redirect(url_for('dashboard', error="Admin access required"))
            return f(*args, **kwargs, user=user)
        return wrapper
    return decorator

def api_key_required(admin_only=False):
    """Decorator for API-only endpoints that require API key authentication."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Only check API key authentication (no session fallback)
            api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
            if not api_key:
                return jsonify({'error': 'API key required'}), 401
            
            try:
                from app.models.api_key import APIKey
                api_key_obj = APIKey.get_by_key(api_key)
                if not api_key_obj:
                    return jsonify({'error': 'Invalid API key'}), 401
                
                if api_key_obj.is_expired():
                    return jsonify({'error': 'API key expired'}), 401
                
                with db.get_connection() as conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute('SELECT * FROM users WHERE id = %s', (api_key_obj.user_id,))
                    user = cursor.fetchone()
                    
                    if not user:
                        return jsonify({'error': 'User not found'}), 401
                    
                    if admin_only and not user['is_admin']:
                        return jsonify({'error': 'Admin access required'}), 403
                    
                    return f(*args, **kwargs, user=user)
            except Exception as e:
                return jsonify({'error': 'Authentication error'}), 401
        return wrapper
    return decorator