"""
Command Sequence Service
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.utils.logger import logger
from app.models.sequence import CommandSequence, SequenceCommand
from app.models.command import Command

class SequenceService:
    @staticmethod
    def create_sequence(name: str, description: str, user_id: str) -> CommandSequence:
        """Create a new command sequence"""
        sequence = CommandSequence(
            name=name,
            description=description,
            created_by=user_id
        )
        
        with get_db() as conn:
            conn.execute("""
                INSERT INTO command_sequences 
                (id, name, description, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (sequence.id, sequence.name, sequence.description, 
                  sequence.created_by, sequence.created_at))
            conn.commit()
            
        logger.info(f"Sequence created: {name} by user {user_id}")
        return sequence
    
    @staticmethod
    def get_sequence(sequence_id: str) -> Optional[CommandSequence]:
        """Get a command sequence by ID"""
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM command_sequences WHERE id = %s
            """, (sequence_id,))
            sequence_row = cursor.fetchone()
            
            if not sequence_row:
                return None
                
            sequence = CommandSequence.from_db_row(sequence_row)
            
            # Get sequence commands
            cursor.execute("""
                SELECT sc.*, c.name as command_name, c.command_data, c.remote_id 
                FROM sequence_commands sc
                JOIN commands c ON sc.command_id = c.id
                WHERE sc.sequence_id = %s
                ORDER BY sc.position
            """, (sequence_id,))
            
            command_rows = cursor.fetchall()
            
            for row in command_rows:
                seq_cmd = SequenceCommand.from_db_row(row)
                seq_cmd.command = Command(
                    id=row['command_id'],
                    name=row['command_name'],
                    remote_id=row['remote_id'],
                    command_data=row['command_data']
                )
                sequence.commands.append(seq_cmd)
                
        return sequence
    
    @staticmethod
    def get_all_sequences(user_id: Optional[str] = None) -> List[CommandSequence]:
        """Get all command sequences, optionally filtered by user"""
        sequences = []
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            if user_id:
                cursor.execute("""
                    SELECT * FROM command_sequences WHERE created_by = %s
                """, (user_id,))
            else:
                cursor.execute("SELECT * FROM command_sequences")
                
            sequence_rows = cursor.fetchall()
            
            for row in sequence_rows:
                sequences.append(CommandSequence.from_db_row(row))
                
        return sequences
    
    @staticmethod
    def add_command_to_sequence(sequence_id: str, command_id: str, position: int = None, delay_ms: int = 0) -> SequenceCommand:
        """Add a command to a sequence"""
        sequence = SequenceService.get_sequence(sequence_id)
        if not sequence:
            raise ValueError(f"Sequence {sequence_id} not found")
            
        # If position is not provided, add to the end
        if position is None:
            position = len(sequence.commands) + 1
            
        seq_cmd = SequenceCommand(
            sequence_id=sequence_id,
            command_id=command_id,
            position=position,
            delay_ms=delay_ms
        )
        
        with get_db() as conn:
            # If position is specified, shift existing commands
            if position <= len(sequence.commands):
                conn.execute("""
                    UPDATE sequence_commands 
                    SET position = position + 1
                    WHERE sequence_id = %s AND position >= %s
                """, (sequence_id, position))
            
            # Insert the new command
            conn.execute("""
                INSERT INTO sequence_commands
                (id, sequence_id, command_id, position, delay_ms, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (seq_cmd.id, seq_cmd.sequence_id, seq_cmd.command_id,
                  seq_cmd.position, seq_cmd.delay_ms, seq_cmd.created_at))
            conn.commit()
            
        logger.info(f"Command {command_id} added to sequence {sequence_id} at position {position}")
        return seq_cmd
    
    @staticmethod
    def remove_command_from_sequence(sequence_id: str, seq_command_id: str) -> bool:
        """Remove a command from a sequence"""
        with get_db() as conn:
            # Get the position of the command being removed
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT position FROM sequence_commands
                WHERE id = %s AND sequence_id = %s
            """, (seq_command_id, sequence_id))
            
            row = cursor.fetchone()
            if not row:
                return False
                
            position = row['position']
            
            # Delete the command
            conn.execute("""
                DELETE FROM sequence_commands
                WHERE id = %s AND sequence_id = %s
            """, (seq_command_id, sequence_id))
            
            # Reorder remaining commands
            conn.execute("""
                UPDATE sequence_commands
                SET position = position - 1
                WHERE sequence_id = %s AND position > %s
            """, (sequence_id, position))
            
            conn.commit()
            
        logger.info(f"Command {seq_command_id} removed from sequence {sequence_id}")
        return True
    
    @staticmethod
    def execute_sequence(sequence_id: str) -> List[str]:
        """Execute a command sequence and return the IDs of the queued commands"""
        sequence = SequenceService.get_sequence(sequence_id)
        if not sequence:
            raise ValueError(f"Sequence {sequence_id} not found")
            
        command_ids = []
        
        for seq_cmd in sequence.commands:
            # For now, we'll just log commands - in a real implementation,
            # we'd send them to the appropriate execution service
            cmd = seq_cmd.command
            cmd_id = cmd.id if cmd else seq_cmd.command_id
            
            # Log command with status 'queued'
            with get_db() as conn:
                conn.execute("""
                    UPDATE commands
                    SET status = 'queued'
                    WHERE id = %s
                """, (cmd_id,))
                conn.commit()
            
            command_ids.append(cmd_id)
            logger.info(f"Command {cmd_id} queued from sequence {sequence_id}, delay: {seq_cmd.delay_ms}ms")
            
        return command_ids
