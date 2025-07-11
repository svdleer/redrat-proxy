#!/usr/bin/env python3
"""
Database diagnostic tool for RedRat Proxy
This script performs comprehensive checks on your database setup and fixes common issues
"""

import os
import sys
import bcrypt
import mysql.connector
from mysql.connector import Error
import uuid
from datetime import datetime, timedelta

# Database configuration from environment or defaults
DB_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ.get('MYSQL_USER', 'redrat'),
    'password': os.environ.get('MYSQL_PASSWORD', 'redratpass'),
    'database': os.environ.get('MYSQL_DB', 'redrat_proxy')
}

def hash_password(password):
    """Generate a new bcrypt password hash"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def test_connection(config=None, no_db=False):
    """Test database connection with optional configuration"""
    if config is None:
        config = DB_CONFIG.copy()
    
    # Remove database from config if no_db is True
    if no_db and 'database' in config:
        config.pop('database')
    
    print(f"\n[1] Testing connection to MySQL at {config['host']}:{config['port']}...")
    
    try:
        conn = mysql.connector.connect(**config)
        if conn.is_connected():
            print(f"✅ Successfully connected to MySQL")
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"   MySQL version: {version[0]}")
            cursor.close()
            return conn
        else:
            print("❌ Connection test failed - could not connect")
            return None
    except Error as e:
        print(f"❌ Connection error: {e}")
        return None

def create_database(conn):
    """Create database if it doesn't exist"""
    db_name = DB_CONFIG['database']
    print(f"\n[2] Checking if database '{db_name}' exists...")
    
    try:
        cursor = conn.cursor()
        
        # Try to create the database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"✅ Database '{db_name}' exists or was created")
        
        # Use the database
        cursor.execute(f"USE {db_name}")
        print(f"   Now using database '{db_name}'")
        
        cursor.close()
        return True
    except Error as e:
        print(f"❌ Error creating/using database: {e}")
        return False

def check_tables(conn):
    """Check if all required tables exist and have correct structure"""
    print("\n[3] Checking database tables...")
    
    required_tables = [
        'users', 'remotes', 'sessions', 'irdb_files', 'commands',
        'command_sequences', 'sequence_commands', 'scheduled_tasks',
        'command_templates'
    ]
    
    try:
        cursor = conn.cursor()
        
        # Get list of existing tables
        cursor.execute("SHOW TABLES")
        existing_tables = [t[0] for t in cursor.fetchall()]
        
        # Check each required table
        missing_tables = []
        for table in required_tables:
            if table in existing_tables:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' is missing")
                missing_tables.append(table)
        
        cursor.close()
        return missing_tables
    except Error as e:
        print(f"❌ Error checking tables: {e}")
        return required_tables  # Assume all tables are missing

def validate_admin_user(conn):
    """Check if admin user exists and has correct credentials"""
    print("\n[4] Validating admin user...")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Check if admin user exists
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        
        if not admin:
            print("❌ Admin user not found")
            return False
        
        print(f"✅ Admin user exists (ID: {admin['id']})")
        
        # Check password hash
        hash_format_valid = admin['password_hash'].startswith('$2b$') or admin['password_hash'].startswith('$2a$')
        if hash_format_valid:
            print("✅ Password hash has valid bcrypt format")
        else:
            print(f"❌ Password hash has invalid format: {admin['password_hash'][:10]}...")
            return False
            
        cursor.close()
        return True
    except Error as e:
        print(f"❌ Error validating admin user: {e}")
        return False

def create_admin_user(conn):
    """Create or update admin user"""
    print("\n[5] Creating/updating admin user...")
    
    try:
        cursor = conn.cursor()
        
        # Standard admin password
        admin_password = 'admin123'
        password_hash = hash_password(admin_password)
        
        # Try to update existing admin user
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE username = 'admin'",
            (password_hash,)
        )
        
        if cursor.rowcount > 0:
            print(f"✅ Updated admin user password to '{admin_password}'")
        else:
            # No admin user, create one
            admin_id = 'admin-' + str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO users (id, username, password_hash, is_admin) VALUES (%s, %s, %s, %s)",
                (admin_id, 'admin', password_hash, True)
            )
            print(f"✅ Created new admin user with password '{admin_password}'")
        
        conn.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"❌ Error creating/updating admin user: {e}")
        return False

