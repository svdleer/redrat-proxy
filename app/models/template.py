"""
Command Template Model
"""
import uuid
import json
from datetime import datetime
from typing import Dict, Any

class CommandTemplate:
    def __init__(self, id=None, irdb_id=None, name=None, template_data=None, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.irdb_id = irdb_id
        self.name = name
        self.template_data = template_data or {}
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def from_db_row(cls, row):
        """Create a CommandTemplate from a database row"""
        if not row:
            return None
            
        # Parse JSON from the database
        template_data = json.loads(row['template_data']) if isinstance(row['template_data'], str) else row['template_data']
        
        return cls(
            id=row['id'],
            irdb_id=row['irdb_id'],
            name=row['name'],
            template_data=template_data,
            created_at=row['created_at']
        )
    
    def to_dict(self):
        """Convert to a dictionary for API responses"""
        return {
            'id': self.id,
            'irdb_id': self.irdb_id,
            'name': self.name,
            'template_data': self.template_data,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }
    
    def generate_command(self, remote_id, command_name=None):
        """Generate a command from this template"""
        from app.models.command import Command
        
        command = Command(
            remote_id=remote_id,
            name=command_name or self.name,
            command_data=self.template_data.get('signal_data', '')
        )
        
        return command
