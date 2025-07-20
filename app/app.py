from flask import Flask, request, jsonify, send_from_directory, render_template, Response
import json
import os
import logging
import uuid
import sys
import time
import tempfile
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)

# Create Flask app first
app = Flask(__name__)
print(f"✅ Flask app created successfully: {app}")
print(f"✅ Flask app type: {type(app)}")
print(f"✅ Flask app name: {app.name}")

# Configure Flask app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'static/remote_images'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

# Configure for reverse proxy on host
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
print("✅ Flask app configured successfully")

# Initialize Swagger documentation
try:
    from flasgger import Swagger
    from app.swagger_config import init_swagger
    swagger = init_swagger(app)
    print("✅ Swagger documentation initialized")
except ImportError:
    print("⚠️  Swagger not available - install flasgger for API documentation")
    swagger = None

# Import dependencies with error handling
try:
    # Try local import first (when running as a module)
    from app.auth import hash_password, verify_password, login_required
    from app.mysql_db import db
    print("✅ Successfully imported auth and database modules")
except ImportError as e:
    print(f"⚠️  Local import failed: {e}")
    try:
        # Fall back to relative import (when importing within the package)
        from .auth import hash_password, verify_password, login_required
        from .mysql_db import db
        print("✅ Successfully imported auth and database modules (relative import)")
    except ImportError as e2:
        print(f"❌ Both import methods failed: {e2}")
        # Create dummy functions to prevent app from failing
        def hash_password(password):
            return password
        def verify_password(hash, password):
            return hash == password
        def login_required(admin_only=False):
            def decorator(f):
                return f
            return decorator
        
        # Create a dummy database object
        class DummyDB:
            def init_db(self):
                print("⚠️  Using dummy database - authentication disabled")
        db = DummyDB()
        print("⚠️  Using dummy auth/db - please fix imports and restart")

# Initialize database (handle errors gracefully)
try:
    db.init_db()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️  Database initialization failed: {e}")
    print("🔧 Application will continue without database - please fix and restart")

# Add current datetime and request to all templates
@app.context_processor
def inject_globals():
    return {'now': datetime.utcnow(), 'request': request}

@app.route('/')
@login_required()
def dashboard(user):
    return render_template('dashboard.html', user=user)

@app.route('/redrat-devices')
@login_required(admin_only=True)
def redrat_devices(user):
    """RedRat devices management page (admin only)"""
    return render_template('admin/redrat_devices.html', user=user)

@app.route('/dashboard')
@login_required()
def dashboard_alias(user):
    return render_template('dashboard.html', user=user)

@app.route('/login')
def login_page():
    return render_template('login.html', user=None)

@app.route('/api/login', methods=['POST'])
def login():
    """
    User Login
    ---
    tags:
      - Authentication
    summary: Authenticate user and create session
    description: Authenticates a user with username and password, creates a session, and returns user information
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              description: Username
              example: admin
            password:
              type: string
              description: Password
              example: admin
          required:
            - username
            - password
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            user:
              type: object
              properties:
                username:
                  type: string
                  example: admin
                is_admin:
                  type: boolean
                  example: true
      401:
        description: Invalid credentials
        schema:
          type: object
          properties:
            error:
              type: string
              example: Invalid credentials
    """
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
    """
    Get Dashboard Statistics
    ---
    tags:
      - Dashboard
    summary: Get dashboard statistics and counts
    description: Retrieve statistics for dashboard including counts of remotes, commands, sequences, schedules, and RedRat devices
    security:
      - SessionAuth: []
    responses:
      200:
        description: Dashboard statistics
        schema:
          type: object
          properties:
            remotes:
              type: integer
              description: Total number of remotes
              example: 5
            commands:
              type: integer
              description: Total number of command templates
              example: 25
            sequences:
              type: integer
              description: Total number of sequences
              example: 3
            schedules:
              type: integer
              description: Total number of schedules
              example: 2
            redrat_devices:
              type: integer
              description: Total number of RedRat devices
              example: 1
      401:
        description: Unauthorized - Login required
    """
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get total remotes
        cursor.execute("SELECT COUNT(*) as total FROM remotes")
        remotes_count = cursor.fetchone()['total']
        
        # Get total available commands (command templates)
        cursor.execute("SELECT COUNT(*) as total FROM command_templates")
        commands_count = cursor.fetchone()['total']
        
        # Get total sequences (if table exists)
        sequences_count = 0
        schedules_count = 0
        redrat_devices_count = 0
        try:
            cursor.execute("SELECT COUNT(*) as total FROM sequences")
            sequences_count = cursor.fetchone()['total']
            
            # Get total schedules (if table exists)
            cursor.execute("SELECT COUNT(*) as total FROM schedules")
            schedules_count = cursor.fetchone()['total']
            
            # Get total RedRat devices
            cursor.execute("SELECT COUNT(*) as total FROM redrat_devices")
            redrat_devices_count = cursor.fetchone()['total']
        except:
            # Tables might not exist yet
            pass
            
    return jsonify({
        'remotes': remotes_count,
        'commands': commands_count,
        'sequences': sequences_count,
        'schedules': schedules_count,
        'redrat_devices': redrat_devices_count
    })

