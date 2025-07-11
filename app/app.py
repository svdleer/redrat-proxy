from flask import Flask, request, jsonify, send_from_directory, render_template, Response
# Fix imports to work both in local development and in Docker
try:
    # Try local import first (when running as a module)
    from app.auth import hash_password, verify_password, login_required
    from app.mysql_db import db
except ImportError:
    # Fall back to relative import (when importing within the package)
    from .auth import hash_password, verify_password, login_required
    from .mysql_db import db
import uuid
import os
import json
import time
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/remote_images'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB
# Configure for reverse proxy on host
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Initialize database
db.init_db()

@app.route('/')
@login_required()
def dashboard(user):
    return render_template('dashboard.html', user=user)

@app.route('/login')
def login_page():
    return render_template('login.html')

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

@app.route('/logout')
def logout():
    session_id = request.cookies.get('session_id')
    if session_id:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
            conn.commit()
    
    response = jsonify({'success': True})
    response.delete_cookie('session_id')
    response.headers['Location'] = '/login'
    response.status_code = 302
    return response

# API endpoints for the dashboard

@app.route('/api/stats')
@login_required()
def get_stats(user):
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get total remotes
        cursor.execute("SELECT COUNT(*) as total FROM remotes")
        remotes_count = cursor.fetchone()['total']
        
        # Get total commands
        cursor.execute("SELECT COUNT(*) as total FROM commands")
        commands_count = cursor.fetchone()['total']
        
        # Get total sequences (if table exists)
        sequences_count = 0
        schedules_count = 0
        try:
            cursor.execute("SELECT COUNT(*) as total FROM sequences")
            sequences_count = cursor.fetchone()['total']
            
            # Get total schedules (if table exists)
            cursor.execute("SELECT COUNT(*) as total FROM schedules")
            schedules_count = cursor.fetchone()['total']
        except:
            # Tables might not exist yet
            pass
            
    return jsonify({
        'remotes': remotes_count,
        'commands': commands_count,
        'sequences': sequences_count,
        'schedules': schedules_count
    })

@app.route('/api/remotes')
@login_required()
def get_remotes(user):
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM remotes")
        remotes = cursor.fetchall()
        
    return jsonify(remotes)

@app.route('/api/commands', methods=['GET', 'POST'])
@login_required()
def handle_commands(user):
    if request.method == 'GET':
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.*, r.name as remote_name 
                FROM commands c
                JOIN remotes r ON c.remote_id = r.id
                ORDER BY c.created_at DESC
                LIMIT 50
            """)
            commands = cursor.fetchall()
            
            # Convert datetime objects to strings for JSON serialization
            for cmd in commands:
                if isinstance(cmd['created_at'], datetime):
                    cmd['created_at'] = cmd['created_at'].isoformat()
                if isinstance(cmd.get('executed_at'), datetime):
                    cmd['executed_at'] = cmd['executed_at'].isoformat()
                    
        return jsonify(commands)
    else:  # POST
        data = request.json
        required_fields = ['remote_id', 'command', 'device']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO commands (remote_id, command, device, status, created_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['remote_id'], data['command'], data['device'], 'pending', user['id']))
            conn.commit()
            
            # Get the inserted command details
            cursor.execute("""
                SELECT c.*, r.name as remote_name 
                FROM commands c
                JOIN remotes r ON c.remote_id = r.id
                WHERE c.id = LAST_INSERT_ID()
            """)
            command = cursor.fetchone()
            
        return jsonify({
            'success': True,
            'message': 'Command queued successfully',
            'command': command
        }), 201

@app.route('/api/activity')
@login_required()
def get_activity(user):
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, r.name as remote_name, u.username as user_name
            FROM commands c
            JOIN remotes r ON c.remote_id = r.id
            JOIN users u ON c.created_by = u.id
            ORDER BY c.created_at DESC
            LIMIT 10
        """)
        activities = cursor.fetchall()
        
        # Convert datetime objects to strings for JSON serialization
        for act in activities:
            if isinstance(act['created_at'], datetime):
                act['created_at'] = act['created_at'].isoformat()
            if isinstance(act.get('executed_at'), datetime):
                act['executed_at'] = act['executed_at'].isoformat()
                
    return jsonify(activities)

@app.route('/api/events')
@login_required()
def events(user):
    def event_stream():
        # Keep connection alive for SSE
        while True:
            # Check for new commands or status changes
            with db.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT c.*, r.name as remote_name
                    FROM commands c
                    JOIN remotes r ON c.remote_id = r.id
                    WHERE c.status_updated_at > NOW() - INTERVAL 5 SECOND
                    ORDER BY c.created_at DESC
                    LIMIT 5
                """)
                recent_commands = cursor.fetchall()
                
            if recent_commands:
                for cmd in recent_commands:
                    # Convert datetime objects to strings
                    for key, val in cmd.items():
                        if isinstance(val, datetime):
                            cmd[key] = val.isoformat()
                            
                    yield f"data: {json.dumps({'type': 'command_update', 'command': cmd})}\n\n"
            
            # Send a heartbeat every 15 seconds to keep connection alive
            yield f"data: {json.dumps({'type': 'heartbeat', 'time': datetime.now().isoformat()})}\n\n"
            time.sleep(15)
    
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)