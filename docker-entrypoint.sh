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
import uuid

def check_table_structure(cursor, table_name):
    """Check the structure of a table"""
    try:
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        print(f"\n--- Structure of {table_name} ---")
        column_names = []
        for col in columns:
            print(f"Column: {col[0]}, Type: {col[1]}")
            column_names.append(col[0])
        return column_names
    except Exception as e:
        print(f"Error checking table structure: {e}")
        return []

def recreate_all_tables(cursor):
    """Drop and recreate all tables in the correct order"""
    try:
        print("\n*** RECREATING ALL TABLES ***")
        
        # First drop all tables in reverse dependency order
        print("Dropping existing tables...")
        tables_to_drop = [
            "sessions", "command_templates", "scheduled_tasks", 
            "sequence_commands", "command_sequences", "commands",
            "remote_files", "users", "remotes"
        ]
        
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"✓ Dropped {table}")
            except Exception as e:
                print(f"✗ Error dropping {table}: {e}")
        
        # Create tables in the correct order
        print("\nCreating tables...")
        
        # Create remotes table
        cursor.execute("""
        CREATE TABLE remotes (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            api_key VARCHAR(255) UNIQUE NOT NULL,
            image_path VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("✓ Created remotes table")
        
        # Create users table
        cursor.execute("""
        CREATE TABLE users (
            id VARCHAR(36) PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("✓ Created users table")
        
        # Create sessions table
        cursor.execute("""
        CREATE TABLE sessions (
            session_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        print("✓ Created sessions table")
        
        # Create remote_files table
        cursor.execute("""
        CREATE TABLE remote_files (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            filepath VARCHAR(255),
            device_type VARCHAR(255),
            manufacturer VARCHAR(255),
            uploaded_by VARCHAR(36) NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        print("✓ Created remote_files table")
        
        # Create commands table
        cursor.execute("""
        CREATE TABLE commands (
            id VARCHAR(36) PRIMARY KEY,
            remote_id VARCHAR(36) NOT NULL,
            name VARCHAR(255) NOT NULL,
            command_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (remote_id) REFERENCES remotes(id) ON DELETE CASCADE
        )
        """)
        print("✓ Created commands table")
        
        # Create command_sequences table
        cursor.execute("""
        CREATE TABLE command_sequences (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_by VARCHAR(36) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        print("✓ Created command_sequences table")
        
        # Create sequence_commands table
        cursor.execute("""
        CREATE TABLE sequence_commands (
            id VARCHAR(36) PRIMARY KEY,
            sequence_id VARCHAR(36) NOT NULL,
            command_id VARCHAR(36) NOT NULL,
            position INT NOT NULL,
            delay_ms INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sequence_id) REFERENCES command_sequences(id) ON DELETE CASCADE,
            FOREIGN KEY (command_id) REFERENCES commands(id) ON DELETE CASCADE
        )
        """)
        print("✓ Created sequence_commands table")
        
        # Create scheduled_tasks table
        cursor.execute("""
        CREATE TABLE scheduled_tasks (
            id VARCHAR(36) PRIMARY KEY,
            type ENUM('command', 'sequence') NOT NULL,
            target_id VARCHAR(36) NOT NULL,
            schedule_type ENUM('once', 'daily', 'weekly', 'monthly') NOT NULL,
            schedule_data JSON NOT NULL,
            next_run DATETIME NOT NULL,
            created_by VARCHAR(36) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        print("✓ Created scheduled_tasks table")
        
        # Create command_templates table
        cursor.execute("""
        CREATE TABLE command_templates (
            id VARCHAR(36) PRIMARY KEY,
            file_id VARCHAR(36) NOT NULL,
            name VARCHAR(255) NOT NULL,
            device_type VARCHAR(255),
            template_data JSON NOT NULL,
            created_by VARCHAR(36) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES remote_files(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        print("✓ Created command_templates table")
        
        # Insert default admin user
        cursor.execute("""
        INSERT INTO users (id, username, password_hash, is_admin)
        VALUES ('admin-id', 'admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', TRUE)
        """)
        print("✓ Added default admin user")
        
        # Insert sample remote for testing
        cursor.execute("""
        INSERT INTO remotes (id, name, api_key, image_path)
        VALUES (%s, 'Sample TV Remote', %s, 'remote_images/sample_remote.png')
        """, (str(uuid.uuid4()), str(uuid.uuid4())))
        print("✓ Added sample remote")
        
        return True
    except Exception as e:
        print(f"Error recreating tables: {e}")
        return False

def fix_tables(cursor, existing_tables):
    """Fix specific issues with tables"""
    # Check if users table exists but has wrong schema
    if "users" in existing_tables:
        columns = check_table_structure(cursor, "users")
        if "username" not in columns:
            print("\n!!! The users table exists but is missing the username column !!!")
            return recreate_all_tables(cursor)
    
    # Check if sessions table exists but has foreign key issues
    if "sessions" in existing_tables:
        try:
            cursor.execute("SELECT * FROM sessions LIMIT 1")
        except mysql.connector.Error as e:
            if "foreign key constraint fails" in str(e).lower():
                print("\n!!! The sessions table has foreign key issues !!!")
                return recreate_all_tables(cursor)
    
    return False

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
        
        # First check if tables exist
        cursor.execute("SHOW TABLES")
        existing_tables = [t[0] for t in cursor.fetchall()]
        print(f"Existing tables: {', '.join(existing_tables) if existing_tables else 'none'}")
        
        # Try to fix tables if they exist but have issues
        if existing_tables:
            fixed = fix_tables(cursor, existing_tables)
            if fixed:
                print("✓ Fixed table issues")
        
        # If no tables exist, create them all from scratch
        if not existing_tables:
            print("\nNo tables found, creating from scratch...")
            recreate_all_tables(cursor)
        
        # Verify users table has the right structure
        print("\nVerifying users table structure:")
        user_columns = check_table_structure(cursor, "users")
        if "username" not in user_columns:
            print("❌ users table still missing username column, recreating all tables...")
            recreate_all_tables(cursor)
        
        # Verify admin user exists
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
            admin_count = cursor.fetchone()[0]
            print(f"\nAdmin users found: {admin_count}")
            
            # Add admin if none exists
            if admin_count == 0:
                print("No admin user found, adding default admin...")
                cursor.execute("""
                INSERT INTO users (id, username, password_hash, is_admin)
                VALUES ('admin-id', 'admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', TRUE)
                """)
                print("✓ Added default admin user")
        except Exception as e:
            print(f"Error checking admin user: {e}")
            print("Recreating all tables...")
            recreate_all_tables(cursor)
        
        # Final verification of all tables
        cursor.execute("SHOW TABLES")
        final_tables = [t[0] for t in cursor.fetchall()]
        expected_tables = ['remotes', 'users', 'sessions', 'remote_files', 'commands',
                           'command_sequences', 'sequence_commands', 'scheduled_tasks', 'command_templates']
        
        missing_tables = [t for t in expected_tables if t not in final_tables]
        if missing_tables:
            print(f"\n❌ Still missing tables: {', '.join(missing_tables)}")
            print("Attempting one final recreation of all tables...")
            recreate_all_tables(cursor)
        else:
            print("\n✓ All tables exist!")
        
        # Final check
        cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
        admin_count = cursor.fetchone()[0]
        if admin_count > 0:
            print("✓ Admin user exists")
        else:
            print("❌ Admin user still missing!")
        
        cursor.close()
        conn.close()
        print("\nDatabase initialization completed!")
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

# Create required directories
mkdir -p /app/app/static/remote_files
mkdir -p /app/app/static/images/remotes

echo "Starting the application..."
exec "$@"
