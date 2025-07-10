from flask import Flask, request, jsonify, send_from_directory, render_template
from auth import hash_password, verify_password, login_required
from app.mysql_db import db
import uuid
import os
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/remote_images'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Initialize database
db.init_db()

@app.route('/')
@login_required()
def dashboard(user):
    return render_template('dashboard.html', user=user)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (data['username'],))
        user = cursor.fetchone()
    
    if not user or not verify_password(user['password_hash'], data['password']):
        return {'error': 'Invalid credentials'}, 401
    
    session_id = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(days=7)
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (session_id, user_id, expires_at) VALUES (%s, %s, %s)",
            (session_id, user['id'], expires_at)
        )
        conn.commit()
    
    response = jsonify({'success': True, 'user': {
        'username': user['username'],
        'is_admin': user['is_admin']
    }})
    response.set_cookie('session_id', session_id, httponly=True, max_age=604800)
    return response

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)