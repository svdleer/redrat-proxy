import mysql.connector
from mysql.connector import pooling
import os
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
            print("✅ MySQL connection pool created successfully")
        except Exception as e:
            print(f"❌ Error creating connection pool: {e}")
            print("⚠️  Application will start without database connection")
            print("🔧 Please fix MySQL permissions and restart the application")
            self.connection_pool = None

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

    def init_db(self, force_recreate=False):
        """Initialize the database with tables from mysql_schema.sql"""
        # Read the SQL schema
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schema_path = os.path.join(script_dir, 'mysql_schema.sql')
        
        try:
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
        except Exception as e:
            print(f"Error reading schema file: {e}")
            return
        
        # Split the SQL into individual statements
        statements = schema_sql.split(';')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Skip the CREATE DATABASE and USE statements
            for statement in statements[2:]:
                if statement.strip():
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        print(f"Error executing SQL: {e}")
                        print(f"Statement: {statement}")
            
            conn.commit()
            print("Database initialized successfully")

# Singleton instance
db = MySQLDatabase()