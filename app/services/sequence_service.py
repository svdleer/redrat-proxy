"""
Command Sequence Service
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.utils.logger import logger

class SequenceService:
    @staticmethod
    def create_sequence(name: str, description: str, user_id: str) -> dict:
        """Create a new command sequence"""
        import uuid
        from datetime import datetime
        
        sequence_id = str(uuid.uuid4())
        created_at = datetime.now()
        
        with get_db() as conn:
            conn.execute("""
                INSERT INTO sequences 
                (name, description, created_by, created_at, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, description, user_id, created_at, 'pending'))
            
            # Get the auto-generated ID
            sequence_id = conn.lastrowid
            conn.commit()
            
        sequence = {
            'id': sequence_id,
            'name': name,
            'description': description,
            'created_by': user_id,
            'created_at': created_at,
            'commands': []
        }
            
        logger.info(f"Sequence created: {name} by user {user_id}")
        return sequence
    
    @staticmethod
    def get_sequence(sequence_id: str) -> Optional[dict]:
        """Get a command sequence by ID"""
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM sequences WHERE id = %s
            """, (sequence_id,))
            sequence_row = cursor.fetchone()
            
            if not sequence_row:
                return None
                
            # Create basic sequence object
            sequence = {
                'id': sequence_row['id'],
                'name': sequence_row['name'],
                'description': sequence_row.get('description', ''),
                'commands': []
            }
            
            # Get sequence commands - no join needed, data is in sequence_commands table
            cursor.execute("""
                SELECT sc.id, sc.command, sc.device, sc.remote_id, sc.position, 
                       sc.delay_ms, sc.ir_port, sc.power
                FROM sequence_commands sc
                WHERE sc.sequence_id = %s
                ORDER BY sc.position
            """, (sequence_id,))
            
            command_rows = cursor.fetchall()
            
            for row in command_rows:
                sequence['commands'].append({
                    'id': row['id'],
                    'command': row['command'],
                    'device': row['device'],
                    'remote_id': row['remote_id'],
                    'position': row['position'],
                    'delay_ms': row['delay_ms'],
                    'ir_port': row['ir_port'],
                    'power': row['power']
                })
                
        return sequence
    
    @staticmethod
    def get_all_sequences(user_id: Optional[str] = None) -> List[dict]:
        """Get all command sequences, optionally filtered by user"""
        sequences = []
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            if user_id:
                cursor.execute("""
                    SELECT * FROM sequences WHERE created_by = %s
                    ORDER BY created_at DESC
                """, (user_id,))
            else:
                cursor.execute("SELECT * FROM sequences ORDER BY created_at DESC")
                
            sequence_rows = cursor.fetchall()
            
            for row in sequence_rows:
                sequences.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row.get('description', ''),
                    'created_by': row['created_by'],
                    'created_at': row['created_at'],
                    'status': row.get('status', 'pending')
                })
                
        return sequences
    
    @staticmethod
    def add_command_to_sequence(sequence_id: str, command_id: str, position: int = None, delay_ms: int = 0) -> dict:
        """Add a command to a sequence"""
        sequence = SequenceService.get_sequence(sequence_id)
        if not sequence:
            raise ValueError(f"Sequence {sequence_id} not found")
            
        # If position is not provided, add to the end
        if position is None:
            position = len(sequence['commands']) + 1
        
        # Create new sequence command
        command_uuid = str(uuid.uuid4())
        now = datetime.datetime.now()
        
        with get_db() as conn:
            # If position is specified, shift existing commands
            if position <= len(sequence['commands']):
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
            """, (command_uuid, sequence_id, command_id, position, delay_ms, now))
            conn.commit()
            
        logger.info(f"Command {command_id} added to sequence {sequence_id} at position {position}")
        return {
            'id': command_uuid,
            'sequence_id': sequence_id,
            'command_id': command_id,
            'position': position,
            'delay_ms': delay_ms,
            'created_at': now
        }
    
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
    def execute_sequence(sequence_id: str) -> bool:
        """Execute a command sequence by adding it to the command queue"""
        sequence = SequenceService.get_sequence(sequence_id)
        if not sequence:
            raise ValueError(f"Sequence {sequence_id} not found")
            
        # Add sequence to command queue for execution
        try:
            from app.services.command_queue import add_sequence
            
            # Convert sequence format for command queue
            sequence_data = {
                'id': sequence_id,
                'name': sequence['name'],
                'commands': sequence['commands']
            }
            
            result = add_sequence(sequence_data)
            if result:
                logger.info(f"Sequence {sequence_id} queued for execution with {len(sequence['commands'])} commands")
                return True
            else:
                logger.error(f"Failed to queue sequence {sequence_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error queuing sequence {sequence_id}: {str(e)}")
            return False