@app.route('/api/remotes')
@login_required()
def get_remotes(user):
    """
    Get All Remotes
    ---
    tags:
      - Remotes
    summary: Get all remotes with command counts
    description: Retrieve a list of all remotes including the number of commands for each remote
    security:
      - SessionAuth: []
    responses:
      200:
        description: List of remotes
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
                description: Remote ID
                example: 1
              name:
                type: string
                description: Remote name
                example: "Samsung TV"
              description:
                type: string
                description: Remote description
                example: "Living room Samsung smart TV"
              command_count:
                type: integer
                description: Number of commands for this remote
                example: 15
              created_at:
                type: string
                format: date-time
                description: Creation timestamp
                example: "2023-01-01T00:00:00Z"
      401:
        description: Unauthorized - Login required
    """
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.*, COUNT(c.id) as command_count 
            FROM remotes r 
            LEFT JOIN commands c ON r.id = c.remote_id 
            GROUP BY r.id
        """)
        remotes = cursor.fetchall()
        
        # Convert any bytes fields to strings to avoid JSON serialization errors
        for remote in remotes:
            if 'config_data' in remote and isinstance(remote['config_data'], bytes):
                remote['config_data'] = remote['config_data'].decode('utf-8')
        
    return jsonify(remotes)
    
@app.route('/api/remotes', methods=['POST'])
@login_required()
def create_remote(user):
    """
    Create New Remote
    ---
    tags:
      - Remotes
    summary: Create a new remote control
    description: Create a new remote control configuration
    security:
      - SessionAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: Remote name
              example: "Samsung TV"
            description:
              type: string
              description: Remote description
              example: "Living room Samsung smart TV"
          required:
            - name
    responses:
      201:
        description: Remote created successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            remote_id:
              type: integer
              description: ID of the created remote
              example: 1
            message:
              type: string
              example: "Remote created successfully"
      400:
        description: Bad request - Missing required fields
      401:
        description: Unauthorized - Login required
    """
    data = request.json
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({"error": "Remote name is required"}), 400
    
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        # Check if remote with this name already exists
        cursor.execute("SELECT id FROM remotes WHERE name = %s", (data['name'],))
        if cursor.fetchone():
            return jsonify({"error": "Remote with this name already exists"}), 400
        
        # Insert the remote
        cursor.execute("""
            INSERT INTO remotes (
                name, manufacturer, device_type, description
            ) VALUES (%s, %s, %s, %s)
        """, (
            data['name'], 
            data.get('manufacturer', ''),
            data.get('device_type', ''),
            data.get('description', '')
        ))
        
        remote_id = cursor.lastrowid
        conn.commit()
        
        # Get the created remote
        cursor.execute("SELECT * FROM remotes WHERE id = %s", (remote_id,))
        remote = cursor.fetchone()
    
    return jsonify(remote)
    
@app.route('/api/remotes/import-xml', methods=['POST'])
@login_required()
def import_xml(user):
    """Import remotes from XML file"""
    import tempfile
    
    if 'xml_file' not in request.files:
        return jsonify({"error": "No XML file uploaded"}), 400
        
    xml_file = request.files['xml_file']
    
    if not xml_file or xml_file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not xml_file.filename.endswith('.xml'):
        return jsonify({"error": "File must be an XML file"}), 400
    
    # Save the file temporarily
    temp_path = os.path.join(tempfile.gettempdir(), "remotes_import.xml")
    xml_file.save(temp_path)
    
    # Debug: Check the uploaded file
    app.logger.info(f"Saved uploaded file to: {temp_path}")
    try:
        with open(temp_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            app.logger.info(f"First line of uploaded file: {repr(first_line)}")
    except Exception as e:
        app.logger.error(f"Error reading uploaded file: {e}")
    
    try:
        # Use the remote service to import XML
        from app.services.remote_service import import_remotes_from_xml
        
        imported_count = import_remotes_from_xml(temp_path, user['id'])
        return jsonify({"message": "Import successful", "imported": imported_count}), 200
    except Exception as e:
        app.logger.error(f"Error importing XML: {str(e)}")
        return jsonify({"error": "Error importing XML", "message": str(e)}), 500
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
@app.route('/api/remotes/<int:remote_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required()
def remote_detail(user, remote_id):
    """Handle individual remote operations"""
    with db.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Get remote details
            cursor.execute("SELECT * FROM remotes WHERE id = %s", (remote_id,))
            remote = cursor.fetchone()
            
            if not remote:
                return jsonify({"error": "Remote not found"}), 404
            
            # Convert any bytes fields to strings to avoid JSON serialization errors
            if 'config_data' in remote and isinstance(remote['config_data'], bytes):
                remote['config_data'] = remote['config_data'].decode('utf-8')
                
            return jsonify(remote)
            
        elif request.method == 'PUT':
            # Update remote
            data = request.json
            
            # Validate required fields
            if not data.get('name'):
                return jsonify({"error": "Remote name is required"}), 400
            
            # Check if remote exists
            cursor.execute("SELECT id FROM remotes WHERE id = %s", (remote_id,))
            if not cursor.fetchone():
                return jsonify({"error": "Remote not found"}), 404
            
            # Update the remote
            cursor.execute("""
                UPDATE remotes SET 
                name = %s, 
                manufacturer = %s,
                device_model_number = %s,
                device_type = %s,
                description = %s
                WHERE id = %s
            """, (
                data['name'],
                data.get('manufacturer', ''),
                data.get('device_model_number', ''),
                data.get('device_type', ''),
                data.get('description', ''),
                remote_id
            ))
            conn.commit()
            
            # Get updated remote
            cursor.execute("SELECT * FROM remotes WHERE id = %s", (remote_id,))
            remote = cursor.fetchone()
            
            return jsonify(remote)
            
        elif request.method == 'DELETE':
            # Check if remote exists
            cursor.execute("SELECT id FROM remotes WHERE id = %s", (remote_id,))
            if not cursor.fetchone():
                return jsonify({"error": "Remote not found"}), 404
            
            # Delete the remote
            cursor.execute("DELETE FROM remotes WHERE id = %s", (remote_id,))
            conn.commit()
            
            return jsonify({"message": f"Remote {remote_id} deleted successfully"})

@app.route('/api/remotes/<int:remote_id>/commands', methods=['GET'])
@login_required()
def get_remote_commands(user, remote_id):
    """Get available commands for a specific remote"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, template_data
                FROM command_templates
                WHERE JSON_EXTRACT(template_data, '$.remote_id') = %s
                ORDER BY name
            """, (remote_id,))
            
            commands = []
            for row in cursor.fetchall():
                command_name = row[0]
                template_data = row[1]
                # Parse template data to get UID if needed
                try:
                    import json
                    data = json.loads(template_data)
                    uid = data.get('uid', '')
                except:
                    uid = ''
                
                commands.append({
                    'name': command_name,
                    'uid': uid
                })
            
        return jsonify(commands)
    except Exception as e:
        print(f"Error fetching commands for remote {remote_id}: {e}")
        return jsonify({'error': 'Failed to fetch commands'}), 500

@app.route('/api/commands', methods=['GET', 'POST'])
@login_required()
def handle_commands(user):
    """
    Get Commands or Execute Command
    ---
    tags:
      - Commands
    summary: Get recent commands or execute a new command
    description: |
      GET: Retrieve the 50 most recent commands with remote information
      POST: Execute a command for a specific remote
    security:
      - SessionAuth: []
    parameters:
      - name: body
        in: body
        required: false
        description: Required for POST requests to execute commands
        schema:
          type: object
          properties:
            remote_id:
              type: integer
              description: ID of the remote to use
              example: 1
            command:
              type: string
              description: Name of the command to execute
              example: "power_on"
            redrat_device_id:
              type: integer
              description: ID of the RedRat device to use for execution
              example: 1
            ir_port:
              type: integer
              description: RedRat IR output port (1-16)
              example: 1
              default: 1
            power:
              type: integer
              description: IR signal power (1-100)
              example: 100
              default: 100
    responses:
      200:
        description: |
          GET: List of recent commands
          POST: Command execution result
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            commands:
              type: array
              description: List of commands (GET only)
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  command_name:
                    type: string
                    example: "power_on"
                  remote_name:
                    type: string
                    example: "Samsung TV"
                  executed_at:
                    type: string
                    format: date-time
                    example: "2023-01-01T00:00:00Z"
                  created_at:
                    type: string
                    format: date-time
                    example: "2023-01-01T00:00:00Z"
            message:
              type: string
              description: Success message (POST only)
              example: "Command executed successfully"
      400:
        description: Bad request - Missing required parameters for POST
      401:
        description: Unauthorized - Login required
    """
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
        required_fields = ['remote_id', 'command', 'redrat_device_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO commands (remote_id, command, device, status, created_by, ir_port, power)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (data['remote_id'], data['command'], f"RedRat Device {data['redrat_device_id']}", 'pending', user['id'], 
                  data.get('ir_port', 1), data.get('power', 50)))
            conn.commit()
            
            command_id = cursor.lastrowid
            
            # Add command to execution queue
            try:
                from app.services.command_queue import add_command
                command_data = {
                    'id': command_id,
                    'remote_id': data['remote_id'],
                    'command': data['command'],
                    'device': f"RedRat Device {data['redrat_device_id']}",
                    'redrat_device_id': data['redrat_device_id'],
                    'ir_port': data.get('ir_port', 1),
                    'power': data.get('power', 50)
                }
                
                if add_command(command_data):
                    logger.info(f"Command {command_id} queued for execution")
                else:
                    logger.error(f"Failed to queue command {command_id}")
                    
            except Exception as e:
                logger.error(f"Error queuing command {command_id}: {str(e)}")
            
            # Get the inserted command details
            cursor.execute("""
                SELECT c.*, r.name as remote_name 
                FROM commands c
                JOIN remotes r ON c.remote_id = r.id
                WHERE c.id = %s
            """, (command_id,))
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

@app.route('/api/activity', methods=['DELETE'])
@login_required()
def clear_activity_log(user):
    """Clear all command history/activity log"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM commands")
            conn.commit()
            
        return jsonify({
            'success': True,
            'message': 'Activity log cleared successfully'
        })
    except Exception as e:
        logger.error(f"Error clearing activity log: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear activity log'
        }), 500

