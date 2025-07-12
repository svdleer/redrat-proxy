"""
Template Service
"""
import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.utils.logger import logger
from app.models.template import CommandTemplate

class TemplateService:
    @staticmethod
    def create_template(irdb_id: str, name: str, template_data: Dict[str, Any]) -> CommandTemplate:
        """Create a new command template from IRDB data"""
        template = CommandTemplate(
            irdb_id=irdb_id,
            name=name,
            template_data=template_data
        )
        
        with get_db() as conn:
            conn.execute("""
                INSERT INTO command_templates
                (id, irdb_id, name, template_data, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (template.id, template.irdb_id, template.name, 
                  json.dumps(template.template_data), template.created_at))
            conn.commit()
            
        logger.info(f"Template created: {name} from IRDB {irdb_id}")
        return template
    
    @staticmethod
    def get_template(template_id: str) -> Optional[CommandTemplate]:
        """Get a command template by ID"""
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM command_templates WHERE id = %s
            """, (template_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return CommandTemplate.from_db_row(row)
    
    @staticmethod
    def get_templates_by_irdb(irdb_id: str) -> List[CommandTemplate]:
        """Get all templates for an IRDB file"""
        templates = []
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM command_templates
                WHERE irdb_id = %s
            """, (irdb_id,))
            
            rows = cursor.fetchall()
            
            for row in rows:
                templates.append(CommandTemplate.from_db_row(row))
                
        return templates
    
    @staticmethod
    def extract_templates_from_irdb(irdb_id: str, irdb_file_path: str) -> List[CommandTemplate]:
        """Extract command templates from an IRDB file"""
        # This is a placeholder - in a real implementation, you'd need to
        # parse the IRDB file format and extract signal patterns
        
        # For now, we'll create a dummy template
        template_data = {
            "signal_type": "infrared",
            "protocol": "NEC",
            "signal_data": "SAMPLE_PATTERN_DATA"
        }
        
        template = TemplateService.create_template(
            irdb_id=irdb_id,
            name=f"Template from {os.path.basename(irdb_file_path)}",
            template_data=template_data
        )
        
        return [template]
    
    @staticmethod
    def delete_template(template_id: str) -> bool:
        """Delete a command template"""
        with get_db() as conn:
            conn.execute("""
                DELETE FROM command_templates
                WHERE id = %s
            """, (template_id,))
            conn.commit()
            
        logger.info(f"Template {template_id} deleted")
        return True
