#!/bin/bash
set -e

# Activate virtual environment
source /app/venv/bin/activate

# Print Python version and location
echo "Using Python: $(which python)"
python --version

# Print Flask version
echo "Flask version: $(pip show flask | grep Version)"

# Wait for host's MySQL to be ready
echo "Waiting for MySQL on host.docker.internal to be ready..."
MAX_RETRIES=30
RETRY_INTERVAL=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python - <<EOF
import mysql.connector
import os
import sys
try:
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'host.docker.internal'),
        user=os.getenv('MYSQL_USER', 'redrat'),
        password=os.getenv('MYSQL_PASSWORD', 'redratpass'),
        port=int(os.getenv('MYSQL_PORT', '3306'))
    )
    conn.close()
    print("MySQL connection successful!")
    sys.exit(0)
except Exception as e:
    print(f"MySQL connection failed: {e}")
    sys.exit(1)
EOF
    then
        echo "MySQL on host is ready!"
        break
    else
        echo "Waiting for MySQL on host... Retry $((RETRY_COUNT+1))/$MAX_RETRIES"
        RETRY_COUNT=$((RETRY_COUNT+1))
        sleep $RETRY_INTERVAL
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Failed to connect to MySQL after $MAX_RETRIES retries. Exiting..."
    exit 1
fi

# Initialize database schema
echo "Initializing database schema..."
python - <<EOF
import mysql.connector
import os
import sys
import time

def create_database():
    try:
        # First connect without specifying database to create it if needed
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'host.docker.internal'),
            user=os.getenv('MYSQL_USER', 'redrat'),
            password=os.getenv('MYSQL_PASSWORD', 'redratpass'),
            port=int(os.getenv('MYSQL_PORT', '3306'))
        )
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        db_name = os.getenv('MYSQL_DB', 'redrat_proxy')
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Database '{db_name}' created or already exists")
        
        # Use the database
        cursor.execute(f"USE {db_name}")
        
        # Read schema file
        with open('/app/mysql_schema.sql', 'r') as f:
            sql_file = f.read()
            # Remove CREATE DATABASE and USE statements from the schema
            lines = []
            for line in sql_file.split('\n'):
                if not line.strip().lower().startswith('create database') and not line.strip().lower().startswith('use'):
                    lines.append(line)
            
            # Join all non-skipped lines back together
            modified_sql = '\n'.join(lines)
            
            # Split SQL file into separate statements
            sql_statements = modified_sql.split(';')
            
            # Execute each statement
            for statement in sql_statements:
                if statement.strip():  # Skip empty statements
                    try:
                        print(f"Executing: {statement[:50]}...")
                        cursor.execute(statement)
                        conn.commit()
                    except Exception as stmt_err:
                        print(f"Error executing statement: {stmt_err}")
                        # Continue with next statement rather than failing completely
                        # This allows tables that already exist to be skipped
        
        cursor.close()
        conn.close()
        print("Database initialization completed successfully!")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

# Try to initialize database
for attempt in range(3):
    if create_database():
        break
    else:
        print(f"Retrying database initialization (attempt {attempt+1}/3)...")
        time.sleep(5)
else:
    print("Failed to initialize database after 3 attempts")
    sys.exit(1)
EOF

# Test application database connection
echo "Testing application database connection..."
python - <<EOF
import os
import sys
import mysql.connector

try:
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'host.docker.internal'),
        user=os.getenv('MYSQL_USER', 'redrat'),
        password=os.getenv('MYSQL_PASSWORD', 'redratpass'),
        database=os.getenv('MYSQL_DB', 'redrat_proxy'),
        port=int(os.getenv('MYSQL_PORT', '3306'))
    )
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"Found {len(tables)} tables in the database:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Test by checking if users table exists
    cursor.execute("SHOW TABLES LIKE 'users'")
    users_table_exists = cursor.fetchone() is not None
    
    if users_table_exists:
        # Check for admin user
        cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
        count = cursor.fetchone()[0]
        if count > 0:
            print("✅ Database is properly initialized with admin user")
        else:
            print("⚠️ Admin user not found in database")
    else:
        print("❌ Users table not found in database")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Failed to connect to application database: {e}")
    sys.exit(1)
EOF

echo "Starting the application..."
exec "$@"