@app.route('/api/history', methods=['DELETE'])
@login_required()
def clear_command_history(user):
    """Clear recent command history (same as activity log)"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM commands")
            conn.commit()
            
        return jsonify({
            'success': True,
            'message': 'Command history cleared successfully'
        })
    except Exception as e:
        logger.error(f"Error clearing command history: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear command history'
        }), 500

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

@app.route('/commands')
@login_required()
def commands(user):
    return render_template('command.html', user=user)

@app.route('/command')
@login_required()
def command(user):
    return render_template('command.html', user=user)

@app.route('/sequences')
@login_required()
def sequences(user):
    return render_template('sequences.html', user=user)

@app.route('/schedules')
@login_required()
def schedules(user):
    return render_template('schedules.html', user=user)

@app.route('/admin/remotes')
@login_required(admin_only=True)
def admin_remotes(user):
    # Get remotes from database with command count
    remotes = []
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.id, r.name, r.manufacturer, r.device_type, 
                       COUNT(ct.id) as command_count
                FROM remotes r
                LEFT JOIN command_templates ct ON JSON_EXTRACT(ct.template_data, '$.remote_id') = r.id
                GROUP BY r.id, r.name, r.manufacturer, r.device_type
                ORDER BY r.name
            """)
            
            for row in cursor.fetchall():
                remotes.append({
                    'id': row[0],
                    'name': row[1],
                    'manufacturer': row[2] or '',
                    'device_type': row[3] or '',
                    'command_count': row[4]
                })
    except Exception as e:
        print(f"Error fetching remotes: {e}")
    
    return render_template('admin/remotes.html', user=user, remotes=remotes)

@app.route('/admin/users')
@login_required(admin_only=True)
def admin_users(user):
    return render_template('admin/users.html', user=user)

@app.route('/admin/logs')
@login_required(admin_only=True)
def logs(user):
    return render_template('logs.html', user=user)

@app.route('/logs')
@login_required(admin_only=True)
def logs_alias(user):
    return render_template('logs.html', user=user)

@app.route('/redrat-remotes')
@login_required(admin_only=True)
def redrat_remotes_redirect(user):
    """Redirect /redrat-remotes to /admin/remotes for compatibility"""
    from flask import redirect, url_for
    return redirect('/admin/remotes')

@app.route('/api/command-templates', methods=['GET'])
@login_required()
def get_command_templates(user):
    """Get all command templates with remote info"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ct.id, ct.file_id, ct.name, ct.device_type, ct.template_data,
                       rf.name as remote_name, rf.filename
                FROM command_templates ct
                JOIN remote_files rf ON ct.file_id = rf.id
                ORDER BY rf.name, ct.name
            """)
            
            templates = []
            for row in cursor.fetchall():
                # Handle bytes data in template_data
                template_data = row[4]
                if isinstance(template_data, bytes):
                    try:
                        template_data = template_data.decode('utf-8')
                    except UnicodeDecodeError:
                        template_data = str(template_data)
                
                templates.append({
                    'id': row[0],
                    'file_id': row[1],
                    'command_name': row[2],
                    'device_type': row[3],
                    'template_data': template_data,
                    'remote_name': row[5],
                    'filename': row[6]
                })
            
            return jsonify(templates)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/command-templates', methods=['POST'])
@login_required(admin_only=True)
def create_command_template(user):
    """Create a new command template"""
    try:
        data = request.get_json()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO command_templates (file_id, name, device_type, template_data, created_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['file_id'], data['name'], data.get('device_type', ''), 
                  data.get('template_data', ''), user['id']))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Command template created successfully'}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/command-templates/<int:template_id>', methods=['GET'])
@login_required()
def get_command_template(user, template_id):
    """Get a specific command template by ID"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ct.id, ct.file_id, ct.name, ct.device_type, ct.template_data,
                       rf.name as remote_name, rf.filename
                FROM command_templates ct
                JOIN remote_files rf ON ct.file_id = rf.id
                WHERE ct.id = %s
            """, (template_id,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': 'Command template not found'}), 404
            
            # Handle bytes data in template_data
            template_data = row[4]
            if isinstance(template_data, bytes):
                try:
                    template_data = template_data.decode('utf-8')
                except UnicodeDecodeError:
                    template_data = str(template_data)
            
            template = {
                'id': row[0],
                'file_id': row[1],
                'command_name': row[2],
                'device_type': row[3],
                'template_data': template_data,
                'remote_name': row[5],
                'filename': row[6]
            }
            
            return jsonify(template)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/command-templates/<int:template_id>', methods=['PUT'])
@login_required(admin_only=True)
def update_command_template(user, template_id):
    """Update a command template"""
    try:
        data = request.get_json()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE command_templates 
                SET file_id = %s, name = %s, device_type = %s, template_data = %s
                WHERE id = %s
            """, (data['file_id'], data['name'], data.get('device_type', ''), 
                  data.get('template_data', ''), template_id))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Command template updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/command-templates/<int:template_id>', methods=['DELETE'])
@login_required(admin_only=True)
def delete_command_template(user, template_id):
    """Delete a command template"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM command_templates WHERE id = %s", (template_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Command template deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences', methods=['GET'])
@login_required()
def get_sequences(user):
    """
    Get All Sequences
    ---
    tags:
      - Sequences
    summary: Get all command sequences for the current user
    description: Retrieve a list of all command sequences created by the current user, including command counts
    security:
      - SessionAuth: []
    responses:
      200:
        description: List of sequences
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            sequences:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: Sequence ID
                    example: 1
                  name:
                    type: string
                    description: Sequence name
                    example: "Morning TV Routine"
                  description:
                    type: string
                    description: Sequence description
                    example: "Turn on TV, switch to news channel"
                  command_count:
                    type: integer
                    description: Number of commands in sequence
                    example: 3
                  created_at:
                    type: string
                    format: date-time
                    description: Creation timestamp
                    example: "2023-01-01T00:00:00Z"
      401:
        description: Unauthorized - Login required
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.name, s.description, s.created_at,
                       COUNT(sc.id) as command_count
                FROM sequences s
                LEFT JOIN sequence_commands sc ON s.id = sc.sequence_id
                WHERE s.created_by = %s
                GROUP BY s.id, s.name, s.description, s.created_at
                ORDER BY s.created_at DESC
            """, (user['id'],))
            
            sequences = []
            for row in cursor.fetchall():
                sequences.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'created_at': row[3].isoformat() if row[3] else None,
                    'command_count': row[4]
                })
            
            return jsonify({'success': True, 'sequences': sequences})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences', methods=['POST'])
