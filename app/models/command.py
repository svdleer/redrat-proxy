import uuid
from app.database import get_db
from app.utils.logger import logger
from datetime import datetime
from typing import Dict, Any

class Command:
    def __init__(self, id=None, remote_id=None, name=None, command_data=None, created_at=None, status=None):
        self.id = id or str(uuid.uuid4())
        self.remote_id = remote_id
        self.name = name
        self.command_data = command_data
        self.created_at = created_at or datetime.now()
        self.status = status or 'created'  # created, queued, executing, completed, failed
        self.remote_name = None  # Will be populated when needed
    
    @classmethod
    def from_db_row(cls, row):
        """Create a Command from a database row"""
        if not row:
            return None
        
        return cls(
            id=row['id'],
            remote_id=row['remote_id'],
            name=row['name'],
            command_data=row['command_data'],
            created_at=row['created_at'],
            status=row.get('status', 'created')
        )
    
    def to_dict(self):
        """Convert to a dictionary for API responses"""
        return {
            'id': self.id,
            'remote_id': self.remote_id,
            'name': self.name,
            'command_data': self.command_data,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'status': self.status,
            'remote_name': self.remote_name
        }
    
    def save(self):
        """Save the command to the database"""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO commands 
                (id, remote_id, name, command_data, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                remote_id = VALUES(remote_id),
                name = VALUES(name),
                command_data = VALUES(command_data)
            """, (self.id, self.remote_id, self.name, self.command_data, self.created_at))
            conn.commit()
        logger.info(f"Command saved: {self.name} for remote {self.remote_id}")
        return self.id
    
    @staticmethod
    def log_command(remote_id, command_name, device_name=None):
        """Log a command execution (backward compatibility method)"""
        cmd = Command(
            remote_id=remote_id,
            name=command_name,
            command_data=f"Command for {device_name}" if device_name else ""
        )
        cmd.status = 'queued'
        cmd.save()
        logger.info(f"Command queued: {command_name} for device {device_name}")
        return cmd.id