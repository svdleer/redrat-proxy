import bcrypt
from functools import wraps
from flask import request, jsonify
from mysql_db import db
from datetime import datetime, timedelta

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(hashed, input_password):
    return bcrypt.checkpw(input_password.encode('utf-8'), hashed.encode('utf-8'))

def get_current_user():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return None
    
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT u.* FROM users u
            JOIN sessions s ON u.id = s.user_id
            WHERE s.session_id = %s AND s.expires_at > UTC_TIMESTAMP()
        ''', (session_id,))
        return cursor.fetchone()

def login_required(admin_only=False):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Unauthorized'}), 401
            if admin_only and not user['is_admin']:
                return jsonify({'error': 'Admin access required'}), 403
            return f(*args, **kwargs, user=user)
        return wrapper
    return decorator