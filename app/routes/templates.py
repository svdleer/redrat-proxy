"""
API endpoints for command templates
"""
from flask import Blueprint, request, jsonify
from app.auth import login_required
from app.services.template_service import TemplateService
from app.utils.logger import logger

templates_bp = Blueprint('templates', __name__)

@templates_bp.route('/api/templates', methods=['GET'])
@login_required
def get_templates():
    """Get templates by IRDB ID"""
    irdb_id = request.args.get('irdb_id')
    
    if not irdb_id:
        return jsonify({
            'success': False,
            'message': "IRDB ID is required"
        }), 400
    
    try:
        templates = TemplateService.get_templates_by_irdb(irdb_id)
        return jsonify({
            'success': True,
            'templates': [template.to_dict() for template in templates]
        }), 200
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to get templates: {str(e)}"
        }), 500

@templates_bp.route('/api/templates', methods=['POST'])
@login_required
def create_template():
    """Create a new command template"""
    data = request.json
    
    if not data or 'irdb_id' not in data or 'name' not in data or 'template_data' not in data:
        return jsonify({
            'success': False,
            'message': "IRDB ID, name and template_data are required"
        }), 400
    
    irdb_id = data['irdb_id']
    name = data['name']
    template_data = data['template_data']
    
    try:
        template = TemplateService.create_template(irdb_id, name, template_data)
        return jsonify({
            'success': True,
            'template': template.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to create template: {str(e)}"
        }), 500

@templates_bp.route('/api/templates/<template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    """Get a command template by ID"""
    try:
        template = TemplateService.get_template(template_id)
        if not template:
            return jsonify({
                'success': False,
                'message': "Template not found"
            }), 404
            
        return jsonify({
            'success': True,
            'template': template.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to get template: {str(e)}"
        }), 500

@templates_bp.route('/api/templates/<template_id>/generate', methods=['POST'])
@login_required
def generate_command(template_id):
    """Generate a command from a template"""
    data = request.json
    
    if not data or 'remote_id' not in data:
        return jsonify({
            'success': False,
            'message': "Remote ID is required"
        }), 400
    
    remote_id = data['remote_id']
    command_name = data.get('name')
    
    try:
        template = TemplateService.get_template(template_id)
        if not template:
            return jsonify({
                'success': False,
                'message': "Template not found"
            }), 404
            
        command = template.generate_command(remote_id, command_name)
        command.save()
        
        return jsonify({
            'success': True,
            'command': command.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"Error generating command from template {template_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to generate command: {str(e)}"
        }), 500

@templates_bp.route('/api/templates/<template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    """Delete a command template"""
    try:
        success = TemplateService.delete_template(template_id)
        if not success:
            return jsonify({
                'success': False,
                'message': "Template not found"
            }), 404
            
        return jsonify({
            'success': True,
            'message': "Template deleted"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to delete template: {str(e)}"
        }), 500

@templates_bp.route('/api/irdb/<irdb_id>/extract-templates', methods=['POST'])
@login_required
def extract_templates(irdb_id):
    """Extract templates from an IRDB file"""
    try:
        # First get the IRDB file path
        from app.models.irdb import IRDBFile
        from app.database import get_db
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM irdb_files WHERE id = %s", (irdb_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({
                    'success': False,
                    'message': "IRDB file not found"
                }), 404
            
            irdb_file = IRDBFile.from_db_row(row)
            
            # Extract templates
            templates = TemplateService.extract_templates_from_irdb(irdb_id, irdb_file.filepath)
            
            return jsonify({
                'success': True,
                'message': f"Extracted {len(templates)} templates",
                'templates': [template.to_dict() for template in templates]
            }), 200
    except Exception as e:
        logger.error(f"Error extracting templates from IRDB {irdb_id}: {e}")
        return jsonify({
            'success': False,
            'message': f"Failed to extract templates: {str(e)}"
        }), 500
