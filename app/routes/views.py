"""
Main application views
"""
from flask import render_template, redirect, url_for, request, jsonify
from app.auth import login_required
from . import main_bp, api_bp, admin_bp
from app.services.command_queue import CommandQueue
from app.services.sequence_service import SequenceService

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
    """Get command execution history"""
    limit = request.args.get('limit', 50, type=int)
    
    try:
        history = CommandQueue.get_command_history(limit)
        return jsonify({
            'success': True,
            'history': [cmd.to_dict() for cmd in history]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Failed to get history: {str(e)}"
        }), 500
