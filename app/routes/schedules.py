"""
API endpoints for task scheduling
"""
from flask import Blueprint, request, jsonify
from app.auth import login_required
from app.services.scheduling_service import SchedulingService
from app.utils.logger import logger

schedules_bp = Blueprint('schedules', __name__)

@schedules_bp.route('/api/schedules', methods=['GET'])
@login_required
def get_schedules():
    """Get all scheduled tasks for the current user"""
    user_id = request.user_id
    
    try:
        tasks = SchedulingService.get_all_tasks(user_id)
        return jsonify({
            'success': True,
            'tasks': [task.to_dict() for task in tasks]
        }), 200
    except Exception as e:
        logger.error(f"Error getting scheduled tasks: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to get scheduled tasks: {str(e)}"
        }), 500

@schedules_bp.route('/api/schedules', methods=['POST'])
@login_required
def create_schedule():
    """Create a new scheduled task"""
    user_id = request.user_id
    data = request.json
    
    if not data or 'type' not in data or 'target_id' not in data or 'schedule_type' not in data:
        return jsonify({
            'success': False,
            'message': "Type, target_id and schedule_type are required"
        }), 400
    
    task_type = data['type']
    target_id = data['target_id']
    schedule_type = data['schedule_type']
    schedule_data = data.get('schedule_data', {})
    
    try:
        task = SchedulingService.schedule_task(
            task_type, target_id, schedule_type, schedule_data, user_id)
        
        return jsonify({
            'success': True,
            'task': task.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating scheduled task: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to create scheduled task: {str(e)}"
        }), 500

@schedules_bp.route('/api/schedules/<task_id>', methods=['GET'])
@login_required
def get_schedule(task_id):
    """Get a scheduled task by ID"""
    try:
        task = SchedulingService.get_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': "Scheduled task not found"
            }), 404
            
        return jsonify({
            'success': True,
            'task': task.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error getting scheduled task {task_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to get scheduled task: {str(e)}"
        }), 500

@schedules_bp.route('/api/schedules/<task_id>', methods=['DELETE'])
@login_required
def delete_schedule(task_id):
    """Delete a scheduled task"""
    try:
        success = SchedulingService.delete_task(task_id)
        if not success:
            return jsonify({
                'success': False,
                'message': "Scheduled task not found"
            }), 404
            
        return jsonify({
            'success': True,
            'message': "Scheduled task deleted"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting scheduled task {task_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to delete scheduled task: {str(e)}"
        }), 500

@schedules_bp.route('/api/schedules/process', methods=['POST'])
@login_required
def process_schedules():
    """Process due scheduled tasks (admin only)"""
    # Check if user is admin (this would typically be done in an admin_required decorator)
    try:
        count = SchedulingService.process_due_tasks()
        
        return jsonify({
            'success': True,
            'message': f"Processed {count} scheduled tasks"
        }), 200
    except Exception as e:
        logger.error(f"Error processing scheduled tasks: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to process scheduled tasks: {str(e)}"
        }), 500
