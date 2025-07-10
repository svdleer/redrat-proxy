from app.database import get_db
from app.utils.logger import logger
from datetime import datetime

class Command:
    @staticmethod
    def log_command(remote_id, command_name, device_name):
        cmd_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute("""
                INSERT INTO commands 
                (id, remote_id, command_name, device_name, status)
                VALUES (%s, %s, %s, %s, 'queued')
            """, (cmd_id, remote_id, command_name, device_name))
            conn.commit()
        logger.info(f"Command queued: {command_name} for {device_name}")
        return cmd_id