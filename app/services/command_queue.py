import queue
import threading
from app.utils.logger import logger
from app.database import get_db

command_queue = queue.Queue()
lock = threading.Lock()

def process_queue():
    while True:
        try:
            cmd = command_queue.get()
            with lock:
                execute_command(cmd)
        except Exception as e:
            logger.error(f"Command failed: {e}")
        finally:
            command_queue.task_done()

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