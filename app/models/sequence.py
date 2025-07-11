"""
Command Sequence Model
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any

class SequenceCommand:
    def __init__(self, id=None, sequence_id=None, command_id=None, position=0, delay_ms=0, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.sequence_id = sequence_id
        self.command_id = command_id
        self.position = position
        self.delay_ms = delay_ms
        self.created_at = created_at or datetime.now()
        self.command = None  # Will be populated from the command table

    @classmethod
    def from_db_row(cls, row):
        """Create a SequenceCommand from a database row"""
        if not row:
            return None
        
        return cls(
            id=row['id'],
            sequence_id=row['sequence_id'],
            command_id=row['command_id'],
            position=row['position'],
            delay_ms=row['delay_ms'],
            created_at=row['created_at']
        )
    
    def to_dict(self):
        """Convert to a dictionary for API responses"""
        return {
            'id': self.id,
            'sequence_id': self.sequence_id,
            'command_id': self.command_id,
            'position': self.position,
            'delay_ms': self.delay_ms,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'command': self.command.to_dict() if self.command else None
        }


class CommandSequence:
    def __init__(self, id=None, name=None, description=None, created_by=None, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
        self.commands: List[SequenceCommand] = []

    @classmethod
    def from_db_row(cls, row):
        """Create a CommandSequence from a database row"""
        if not row:
            return None
        
        return cls(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            created_by=row['created_by'],
            created_at=row['created_at']
        )
    
    def to_dict(self):
        """Convert to a dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'commands': [cmd.to_dict() for cmd in self.commands]
        }
    
    def add_command(self, command_id, delay_ms=0):
        """Add a command to the sequence"""
        position = len(self.commands) + 1
        seq_cmd = SequenceCommand(
            sequence_id=self.id,
            command_id=command_id,
            position=position,
            delay_ms=delay_ms
        )
        self.commands.append(seq_cmd)
        return seq_cmd
    
    def reorder_commands(self):
        """Ensure commands are in proper order"""
        self.commands.sort(key=lambda cmd: cmd.position)
        for i, cmd in enumerate(self.commands):
            cmd.position = i + 1