def create_missing_tables(conn, missing_tables):
    """Create missing tables from schema"""
    if not missing_tables:
        return True
        
    print(f"\n[6] Creating {len(missing_tables)} missing tables...")
    
    # Try to read schema file
    schema_file = 'mysql_schema.sql'
    if not os.path.exists(schema_file):
        print(f"❌ Schema file '{schema_file}' not found")
        return False
    
    try:
        with open(schema_file, 'r') as f:
            schema = f.read()
            
        # Extract CREATE TABLE statements for missing tables
        cursor = conn.cursor()
        created_tables = []
        
        for table in missing_tables:
            # Simple pattern matching to extract CREATE TABLE statements
            # This is a basic implementation - a proper parser would be better
            create_pattern = f"CREATE TABLE IF NOT EXISTS {table} ("
            if create_pattern in schema:
                start_idx = schema.find(create_pattern)
                end_idx = schema.find(");", start_idx) + 2
                
                if start_idx >= 0 and end_idx > start_idx:
                    create_stmt = schema[start_idx:end_idx]
                    try:
                        cursor.execute(create_stmt)
                        print(f"✅ Created table '{table}'")
                        created_tables.append(table)
                    except Error as e:
                        print(f"❌ Error creating table '{table}': {e}")
            else:
                print(f"❌ Could not find CREATE statement for '{table}'")
        
        conn.commit()
        cursor.close()
        
        # Return True if all tables were created
        return len(created_tables) == len(missing_tables)
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def create_test_session(conn):
    """Create a test session for the admin user"""
    print("\n[7] Creating a test session for admin...")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get admin user ID
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        
        if not admin:
            print("❌ Admin user not found")
            return False
            
        admin_id = admin['id']
        
        # Delete any existing test sessions
        cursor.execute("DELETE FROM sessions WHERE session_id = 'test-session'")
        
        # Create a new session
        expires_at = datetime.now() + timedelta(days=7)
        cursor.execute(
            "INSERT INTO sessions (session_id, user_id, expires_at) VALUES (%s, %s, %s)",
            ('test-session', admin_id, expires_at)
        )
        
        conn.commit()
        print("✅ Created test session for admin user")
        
        cursor.close()
        return True
    except Error as e:
        print(f"❌ Error creating test session: {e}")
        return False

def test_authentication(conn):
    """Test authentication with the admin user"""
    print("\n[8] Testing authentication with admin credentials...")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get admin user
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        
        if not admin:
            print("❌ Admin user not found")
            return False
            
        # Test password
        test_password = 'admin123'
        try:
            password_hash = admin['password_hash']
            result = bcrypt.checkpw(test_password.encode('utf-8'), password_hash.encode('utf-8'))
            
            if result:
                print(f"✅ Authentication successful with password '{test_password}'")
            else:
                print(f"❌ Authentication failed with password '{test_password}'")
                print("   Hash in database:", password_hash)
                
                # Try creating a new hash and compare them
                new_hash = hash_password(test_password)
                print(f"   Newly generated hash: {new_hash}")
                return False
        except Exception as e:
            print(f"❌ Error testing password: {e}")
            return False
            
        cursor.close()
        return result
    except Error as e:
        print(f"❌ Error testing authentication: {e}")
        return False

