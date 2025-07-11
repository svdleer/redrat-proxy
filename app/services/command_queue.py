import queue
import threading
import logging

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

# Use get_db if available, otherwise just pass
try:
    from app.database import get_db
except ImportError:
    def get_db():
        return None

class CommandQueue:
    """Class for managing command queues"""
    
    def __init__(self):
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        
    def add_command(self, cmd):
        """Add command to queue"""
        self.queue.put(cmd)
        return True
        
    def process_queue(self):
        """Process commands in the queue"""
        while True:
            try:
                cmd = self.queue.get()
                with self.lock:
                    self.execute_command(cmd)
            except Exception as e:
                logger.error(f"Command failed: {e}")
            finally:
                self.queue.task_done()
                
    def execute_command(self, cmd):
        """Execute a command"""
        db = get_db()
        if db:
            try:
                # Implement RedRat command execution
                logger.info(f"Executing command: {cmd}")
                # Update command status in DB if db is available
                with db() as conn:
                    conn.execute("""
                        UPDATE command_log 
                        SET status = 'executed'
                        WHERE id = %s
                    """, (cmd['id'],))
            except Exception as e:
                logger.error(f"Failed to execute command: {e}")
        else:
            # Just log if no database is available
            logger.info(f"Would execute command: {cmd}")

# Create global command queue instance for backwards compatibility
command_queue_instance = CommandQueue()
command_queue = command_queue_instance.queue
lock = command_queue_instance.lock

def process_queue():
    """Process the global command queue for backwards compatibility"""
    command_queue_instance.process_queue()

def execute_command(cmd):
    with get_db() as conn:
        try:
            # Implement RedRat command execution
            logger.info(f"Executing command: {cmd}")
            # Update command status in DB
            conn.execute("""
                UPDATE command_log 
                SET status = 'executed'
                WHERE id = %s
            """, (cmd['id'],))
            conn.commit()
        except Exception as e:
            logger.error(f"Command execution error: {e}")

# Start worker thread
threading.Thread(target=process_queue, daemon=True).start()