@login_required()
def create_sequence(user):
    """Create a new command sequence"""
    try:
        data = request.get_json()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sequences (created_by, name, description)
                VALUES (%s, %s, %s)
            """, (user['id'], data['name'], data.get('description', '')))
            
            sequence_id = cursor.lastrowid
            conn.commit()
            
            # Return the created sequence
            return jsonify({
                'success': True, 
                'message': 'Sequence created successfully',
                'sequence': {
                    'id': sequence_id,
                    'name': data['name'],
                    'description': data.get('description', ''),
                    'commands': []
                }
            }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences/<int:sequence_id>', methods=['GET'])
@login_required()
def get_sequence(user, sequence_id):
    """Get a specific sequence with its commands"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.name, s.description
                FROM sequences s
                WHERE s.id = %s AND s.created_by = %s
            """, (sequence_id, user['id']))
            
            sequence = cursor.fetchone()
            if not sequence:
                return jsonify({'success': False, 'error': 'Sequence not found'}), 404
            
            # Get commands for this sequence
            cursor.execute("""
                SELECT sc.id, sc.command, sc.device, sc.remote_id, sc.position, sc.delay_ms,
                       rf.name as remote_name, sc.ir_port, sc.power
                FROM sequence_commands sc
                JOIN remote_files rf ON sc.remote_id = rf.id
                WHERE sc.sequence_id = %s
                ORDER BY sc.position
            """, (sequence_id,))
            
            commands = []
            for row in cursor.fetchall():
                commands.append({
                    'id': row[0],
                    'command': row[1],
                    'device': row[2],
                    'remote_id': row[3],
                    'position': row[4],
                    'delay_ms': row[5],
                    'remote_name': row[6],
                    'ir_port': row[7] if row[7] is not None else 1,
                    'power': row[8] if row[8] is not None else 100
                })
            
            return jsonify({
                'success': True,
                'sequence': {
                    'id': sequence[0],
                    'name': sequence[1],
                    'description': sequence[2],
                    'commands': commands
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences/<int:sequence_id>', methods=['PUT'])
@login_required()
def update_sequence(user, sequence_id):
    """Update a sequence"""
    try:
        data = request.get_json()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if sequence exists and belongs to user
            cursor.execute("""
                SELECT id FROM sequences 
                WHERE id = %s AND created_by = %s
            """, (sequence_id, user['id']))
            
            if not cursor.fetchone():
                return jsonify({'success': False, 'error': 'Sequence not found'}), 404
            
            # Update the sequence
            cursor.execute("""
                UPDATE sequences 
                SET name = %s, description = %s
                WHERE id = %s
            """, (data['name'], data.get('description', ''), sequence_id))
            
            conn.commit()
            
            # Return the updated sequence
            return jsonify({
                'success': True, 
                'message': 'Sequence updated successfully',
                'sequence': {
                    'id': sequence_id,
                    'name': data['name'],
                    'description': data.get('description', ''),
                    'commands': []  # Commands would be loaded separately
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences/<int:sequence_id>', methods=['DELETE'])
@login_required()
def delete_sequence(user, sequence_id):
    """Delete a command sequence"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # First delete sequence commands
            cursor.execute("DELETE FROM sequence_commands WHERE sequence_id = %s", (sequence_id,))
            
            # Then delete the sequence
            cursor.execute("DELETE FROM command_sequences WHERE id = %s AND user_id = %s", (sequence_id, user['id']))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Sequence deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users', methods=['GET'])
@login_required(admin_only=True)
def get_users(user):
    """
    Get All Users
    ---
    tags:
      - Users
    summary: Get all users (admin only)
    description: Retrieve a list of all users in the system. Admin access required.
    security:
      - SessionAuth: []
    responses:
      200:
        description: List of users
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            users:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: User ID
                    example: 1
                  username:
                    type: string
                    description: Username
                    example: "admin"
                  is_admin:
                    type: boolean
                    description: Whether user has admin privileges
                    example: true
                  created_at:
                    type: string
                    format: date-time
                    description: User creation timestamp
                    example: "2023-01-01T00:00:00Z"
                  last_login:
                    type: string
                    format: date-time
                    description: Last login timestamp
                    example: "2023-01-01T00:00:00Z"
      401:
        description: Unauthorized - Admin access required
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.username, u.is_admin, u.created_at
                FROM users u
                ORDER BY u.created_at DESC
            """)
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row[0],
                    'username': row[1],
                    'is_admin': bool(row[2]),
                    'created_at': row[3].isoformat() if row[3] else None,
                    'last_login': None  # We'll set this to None for now since sessions table doesn't track this
                })
            
            return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@login_required(admin_only=True)
def create_user(user):
    """Create a new user (admin only)"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        is_admin = data.get('is_admin', False)
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400
        
        # Check if username already exists
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({'success': False, 'error': 'Username already exists'}), 409
        
        # Hash password and create user
        password_hash = hash_password(password)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, is_admin)
                VALUES (%s, %s, %s)
            """, (username, password_hash, is_admin))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'User created successfully'}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required(admin_only=True)
def update_user(user, user_id):
    """Update a user (admin only)"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        is_admin = data.get('is_admin')
        
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if new username conflicts with existing user
            cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, user_id))
            if cursor.fetchone():
                return jsonify({'success': False, 'error': 'Username already exists'}), 409
            
            # Update user
            if password:
                password_hash = hash_password(password)
                cursor.execute("""
                    UPDATE users 
                    SET username = %s, password_hash = %s, is_admin = %s
                    WHERE id = %s
                """, (username, password_hash, is_admin, user_id))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET username = %s, is_admin = %s
                    WHERE id = %s
                """, (username, is_admin, user_id))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'User updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required(admin_only=True)