def recreate_database():
    """Completely recreate the database from scratch"""
    print("\n=== RECREATING DATABASE FROM SCRATCH ===")
    
    # First connect without specifying database
    conn = test_connection(no_db=True)
    if not conn:
        return False
        
    db_name = DB_CONFIG['database']
    cursor = conn.cursor()
    
    try:
        # Drop database if it exists
        print(f"Dropping database '{db_name}' if it exists...")
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        
        # Create database
        print(f"Creating database '{db_name}'...")
        cursor.execute(f"CREATE DATABASE {db_name}")
        
        # Switch to the database
        cursor.execute(f"USE {db_name}")
        
        # Read and execute full schema
        schema_file = 'mysql_schema.sql'
        if not os.path.exists(schema_file):
            print(f"❌ Schema file '{schema_file}' not found")
            return False
            
        with open(schema_file, 'r') as f:
            schema_lines = f.readlines()
        
        # Skip first two lines (CREATE DATABASE and USE statements)
        schema_script = ''.join(schema_lines[2:])
        
        # Execute schema
        print("Executing schema script...")
        for statement in schema_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
                
        conn.commit()
        print("✅ Database recreated successfully!")
        
        # Validate admin user
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count > 0:
            print("✅ Admin user created successfully")
        else:
            print("❌ Failed to create admin user")
            return False
            
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"❌ Error recreating database: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("=== RedRat Proxy Database Diagnostic ===")
    print("Current database configuration:")
    for key, value in DB_CONFIG.items():
        if key != 'password':
            print(f"  - {key}: {value}")
        else:
            print(f"  - {key}: {'*' * len(str(value))}")  # Hide password
    
    # Step 1: Test basic connection (no database)
    conn = test_connection(no_db=True)
    if not conn:
        print("\nCould not connect to MySQL server. Please check:")
        print("1. MySQL is running and accessible")
        print("2. User credentials are correct")
        print("3. Host and port are correct")
        sys.exit(1)
        
    # Step 2: Create/verify database
    if not create_database(conn):
        print("\nFailed to create or use database. Options:")
        print("1. Check MySQL user permissions")
        print("2. Try recreating the database from scratch")
        recreate = input("\nWould you like to recreate the database from scratch? [y/N]: ")
        if recreate.lower() == 'y':
            if recreate_database():
                print("\n✅ Database recreated successfully. Please try logging in again.")
                sys.exit(0)
            else:
                print("\n❌ Failed to recreate database.")
                sys.exit(1)
        sys.exit(1)
        
    # Step 3: Check tables
    missing_tables = check_tables(conn)
    
    # Step 4: Create missing tables if needed
    if missing_tables:
        print(f"\nFound {len(missing_tables)} missing tables.")
        if not create_missing_tables(conn, missing_tables):
            print("\nFailed to create all missing tables. Options:")
            print("1. Check MySQL user permissions")
            print("2. Try recreating the database from scratch")
            recreate = input("\nWould you like to recreate the database from scratch? [y/N]: ")
            if recreate.lower() == 'y':
                if recreate_database():
                    print("\n✅ Database recreated successfully. Please try logging in again.")
                    sys.exit(0)
                else:
                    print("\n❌ Failed to recreate database.")
                    sys.exit(1)
    
    # Step 5: Validate admin user
    admin_valid = validate_admin_user(conn)
    
    # Step 6: Create/update admin user if needed
    if not admin_valid:
        if not create_admin_user(conn):
            print("\nFailed to create/update admin user.")
            sys.exit(1)
    
    # Step 7: Test authentication
    if not test_authentication(conn):
        print("\nFailed authentication test. Updating admin password...")
        if not create_admin_user(conn):
            print("❌ Failed to update admin password.")
            sys.exit(1)
            
    # Step 8: Create test session
    create_test_session(conn)
    
    # Close connection
    conn.close()
    
    print("\n=== Diagnostic Complete ===")
    print("\nYou should now be able to log in with:")
    print("Username: admin")
    print("Password: admin123")
    print("\nIf login still fails, please check:")
    print("1. Browser cookies/cache (try clearing them)")
    print("2. Web server logs for API errors")
    print("3. Docker container logs for database connection issues")

if __name__ == "__main__":
    main()
