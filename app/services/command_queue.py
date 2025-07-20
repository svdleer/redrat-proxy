import queue
import threading
import logging
import time
from typing import Dict, Any, Optional

# Set up logger if app.utils.logger is not available
try:
    from app.utils.logger import logger
except ImportError:
    logger = logging.getLogger("redrat")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

# Import the enhanced RedRat service
try:
    from app.services.redrat_service import create_redrat_service
    from app.services.redrat_device_service import RedRatDeviceService
except ImportError:
    logger.warning("RedRat service not available")
    create_redrat_service = lambda host, port: None
    RedRatDeviceService = None

# Use get_db if available, otherwise just pass
try:
    from app.mysql_db import db
except ImportError:
    class MockDB:
        def get_connection(self):
            return None
    db = MockDB()

class CommandQueue:
    """Enhanced command queue with RedRat hardware integration."""
    
    def __init__(self):
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.running = False
        self.worker_thread = None
        
    def start(self):
        """Start the command queue worker thread."""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
            logger.info("Command queue worker started")
        
    def stop(self):
        """Stop the command queue worker thread."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
            logger.info("Command queue worker stopped")
        
    def add_command(self, command: Dict[str, Any]) -> bool:
        """Add command to queue for processing.
        
        Args:
            command: Command dictionary with required fields
            
        Returns:
            True if command was added to queue
        """
        try:
            # Validate required fields
            required_fields = ['id', 'remote_id', 'command', 'device']
            if not all(field in command for field in required_fields):
                logger.error(f"Command missing required fields: {command}")
                return False
                
            self.queue.put(command)
            logger.info(f"Command {command['id']} added to queue")
            return True
            
        except Exception as e:
            logger.error(f"Error adding command to queue: {str(e)}")
            return False
            
    def add_sequence(self, sequence: Dict[str, Any]) -> bool:
        """Add sequence to queue for processing.
        
        Args:
            sequence: Sequence dictionary with commands
            
        Returns:
            True if sequence was added to queue
        """
        try:
            # Validate sequence structure
            if 'id' not in sequence or 'commands' not in sequence:
                logger.error(f"Sequence missing required fields: {sequence}")
                return False
                
            # Add sequence as special command type
            sequence_command = {
                'type': 'sequence',
                'sequence_id': sequence['id'],
                'commands': sequence['commands']
            }
            
            self.queue.put(sequence_command)
            logger.info(f"Sequence {sequence['id']} added to queue")
            return True
            
        except Exception as e:
            logger.error(f"Error adding sequence to queue: {str(e)}")
            return False
        
    def _process_queue(self):
        """Process commands in the queue."""
        logger.info("Command queue processing started")
        
        while self.running:
            try:
                # Get command from queue with timeout
                command = self.queue.get(timeout=1)
                
                with self.lock:
                    if command.get('type') == 'sequence':
                        self._execute_sequence(command)
                    else:
                        self._execute_command(command)
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing command queue: {str(e)}")
            finally:
                try:
                    self.queue.task_done()
                except:
                    pass
                    
        logger.info("Command queue processing stopped")
                
    def _execute_command(self, command):
        """Execute a single command using RedRat service.
        
        Args:
            command: Command dictionary
        """
        try:
            logger.info(f"Executing command {command['id']}: {command['command']}")
            
            # Get RedRat device from database
            if not RedRatDeviceService:
                logger.error("RedRat service not available")
                self._update_command_status(command['id'], 'failed', 
                                          'RedRat service not configured')
                return
            
            # Get the RedRat device information
            device_info = self._get_redrat_device_for_command(command)
            if not device_info:
                logger.error(f"No RedRat device found for command {command['id']}")
                self._update_command_status(command['id'], 'failed', 
                                          'No RedRat device available')
                return
            
            # Create RedRat service instance for this device
            redrat_service = create_redrat_service(device_info['ip_address'], device_info['port'])
            if not redrat_service:
                logger.error(f"Failed to create RedRat service for {device_info['ip_address']}:{device_info['port']}")
                self._update_command_status(command['id'], 'failed', 
                                          'Failed to connect to RedRat device')
                return
            
            # Execute command
            result = redrat_service.send_command(
                command['id'],
                command['remote_id'],
                command['command'],
                command.get('ir_port', 1),
                command.get('power', 50)
            )
            
            if result['success']:
                logger.info(f"Command {command['id']} executed successfully")
            else:
                logger.error(f"Command {command['id']} failed: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error executing command {command['id']}: {str(e)}")
            self._update_command_status(command['id'], 'failed', str(e))
            
    def _execute_sequence(self, sequence_command: Dict[str, Any]):
        """Execute a sequence of commands using RedRat service.
        
        Args:
            sequence_command: Sequence command dictionary
        """
        try:
            sequence_id = sequence_command['sequence_id']
            commands = sequence_command['commands']
            
            logger.info(f"Executing sequence {sequence_id} with {len(commands)} commands")
            
            # Get RedRat device from database for sequence
            if not RedRatDeviceService:
                logger.error("RedRat service not available")
                return
            
            # Get the RedRat device information for the sequence
            device_info = self._get_redrat_device_for_sequence(sequence_id)
            if not device_info:
                logger.error(f"No RedRat device found for sequence {sequence_id}")
                return
            
            # Create RedRat service instance for this device
            redrat_service = create_redrat_service(device_info['ip_address'], device_info['port'])
            if not redrat_service:
                logger.error(f"Failed to create RedRat service for {device_info['ip_address']}:{device_info['port']}")
                return
            
            # Execute sequence
            result = redrat_service.send_sequence(sequence_id, commands)
            
            if result['success']:
                logger.info(f"Sequence {sequence_id} executed successfully")
            else:
                logger.error(f"Sequence {sequence_id} failed: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error executing sequence {sequence_command['sequence_id']}: {str(e)}")
    
    def _get_redrat_device_for_command(self, command):
        """Get RedRat device information for a command."""
        try:
            # For now, get the first active RedRat device from database
            # In the future, this could be based on command routing or device assignment
            devices = RedRatDeviceService.get_all_devices()
            active_devices = [d for d in devices if d.get('is_active', False)]
            
            if active_devices:
                return active_devices[0]  # Return first active device
            
            logger.warning("No active RedRat devices found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting RedRat device for command: {str(e)}")
            return None
    
    def _get_redrat_device_for_sequence(self, sequence_id):
        """Get RedRat device information for a sequence."""
        try:
            # For now, get the first active RedRat device from database
            # In the future, this could be based on sequence routing or device assignment
            devices = RedRatDeviceService.get_all_devices()
            active_devices = [d for d in devices if d.get('is_active', False)]
            
            if active_devices:
                return active_devices[0]  # Return first active device
            
            logger.warning("No active RedRat devices found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting RedRat device for sequence: {str(e)}")
            return None
            
    def _update_command_status(self, command_id: int, status: str, error_message: str = None):
        """Update command status in database.
        
        Args:
            command_id: Database ID of the command
            status: New status ('executed', 'failed', 'pending')
            error_message: Error message if failed
        """
        try:
            with db.get_connection() as conn:
                if not conn:
                    return
                    
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE commands 
                    SET status = %s, executed_at = CURRENT_TIMESTAMP, 
                        status_updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (status, command_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating command status: {str(e)}")


# Create global command queue instance
command_queue_instance = CommandQueue()

# Start the queue automatically
command_queue_instance.start()

# Legacy compatibility functions
def add_command(cmd: Dict[str, Any]) -> bool:
    """Add command to the global command queue (legacy compatibility)."""
    return command_queue_instance.add_command(cmd)

def add_sequence(seq: Dict[str, Any]) -> bool:
    """Add sequence to the global command queue."""
    return command_queue_instance.add_sequence(seq)

# Export the queue for backwards compatibility
command_queue = command_queue_instance.queue
lock = command_queue_instance.lock

def process_queue():
    """Process the global command queue for backwards compatibility."""
    # This is now handled by the worker thread
    pass

def execute_command(cmd):
    """Execute command for backwards compatibility."""
    return command_queue_instance._execute_command(cmd)