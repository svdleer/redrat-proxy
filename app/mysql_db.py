import mysql.connector
from mysql.connector import pooling
import os
from contextlib import contextmanager

class MySQLDatabase:
    def __init__(self):
        self.config = {
            'host': os.getenv('MYSQL_HOST', 'db'),
            'port': os.getenv('MYSQL_PORT', '3306'),
            'database': os.getenv('MYSQL_DB', 'redrat_proxy'),
            'user': os.getenv('MYSQL_USER', 'redrat'),
            'password': os.getenv('MYSQL_PASSWORD', 'securepassword'),
            'pool_name': 'redrat_pool',
            'pool_size': 5,
            'pool_reset_session': True
        }
        self._create_pool()

    def _create_pool(self):
        try:
            self.connection_pool = pooling.MySQLConnectionPool(**self.config)
        except Exception as e:
            print("Error creating connection pool:", e)
            raise

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = self.connection_pool.get_connection()
            yield conn
        except Exception as e:
            print("Database error:", e)
            raise
        finally:
            if conn:
                conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS remotes (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    api_key VARCHAR(255) UNIQUE NOT NULL,
                    image_path VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS irdb_files (
                    id VARCHAR(36) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    filepath VARCHAR(255) NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

# Singleton instance
db = MySQLDatabase()