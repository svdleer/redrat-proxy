"""
API endpoints for command sequences
"""
from flask import Blueprint, request, jsonify
from app.auth import login_required
from app.services.sequence_service import SequenceService
from app.utils.logger import logger

sequences_bp = Blueprint('sequences', __name__)

@sequences_bp.route('/api/sequences', methods=['GET'])
@login_required
def get_sequences():
    """Get all command sequences for the current user"""
    user_id = request.user_id
    
    try:
        sequences = SequenceService.get_all_sequences(user_id)
        return jsonify({
            'success': True,
            'sequences': [seq.to_dict() for seq in sequences]
        }), 200
    except Exception as e:
        logger.error(f"Error getting sequences: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to get sequences: {str(e)}"
        }), 500

@sequences_bp.route('/api/sequences', methods=['POST'])
@login_required
def create_sequence():
    """Create a new command sequence"""
    user_id = request.user_id
    data = request.json
    
    if not data or 'name' not in data:
        return jsonify({
            'success': False,
            'message': "Name is required"
        }), 400
    
    name = data['name']
    description = data.get('description', '')
    
    try:
        sequence = SequenceService.create_sequence(name, description, user_id)
        return jsonify({
            'success': True,
            'sequence': sequence.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"Error creating sequence: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to create sequence: {str(e)}"
        }), 500

@sequences_bp.route('/api/sequences/<sequence_id>', methods=['GET'])
@login_required
def get_sequence(sequence_id):
    """Get a command sequence by ID"""
    try:
        sequence = SequenceService.get_sequence(sequence_id)
        if not sequence:
            return jsonify({
                'success': False,
                'message': "Sequence not found"
            }), 404
            
        return jsonify({
            'success': True,
            'sequence': sequence.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error getting sequence {sequence_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to get sequence: {str(e)}"
        }), 500

@sequences_bp.route('/api/sequences/<sequence_id>/commands', methods=['POST'])
@login_required
def add_command(sequence_id):
    """Add a command to a sequence"""
    data = request.json
    
    if not data or 'command_id' not in data:
        return jsonify({
            'success': False,
            'message': "Command ID is required"
        }), 400
    
    command_id = data['command_id']
    position = data.get('position')  # Optional
    delay_ms = data.get('delay_ms', 0)
    
    try:
        seq_cmd = SequenceService.add_command_to_sequence(
            sequence_id, command_id, position, delay_ms)
        
        return jsonify({
            'success': True,
            'sequence_command': seq_cmd.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error adding command to sequence {sequence_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to add command: {str(e)}"
        }), 500

@sequences_bp.route('/api/sequences/<sequence_id>/commands/<command_id>', methods=['DELETE'])
@login_required
def remove_command(sequence_id, command_id):
    """Remove a command from a sequence"""
    try:
        success = SequenceService.remove_command_from_sequence(sequence_id, command_id)
        if not success:
            return jsonify({
                'success': False,
                'message': "Command not found in sequence"
            }), 404
            
        return jsonify({
            'success': True,
            'message': "Command removed from sequence"
        }), 200
    except Exception as e:
        logger.error(f"Error removing command {command_id} from sequence {sequence_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to remove command: {str(e)}"
        }), 500

@sequences_bp.route('/api/sequences/<sequence_id>/execute', methods=['POST'])
@login_required
def execute_sequence(sequence_id):
    """Execute a command sequence"""
    try:
        command_ids = SequenceService.execute_sequence(sequence_id)
        
        return jsonify({
            'success': True,
            'message': f"Sequence execution started with {len(command_ids)} commands",
            'command_ids': command_ids
        }), 200
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error executing sequence {sequence_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to execute sequence: {str(e)}"
        }), 500