def delete_user(user, user_id):
    """Delete a user (admin only)"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Don't allow deleting the admin user
            cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            user_to_delete = cursor.fetchone()
            if user_to_delete and user_to_delete[0] == 'admin':
                return jsonify({'success': False, 'error': 'Cannot delete admin user'}), 400
            
            # Delete user sessions first
            cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
            
            # Delete user
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@login_required(admin_only=True)
def reset_user_password(user, user_id):
    """Reset a user's password to default (admin only)"""
    try:
        default_password = 'admin123'
        password_hash = hash_password(default_password)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s
                WHERE id = %s
            """, (password_hash, user_id))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Password reset successfully', 'new_password': default_password})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/remote-files', methods=['GET'])
@login_required()
def get_remote_files(user):
    """Get all remote files"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, filename, device_type
                FROM remote_files
                ORDER BY name
            """)
            
            files = []
            for row in cursor.fetchall():
                files.append({
                    'id': row[0],
                    'name': row[1],
                    'filename': row[2],
                    'device_type': row[3]
                })
            
            return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sequences/<int:sequence_id>/commands', methods=['POST'])
@login_required()
def add_command_to_sequence(user, sequence_id):
    """Add a command to a sequence
    ---
    tags:
      - Sequences
    parameters:
      - in: path
        name: sequence_id
        type: integer
        required: true
        description: The sequence ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            command_id:
              type: integer
              description: The command template ID
            delay_ms:
              type: integer
              description: Delay in milliseconds before executing this command
              default: 0
            ir_port:
              type: integer
              description: IR port to use (1-16)
              default: 1
            power:
              type: integer
              description: IR power level (0-100)
              default: 100
    responses:
      201:
        description: Command added to sequence successfully
      404:
        description: Command template not found
      500:
        description: Server error
    """
    try:
        data = request.get_json()
        command_id = data.get('command_id')  # This is actually a command template ID
        delay_ms = data.get('delay_ms', 0)
        ir_port = data.get('ir_port', 1)  # Default to port 1
        power = data.get('power', 50)  # Default to half power
        
        # First, get the command template to extract command info
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ct.name, ct.file_id, rf.name as remote_name
                FROM command_templates ct
                JOIN remote_files rf ON ct.file_id = rf.id
                WHERE ct.id = %s
            """, (command_id,))
            
            template = cursor.fetchone()
            if not template:
                return jsonify({'success': False, 'error': 'Command template not found'}), 404
            
            # Get the next position for this sequence
            cursor.execute("""
                SELECT COALESCE(MAX(position), 0) + 1 as next_position
                FROM sequence_commands
                WHERE sequence_id = %s
            """, (sequence_id,))
            
            next_position = cursor.fetchone()[0]
            
            # Insert the command into the sequence
            cursor.execute("""
                INSERT INTO sequence_commands (sequence_id, command, device, remote_id, position, delay_ms, ir_port, power)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE delay_ms = VALUES(delay_ms), ir_port = VALUES(ir_port), power = VALUES(power)
            """, (sequence_id, template[0], '', template[1], next_position, delay_ms, ir_port, power))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Command added to sequence'}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences/<int:sequence_id>/commands/<int:command_id>', methods=['DELETE'])
