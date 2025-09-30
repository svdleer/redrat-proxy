from app.database import get_db
from app.utils.logger import logger
import uuid

class Remote:
    @staticmethod
    def create(name, description=None):
        api_key = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute("""
                INSERT INTO remotes 
                (name, api_key, description) 
                VALUES (%s, %s, %s)
            """, (name, api_key, description))
            conn.commit()
        logger.info(f"Created remote: {name}")
        return api_key

    @staticmethod
    def list_all():
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT r.*, COUNT(c.id) as command_count 
                FROM remotes r
                LEFT JOIN commands c ON r.id = c.remote_id
                GROUP BY r.id
            """)
            return cursor.fetchall()