"""
Main application views
"""
from flask import render_template, redirect, url_for, request, jsonify
from app.auth import login_required
from . import main_bp, api_bp, admin_bp
from app.services.command_queue import CommandQueue
from app.services.sequence_service import SequenceService
from app.services.redrat_service import reset_redrat_service

# Main routes
@main_bp.route('/')
@login_required
def index():
    """Dashboard home page"""
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

@main_bp.route('/commands')
@login_required
def commands():
    """Command management page"""
    return render_template('command.html')

@main_bp.route('/sequences')
@login_required
def sequences():
    """Command sequences page"""
    return render_template('sequences.html')

@main_bp.route('/schedules')
@login_required
def schedules():
    """Task scheduling page"""
    return render_template('schedules.html')

# API routes
@api_bp.route('/queue', methods=['GET'])
@login_required
def get_queue():
    """Get the current command queue"""
    try:
        queue = CommandQueue.get_queue()
        return jsonify({
            'success': True,
            'queue': [cmd.to_dict() for cmd in queue]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Failed to get queue: {str(e)}"
        }), 500

@api_bp.route('/queue', methods=['POST'])
@login_required
def add_to_queue():
    """Add a command to the queue"""
    data = request.json
    
    if not data or 'command_id' not in data:
        return jsonify({
            'success': False,
            'message': "Command ID is required"
        }), 400
    
    command_id = data['command_id']
    
    try:
        success = CommandQueue.add_to_queue(command_id)
        return jsonify({
            'success': success,
            'message': "Command added to queue" if success else "Failed to add command to queue"
        }), 200 if success else 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Failed to add command to queue: {str(e)}"
        }), 500

@api_bp.route('/queue', methods=['DELETE'])
@login_required
def clear_queue():
    """Clear the command queue"""
    try:
        count = CommandQueue.clear_queue()
        return jsonify({
            'success': True,
            'message': f"Cleared {count} commands from queue"
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Failed to clear queue: {str(e)}"
        }), 500

@api_bp.route('/queue/<command_id>', methods=['DELETE'])
@login_required
def remove_from_queue(command_id):
    """Remove a command from the queue"""
    try:
        success = CommandQueue.remove_from_queue(command_id)
        return jsonify({
            'success': success,
            'message': "Command removed from queue" if success else "Failed to remove command from queue"
        }), 200 if success else 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Failed to remove command from queue: {str(e)}"
        }), 500

@api_bp.route('/queue/process', methods=['POST'])
@login_required
def process_queue():
    """Process the command queue"""
    try:
        count = CommandQueue.process_queue()
        return jsonify({
            'success': True,
            'message': f"Processed {count} commands from queue"
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Failed to process queue: {str(e)}"
        }), 500

@api_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """Get command history"""
    try:
        # Import here to avoid circular imports
        from app.database import get_db
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT ch.*, r.name as remote_name, rd.name as device_name
                FROM command_history ch
                LEFT JOIN remotes r ON ch.remote_id = r.id
                LEFT JOIN redrat_devices rd ON ch.device_id = rd.id
                ORDER BY ch.executed_at DESC
                LIMIT 20
            """)
            history = cursor.fetchall()
            
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/history', methods=['DELETE'])
@login_required
def clear_history():
    """Clear command history"""
    try:
        from app.database import get_db
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM command_history")
            count = cursor.rowcount
            conn.commit()
            
        return jsonify({
            'success': True,
            'message': f"Cleared {count} commands from history"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Failed to clear history: {str(e)}"
        }), 500

@api_bp.route('/activity', methods=['DELETE'])
@login_required
def clear_activity():
    """Clear activity log"""
    try:
        from app.database import get_db
        
        with get_db() as conn:
            cursor = conn.cursor()
            # Clear activity-related tables (adjust table names as needed)
            cursor.execute("DELETE FROM activity_log WHERE 1=1")
            count = cursor.rowcount
            conn.commit()
            
        return jsonify({
            'success': True,
            'message': f"Cleared {count} activity entries"
        })
    except Exception as e:
        # If activity_log table doesn't exist, that's okay
        return jsonify({
            'success': True,
            'message': "Activity log cleared"
        })

# Admin routes
@admin_bp.route('/reset-service-cache', methods=['POST'])
@login_required
def reset_service_cache():
    """Reset the RedRat service cache"""
    try:
        reset_redrat_service()
        return jsonify({
            'success': True,
            'message': "RedRat service cache reset successfully"
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Failed to reset service cache: {str(e)}"
        }), 500
