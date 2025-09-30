from app.database import get_db
from app.utils.logger import logger
import uuid
from datetime import datetime

class User:
    @staticmethod
    def create(username, password_hash, is_admin=False):
        user_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute("""
                INSERT INTO users (id, username, password_hash, is_admin)
                VALUES (%s, %s, %s, %s)
            """, (user_id, username, password_hash, is_admin))
            conn.commit()
        logger.info(f"Created user: {username}")
        return user_id

    @staticmethod
    def get_by_username(username):
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()