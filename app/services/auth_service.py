from app.models.user import User
from app.utils.logger import logger
import bcrypt

class AuthService:
    @staticmethod
    def authenticate(username, password):
        user = User.get_by_username(username)
        if not user:
            logger.warning(f"Failed login attempt for non-existent user: {username}")
            return None
            
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            logger.warning(f"Failed login attempt for user: {username}")
            return None
            
        logger.info(f"User logged in: {username}")
        return user

    @staticmethod
    def create_user(username, password, is_admin=False):
        if User.get_by_username(username):
            logger.error(f"User already exists: {username}")
            return False
            
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        User.create(username, password_hash, is_admin)
        logger.info(f"User created: {username}")
        return True