import mysql.connector.pooling
import os
from contextlib import contextmanager
from app.config import Config
from app.utils.logger import logger

class MySQLDatabase:
    def __init__(self):
        self.config = {
            'host': Config.MYSQL_HOST,
            'port': Config.MYSQL_PORT,
            'database': Config.MYSQL_DB,
            'user': Config.MYSQL_USER,
            'password': Config.MYSQL_PASSWORD,
            'pool_name': 'redrat_pool',
            'pool_size': 5,
            'auth_plugin': 'mysql_native_password'  # Important for host MySQL
        }
        self._create_pool()

    def _create_pool(self):
        try:
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(**self.config)
            logger.info("MySQL connection pool created successfully")
        except Exception as e:
            logger.error(f"Error creating MySQL connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            conn = self.connection_pool.get_connection()
            yield conn
        except mysql.connector.Error as e:
            logger.error(f"MySQL error: {e}")
            raise
        finally:
            if conn:
                conn.close()

# Singleton instance
db = MySQLDatabase()

@contextmanager
def get_db():
    """Convenience function to get a database connection with cursor"""
    with db.get_connection() as conn:
        yield conn