@login_required()
def remove_command_from_sequence(user, sequence_id, command_id):
    """Remove a command from a sequence"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM sequence_commands 
                WHERE id = %s AND sequence_id = %s
            """, (command_id, sequence_id))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Command not found in sequence'}), 404
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Command removed from sequence'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences/<int:sequence_id>/execute', methods=['POST'])
@login_required()
def execute_sequence(user, sequence_id):
    """Execute a sequence of commands"""
    try:
        # Get sequence and its commands
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.name, s.description
                FROM sequences s
                WHERE s.id = %s AND s.created_by = %s
            """, (sequence_id, user['id']))
            
            sequence = cursor.fetchone()
            if not sequence:
                return jsonify({'success': False, 'error': 'Sequence not found'}), 404
            
            # Get commands for this sequence
            cursor.execute("""
                SELECT sc.id, sc.command, sc.device, sc.remote_id, sc.position, sc.delay_ms,
                       rf.name as remote_name, sc.ir_port, sc.power
                FROM sequence_commands sc
                JOIN remote_files rf ON sc.remote_id = rf.id
                WHERE sc.sequence_id = %s
                ORDER BY sc.position
            """, (sequence_id,))
            
            commands = []
            for row in cursor.fetchall():
                commands.append({
                    'id': row[0],
                    'command': row[1],
                    'device': row[2],
                    'remote_id': row[3],
                    'position': row[4],
                    'delay_ms': row[5],
                    'remote_name': row[6],
                    'ir_port': row[7] if row[7] is not None else 1,
                    'power': row[8] if row[8] is not None else 100
                })
        
        if not commands:
            return jsonify({'success': False, 'error': 'No commands found in sequence'}), 400
        
        # Add sequence to execution queue
        try:
            from app.services.command_queue import add_sequence
            sequence_data = {
                'id': sequence_id,
                'name': sequence[1],
                'commands': commands
            }
            
            if add_sequence(sequence_data):
                logger.info(f"Sequence {sequence_id} queued for execution")
                return jsonify({'success': True, 'message': 'Sequence execution started'})
            else:
                logger.error(f"Failed to queue sequence {sequence_id}")
                return jsonify({'success': False, 'error': 'Failed to queue sequence'}), 500
                
        except Exception as e:
            logger.error(f"Error queuing sequence {sequence_id}: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to queue sequence'}), 500
            
    except Exception as e:
        logger.error(f"Error executing sequence {sequence_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/schedules', methods=['GET'])
@login_required()
def get_schedules(user):
    """Get all schedules for the current user"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.name, s.type, s.target_id, s.schedule_type, 
                       s.schedule_data, s.next_run, s.last_run, s.status, s.created_at
                FROM schedules s
                WHERE s.created_by = %s
                ORDER BY s.created_at DESC
            """, (user['id'],))
            
            schedules = []
            for row in cursor.fetchall():
                # Parse schedule_data if it exists
                schedule_data = row[5]
                if schedule_data:
                    if isinstance(schedule_data, str):
                        schedule_data = json.loads(schedule_data)
                    elif isinstance(schedule_data, bytes):
                        schedule_data = json.loads(schedule_data.decode('utf-8'))
                
                schedules.append({
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'target_id': row[3],
                    'schedule_type': row[4],
                    'schedule_data': schedule_data,
                    'next_run': row[6].isoformat() if row[6] else None,
                    'last_run': row[7].isoformat() if row[7] else None,
                    'status': row[8],
                    'created_at': row[9].isoformat()
                })
            
            return jsonify({'success': True, 'schedules': schedules})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/schedules', methods=['POST'])
@login_required()
def create_schedule(user):
    """Create a new schedule"""
    try:
        data = request.get_json()
        
        # Generate a name based on the schedule type and target
        schedule_name = f"{data['type'].title()} Schedule - {data['schedule_type'].title()}"
        
        # Calculate next run time based on schedule type
        next_run = None
        schedule_data = data.get('schedule_data', {})
        
        if data['schedule_type'] == 'once':
            # For 'once' type, use the provided datetime
            if 'datetime' in schedule_data:
                next_run = schedule_data['datetime']
        elif data['schedule_type'] == 'daily':
            # For daily, use today's date with the provided time
            if 'time' in schedule_data:
                from datetime import datetime, date
                today = date.today()
                time_str = schedule_data['time']
                next_run = f"{today} {time_str}:00"
        elif data['schedule_type'] == 'weekly':
            # For weekly, calculate next occurrence
            if 'day' in schedule_data and 'time' in schedule_data:
                # Simplified: use current date + time for now
                from datetime import datetime
                next_run = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif data['schedule_type'] == 'monthly':
            # For monthly, calculate next occurrence
            if 'day' in schedule_data and 'time' in schedule_data:
                # Simplified: use current date + time for now
                from datetime import datetime
                next_run = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # If next_run is still None, default to current time
        if not next_run:
            from datetime import datetime
            next_run = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedules (name, type, target_id, schedule_type, schedule_data, 
                                     next_run, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                schedule_name,
                data['type'],
                data['target_id'],
                data['schedule_type'],
                json.dumps(schedule_data),
                next_run,
                'active',
                user['id']
            ))
            
            schedule_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Schedule created successfully',
                'schedule': {
                    'id': schedule_id,
                    'name': schedule_name,
                    'type': data['type'],
                    'target_id': data['target_id'],
                    'schedule_type': data['schedule_type'],
                    'schedule_data': schedule_data,
                    'next_run': next_run,
                    'status': 'active'
                }
            }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
@login_required()
def delete_schedule(user, schedule_id):
    """Delete a schedule"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM schedules 
                WHERE id = %s AND created_by = %s
            """, (schedule_id, user['id']))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Schedule not found'}), 404
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Schedule deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Command execution endpoint
@app.route('/api/commands/<int:command_id>/execute', methods=['POST'])
@login_required()
def execute_command(user, command_id):
    """Execute a single command immediately"""
    try:
        # Get command details
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.*, r.name as remote_name
                FROM commands c
                JOIN remotes r ON c.remote_id = r.id
                WHERE c.id = %s
            """, (command_id,))
            
            command = cursor.fetchone()
            if not command:
                return jsonify({'success': False, 'error': 'Command not found'}), 404
        
        # Get execution parameters from request
        data = request.get_json() or {}
        ir_port = data.get('ir_port', 1)
        power = data.get('power', 50)
        
        # Add command to execution queue
        try:
            from app.services.command_queue import add_command
            command_data = {
                'id': command_id,
                'remote_id': command['remote_id'],
                'command': command['command'],
                'device': command['device'],
                'ir_port': ir_port,
                'power': power
            }
            
            if add_command(command_data):
                logger.info(f"Command {command_id} queued for immediate execution")
                return jsonify({
                    'success': True, 
                    'message': f"Command '{command['command']}' sent to {command['remote_name']}",
                    'command': command['command'],
                    'remote': command['remote_name']
                })
            else:
                logger.error(f"Failed to queue command {command_id}")
                return jsonify({'success': False, 'error': 'Failed to queue command'}), 500
                
        except Exception as e:
            logger.error(f"Error queuing command {command_id}: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to queue command'}), 500
            
    except Exception as e:
        logger.error(f"Error executing command {command_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Direct remote command execution endpoint
@app.route('/api/remotes/<int:remote_id>/commands/<command_name>/execute', methods=['POST'])
@login_required()
def execute_remote_command(user, remote_id, command_name):
    """Execute a command directly on a remote without storing in database"""
    try:
        # Get remote details
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM remotes WHERE id = %s", (remote_id,))
            remote = cursor.fetchone()
            
            if not remote:
                return jsonify({'success': False, 'error': 'Remote not found'}), 404
        
        # Get execution parameters from request
        data = request.get_json() or {}
        ir_port = data.get('ir_port', 1)
        power = data.get('power', 50)
        device = data.get('device', remote['name'])
        
        # Create temporary command for execution
        temp_command_id = int(time.time() * 1000000)  # Unique temporary ID
        
        # Add command to execution queue
        try:
            from app.services.command_queue import add_command
            command_data = {
                'id': temp_command_id,
                'remote_id': remote_id,
                'command': command_name,
                'device': device,
                'ir_port': ir_port,
                'power': power
            }
            
            if add_command(command_data):
                logger.info(f"Direct command '{command_name}' queued for remote {remote['name']}")
                return jsonify({
                    'success': True, 
                    'message': f"Command '{command_name}' sent to {remote['name']}",
                    'command': command_name,
                    'remote': remote['name']
                })
            else:
                logger.error(f"Failed to queue direct command '{command_name}'")
                return jsonify({'success': False, 'error': 'Failed to queue command'}), 500
                
        except Exception as e:
            logger.error(f"Error queuing direct command '{command_name}': {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to queue command'}), 500
            
    except Exception as e:
        logger.error(f"Error executing direct command '{command_name}': {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# NetBox Types API endpoint
@app.route('/api/netbox-types', methods=['GET'])
@login_required()
def get_netbox_types(user):
    """Get all NetBox types with their friendly names"""
    try:
        from app.services.redratlib import NetBoxTypes
        
        netbox_types = NetBoxTypes.get_all_types()
        
        return jsonify({
            'success': True,
            'netbox_types': [
                {'value': value, 'name': name}
                for value, name in netbox_types
            ]
        })
    except Exception as e:
        logger.error(f"Error getting NetBox types: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Utility function to translate NetBox type in other endpoints
def translate_netbox_type(netbox_type_value):
    """Translate NetBox type value to friendly name"""
    try:
        from app.services.redratlib import NetBoxTypes
        return NetBoxTypes.get_name(netbox_type_value)
    except Exception:
        return f"Unknown Type ({netbox_type_value})"

# RedRat Devices API Endpoints
@app.route('/api/redrat/devices', methods=['GET'])
@login_required(admin_only=True)
def get_redrat_devices(user):
    """
    Get All RedRat Devices
    ---
    tags:
      - RedRat Devices
    summary: Get all RedRat devices
    description: Retrieve a list of all RedRat infrared devices with their status and configuration
    security:
      - SessionAuth: []
    responses:
      200:
        description: List of RedRat devices
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            devices:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  name:
                    type: string
                    example: "Living Room RedRat"
                  ip_address:
                    type: string
                    example: "192.168.1.100"
                  port:
                    type: integer
                    example: 10001
                  description:
                    type: string
                    example: "Main living room IR emitter"
                  is_active:
                    type: boolean
                    example: true
                  last_status:
                    type: string
                    enum: [online, offline, error]
                    example: "online"
                  last_status_check:
                    type: string
                    format: date-time
                    example: "2023-01-01T12:00:00Z"
                  device_model:
                    type: integer
                    example: 12
                  device_ports:
                    type: integer
                    example: 16
                  port_descriptions:
                    type: object
                    description: Optional descriptions for each IR port (port number as key, description as value)
                    additionalProperties:
                      type: string
                    example:
                      "1": "Smart TV (Samsung)"
                      "2": "Soundbar (Yamaha)"
                      "3": "Cable Box"
                      "4": "Blu-ray Player"
                      "5": "Gaming Console"
                      "6": "Streaming Device"
                      "7": "DVD Player"
                      "8": "Security Camera"
                      "9": "Air Conditioner"
                      "10": "Lighting System"
                      "11": "Projector"
                      "12": "Ceiling Fan"
                      "13": "Garage Door"
                      "14": "Window Blinds"
                      "15": "Audio Receiver"
                      "16": "Smart Speaker"
                  netbox_type_name:
                    type: string
                    example: "iRNetBox IV"
                  created_at:
                    type: string
                    format: date-time
                    example: "2023-01-01T10:00:00Z"
      401:
        description: Unauthorized - Admin access required
      500:
        description: Internal server error
    """
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        devices = RedRatDeviceService.get_all_devices()
        
        # Add translated NetBox types to each device
        for device in devices:
            if 'device_model' in device and device['device_model'] is not None:
                device['netbox_type_name'] = translate_netbox_type(device['device_model'])
                logger.debug(f"Device {device.get('name', 'Unknown')}: device_model={device['device_model']}, netbox_type_name={device['netbox_type_name']}")
            else:
                device['netbox_type_name'] = 'Unknown'
                logger.debug(f"Device {device.get('name', 'Unknown')}: No device_model, setting to 'Unknown'")
                
        logger.debug(f"Returning {len(devices)} devices with translated types")
                
        return jsonify({
            'success': True,
            'devices': devices
        })
    except Exception as e:
        logger.error(f"Error getting RedRat devices: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/redrat/devices', methods=['POST'])
@login_required(admin_only=True)
def create_redrat_device(user):
    """
    Create New RedRat Device
    ---
    tags:
      - RedRat Devices
    summary: Create a new RedRat device
    description: Add a new RedRat infrared device to the system
    security:
      - SessionAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: Device name
              example: "Living Room RedRat"
            ip_address:
              type: string
              description: Device IP address
              example: "192.168.1.100"
            port:
              type: integer
              description: Device port (default 10001)
              example: 10001
            description:
              type: string
              description: Device description
              example: "Main living room IR emitter"
            port_descriptions:
              type: object
              description: Optional descriptions for each IR port (port number as key, description as value)
              additionalProperties:
                type: string
              example:
                "1": "Smart TV (Samsung)"
                "2": "Soundbar (Yamaha)"
                "3": "Cable Box"
                "4": "Blu-ray Player"
                "5": "Gaming Console"
                "6": "Streaming Device"
                "7": "DVD Player"
                "8": "Security Camera"
                "9": "Air Conditioner"
                "10": "Lighting System"
                "11": "Projector"
                "12": "Ceiling Fan"
                "13": "Garage Door"
                "14": "Window Blinds"
                "15": "Audio Receiver"
                "16": "Smart Speaker"
          required:
            - name
            - ip_address
    responses:
      200:
        description: Device created successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Device created successfully"
            device_id:
              type: integer
              example: 1
      400:
        description: Bad request - Missing required fields
      401:
        description: Unauthorized - Admin access required
      500:
        description: Internal server error
    """
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('ip_address'):
            return jsonify({'success': False, 'error': 'Name and IP address are required'}), 400
        
        result = RedRatDeviceService.create_device(
            name=data['name'],
            ip_address=data['ip_address'],
            port=data.get('port', 10001),
            description=data.get('description', ''),
            user_id=user['id'],
            port_descriptions=data.get('port_descriptions')
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error creating RedRat device: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/redrat/devices/<int:device_id>', methods=['GET'])
@login_required(admin_only=True)
def get_redrat_device(user, device_id):
    """
    Get RedRat Device Details
    ---
    tags:
      - RedRat Devices
    summary: Get a specific RedRat device
    description: Retrieve detailed information about a specific RedRat device including port descriptions
    security:
      - SessionAuth: []
    parameters:
      - name: device_id
        in: path
        required: true
        type: integer
        description: Device ID
        example: 1
    responses:
      200:
        description: Device details retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            device:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                name:
                  type: string
                  example: "Living Room RedRat"
                ip_address:
                  type: string
                  example: "192.168.1.100"
                port:
                  type: integer
                  example: 10001
                description:
                  type: string
                  example: "Main living room IR emitter"
                is_active:
                  type: boolean
                  example: true
                device_model:
                  type: integer
                  nullable: true
                  example: 3
                device_ports:
                  type: integer
                  nullable: true
                  example: 4
                port_descriptions:
                  type: object
                  description: Descriptions for each IR port (port number as key, description as value)
                  additionalProperties:
                    type: string
                  example:
                    "1": "Smart TV (Samsung)"
                    "2": "Soundbar (Yamaha)"
                    "3": "Cable Box"
                    "4": "Blu-ray Player"
                    "5": "Gaming Console"
                    "6": "Streaming Device"
                    "7": "DVD Player"
                    "8": "Security Camera"
                    "9": "Air Conditioner"
                    "10": "Lighting System"
                    "11": "Projector"
                    "12": "Ceiling Fan"
                    "13": "Garage Door"
                    "14": "Window Blinds"
                    "15": "Audio Receiver"
                    "16": "Smart Speaker"
                netbox_type_name:
                  type: string
                  example: "RedRat3-II"
                last_status:
                  type: string
                  example: "offline"
                last_status_check:
                  type: string
                  nullable: true
                  example: "2025-07-18T10:56:36"
                created_at:
                  type: string
                  example: "2025-07-18T10:56:36"
                updated_at:
                  type: string
                  example: "2025-07-18T10:56:36"
      401:
        description: Unauthorized - Admin access required
      404:
        description: Device not found
      500:
        description: Internal server error
    """
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        device = RedRatDeviceService.get_device(device_id)
        
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
            
        # Add translated NetBox type
        if 'device_model' in device and device['device_model'] is not None:
            device['netbox_type_name'] = translate_netbox_type(device['device_model'])
        else:
            device['netbox_type_name'] = 'Unknown'
            
        return jsonify({
            'success': True,
            'device': device
        })
    except Exception as e:
        logger.error(f"Error getting RedRat device {device_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/redrat/devices/<int:device_id>', methods=['PUT'])
@login_required(admin_only=True)
def update_redrat_device(user, device_id):
    """
    Update RedRat Device
    ---
    tags:
      - RedRat Devices
    summary: Update an existing RedRat device
    description: Update properties of an existing RedRat infrared device
    security:
      - SessionAuth: []
    parameters:
      - name: device_id
        in: path
        required: true
        type: integer
        description: Device ID
        example: 1
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: Device name
              example: "Living Room RedRat"
            ip_address:
              type: string
              description: Device IP address
              example: "192.168.1.100"
            port:
              type: integer
              description: Device port (default 10001)
              example: 10001
            description:
              type: string
              description: Device description
              example: "Main living room IR emitter"
            is_active:
              type: boolean
              description: Whether the device is active
              example: true
            port_descriptions:
              type: object
              description: Optional descriptions for each IR port (port number as key, description as value)
              additionalProperties:
                type: string
              example:
                "1": "Smart TV (Samsung)"
                "2": "Soundbar (Yamaha)"
                "3": "Cable Box"
                "4": "Blu-ray Player"
                "5": "Gaming Console"
                "6": "Streaming Device"
                "7": "DVD Player"
                "8": "Security Camera"
                "9": "Air Conditioner"
                "10": "Lighting System"
                "11": "Projector"
                "12": "Ceiling Fan"
                "13": "Garage Door"
                "14": "Window Blinds"
                "15": "Audio Receiver"
                "16": "Smart Speaker"
          required:
            - name
            - ip_address
    responses:
      200:
        description: Device updated successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Device updated successfully"
      400:
        description: Bad request - Missing required fields
      401:
        description: Unauthorized - Admin access required
      404:
        description: Device not found
      500:
        description: Internal server error
    """
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('ip_address'):
            return jsonify({'success': False, 'error': 'Name and IP address are required'}), 400
        
        result = RedRatDeviceService.update_device(
            device_id=device_id,
            name=data['name'],
            ip_address=data['ip_address'],
            port=data.get('port', 10001),
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
            port_descriptions=data.get('port_descriptions')
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error updating RedRat device {device_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/redrat/devices/<int:device_id>', methods=['DELETE'])
@login_required(admin_only=True)
def delete_redrat_device(user, device_id):
    """Delete a RedRat device"""
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        result = RedRatDeviceService.delete_device(device_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error deleting RedRat device {device_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/redrat/devices/status', methods=['GET'])
@login_required(admin_only=True)
def get_redrat_devices_status(user):
    """
    Get RedRat Devices Status Summary
    ---
    tags:
      - RedRat Devices
    summary: Get status summary of all RedRat devices
    description: Retrieve a summary of device statuses including online, offline, error counts
    security:
      - SessionAuth: []
    responses:
      200:
        description: Device status summary
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            summary:
              type: object
              properties:
                total:
                  type: integer
                  description: Total number of devices
                  example: 5
                online:
                  type: integer
                  description: Number of online devices
                  example: 3
                offline:
                  type: integer
                  description: Number of offline devices
                  example: 1
                error:
                  type: integer
                  description: Number of devices with errors
                  example: 1
                unknown:
                  type: integer
                  description: Number of devices with unknown status
                  example: 0
      401:
        description: Unauthorized - Admin access required
    """
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        status = RedRatDeviceService.get_devices_status()
        
        return jsonify({
            'success': True,
            'summary': status['summary']  # Extract just the summary part
        })
    except Exception as e:
        logger.error(f"Error getting RedRat devices status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/redrat/devices/<int:device_id>/test', methods=['POST'])
@login_required(admin_only=True)
def test_redrat_device(user, device_id):
    """Test connection to a RedRat device"""
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        result = RedRatDeviceService.test_device_connection(device_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing RedRat device {device_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/redrat/devices/<int:device_id>/power-on', methods=['POST'])
@login_required(admin_only=True)
def power_on_redrat_device(user, device_id):
    """Power on a RedRat device"""
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        result = RedRatDeviceService.power_on_device(device_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error powering on RedRat device {device_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/redrat/devices/<int:device_id>/power-off', methods=['POST'])
@login_required(admin_only=True)
def power_off_redrat_device(user, device_id):
    """Power off a RedRat device"""
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        result = RedRatDeviceService.power_off_device(device_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error powering off RedRat device {device_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/redrat/devices/<int:device_id>/reset', methods=['POST'])
@login_required(admin_only=True)
def reset_redrat_device(user, device_id):
    """Reset a RedRat device"""
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        result = RedRatDeviceService.reset_device(device_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error resetting RedRat device {device_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API Key Management Endpoints
@app.route('/api/keys', methods=['GET'])
@login_required(admin_only=True)
def get_api_keys(user):
    """
    Get User API Keys
    ---
    tags:
      - API Keys
    summary: Get all API keys for the current user
    description: Retrieve a list of all API keys belonging to the authenticated user
    security:
      - SessionAuth: []
    responses:
      200:
        description: List of API keys
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            keys:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  name:
                    type: string
                    example: "My API Key"
                  is_active:
                    type: boolean
                    example: true
                  is_expired:
                    type: boolean
                    example: false
                  expires_at:
                    type: string
                    format: date-time
                    example: "2024-01-01T00:00:00Z"
                  created_at:
                    type: string
                    format: date-time
                    example: "2023-01-01T00:00:00Z"
      401:
        description: Unauthorized - Admin access required
    """
    try:
        from app.models.api_key import APIKey
        keys = APIKey.get_by_user(user['id'])
        return jsonify({
            'success': True,
            'keys': [key.to_dict() for key in keys]
        })
    except Exception as e:
        logger.error(f"Error getting API keys: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/keys', methods=['POST'])
@login_required(admin_only=True)
def create_api_key(user):
    """
    Create New API Key
    ---
    tags:
      - API Keys
    summary: Create a new API key
    description: Generate a new API key for the authenticated user
    security:
      - SessionAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: Name for the API key
              example: "My API Key"
            expires_days:
              type: integer
              description: Days until expiration (default 365)
              example: 365
          required:
            - name
    responses:
      200:
        description: API key created successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            key:
              type: string
              description: The generated API key (only shown once)
              example: "rr_abcdef123456789..."
            key_info:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                name:
                  type: string
                  example: "My API Key"
                expires_at:
                  type: string
                  format: date-time
                  example: "2024-01-01T00:00:00Z"
      400:
        description: Bad request - Missing required fields
      401:
        description: Unauthorized - Admin access required
    """
    try:
        from app.models.api_key import APIKey
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        expires_days = int(data.get('expires_days', 365))
        key, api_key = APIKey.create_key(data['name'], user['id'], expires_days)
        
        if not key:
            return jsonify({'success': False, 'error': 'Failed to create API key'}), 500
        
        return jsonify({
            'success': True,
            'key': key,
            'key_info': api_key.to_dict()
        })
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/keys/<int:key_id>', methods=['DELETE'])
@login_required(admin_only=True)
def delete_api_key(user, key_id):
    """
    Delete API Key
    ---
    tags:
      - API Keys
    summary: Delete an API key
    description: Delete an API key belonging to the authenticated user
    security:
      - SessionAuth: []
    parameters:
      - name: key_id
        in: path
        required: true
        type: integer
        description: ID of the API key to delete
    responses:
      200:
        description: API key deleted successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "API key deleted successfully"
      401:
        description: Unauthorized - Admin access required
      404:
        description: API key not found
    """
    try:
        from app.models.api_key import APIKey
        api_key = APIKey.get_by_id(key_id)
        
        if not api_key:
            return jsonify({'success': False, 'error': 'API key not found'}), 404
        
        if api_key.user_id != user['id']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        if api_key.delete():
            return jsonify({'success': True, 'message': 'API key deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete API key'}), 500
    except Exception as e:
        logger.error(f"Error deleting API key: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
@login_required(admin_only=True)
def get_logs(user):
    """
    Get System Logs
    ---
    tags:
      - System
    summary: Get system logs
    description: Retrieve system logs with optional filtering
    security:
      - SessionAuth: []
    parameters:
      - name: level
        in: query
        type: string
        description: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
      - name: limit
        in: query
        type: integer
        description: Maximum number of log entries to return (default 100)
      - name: search
        in: query
        type: string
        description: Search term to filter logs
    responses:
      200:
        description: List of log entries
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            logs:
              type: array
              items:
                type: object
                properties:
                  timestamp:
                    type: string
                    example: "2023-01-01 12:00:00"
                  level:
                    type: string
                    example: "INFO"
                  message:
                    type: string
                    example: "Application started"
      401:
        description: Unauthorized - Admin access required
    """
    try:
        import os
        import re
        from datetime import datetime
        
        # Parameters
        level_filter = request.args.get('level', '').upper()
        limit = int(request.args.get('limit', 100))
        search_term = request.args.get('search', '').lower()
        
        log_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'redrat.log')
        logs = []
        
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r') as f:
                lines = f.readlines()
                
            # Process lines (newest first)
            for line in reversed(lines[-1000:]):  # Get last 1000 lines
                line = line.strip()
                if not line:
                    continue
                    
                # Parse log line (assuming format: TIMESTAMP - LEVEL - MESSAGE)
                # Example: 2023-01-01 12:00:00,123 - INFO - Message here
                match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?)\s*-\s*(\w+)\s*-\s*(.+)$', line)
                if match:
                    timestamp_str, log_level, message = match.groups()
                    
                    # Apply filters
                    if level_filter and log_level != level_filter:
                        continue
                    if search_term and search_term not in message.lower():
                        continue
                    
                    logs.append({
                        'timestamp': timestamp_str,
                        'level': log_level,
                        'message': message
                    })
                    
                    if len(logs) >= limit:
                        break
                else:
                    # If line doesn't match expected format, treat as raw message
                    if not search_term or search_term in line.lower():
                        logs.append({
                            'timestamp': '',
                            'level': 'RAW',
                            'message': line
                        })
                        
                        if len(logs) >= limit:
                            break
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': len(logs)
        })
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Final verification that the Flask app is available
print(f"✅ Final check - Flask app still available: {app}")
print(f"✅ Final check - Flask app type: {type(app)}")
print(f"✅ Final check - Module completed successfully")

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)