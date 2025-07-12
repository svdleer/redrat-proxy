#!/usr/bin/env python3
"""
Test database connection and login for RedRat Proxy
"""
import os
import bcrypt
import mysql.connector
from mysql.connector import Error

def test_db_connection():
    """Test connection to MySQL database"""
    try:
        conn = mysql.connector.connect(
            host=os.environ.get('MYSQL_HOST', 'localhost'),
            user=os.environ.get('MYSQL_USER', 'redrat'),
            password=os.environ.get('MYSQL_PASSWORD', 'redratpass'),
            database=os.environ.get('MYSQL_DB', 'redrat_proxy')
        )
        
        if conn.is_connected():
            print("✅ Successfully connected to MySQL database")
            return conn
        
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

def check_admin_user(conn):
    """Check if admin user exists and verify its password hash structure"""
    if not conn:
        return
        
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        
        if not admin:
            print("❌ Admin user not found in database")
            print("   Run reset_admin_password.py to create the admin user")
            return
            
        print(f"✅ Found admin user (ID: {admin['id']})")
        
        # Check password hash structure
        password_hash = admin['password_hash']
        if password_hash.startswith('$2b$') or password_hash.startswith('$2a$'):
            print("✅ Password hash has valid bcrypt format")
            
            # Verify if default password works
            test_password = 'admin123'
            try:
                if bcrypt.checkpw(test_password.encode('utf-8'), password_hash.encode('utf-8')):
                    print(f"✅ Default password '{test_password}' is valid for admin user")
                else:
                    print(f"❌ Default password '{test_password}' is NOT valid")
                    print("   Run reset_admin_password.py to reset the admin password")
            except Exception as e:
                print(f"❌ Error checking password: {e}")
                print("   Password hash might be corrupted, run reset_admin_password.py")
        else:
            print(f"❌ Password hash has invalid format: {password_hash[:10]}...")
            print("   Run reset_admin_password.py to fix the hash")
            
    except Error as e:
        print(f"❌ Error querying admin user: {e}")

def check_tables(conn):
    """Check if all required tables exist and have proper structure"""
    required_tables = [
        'users', 'remotes', 'sessions', 'commands', 'irdb_files',
        'command_sequences', 'sequence_commands', 'command_templates',
        'scheduled_tasks'
    ]
    
    if not conn:
        return
        
    try:
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SHOW TABLES")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        print("\n=== Database Tables ===")
        for table in required_tables:
            if table in existing_tables:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' is missing")
                
    except Error as e:
        print(f"❌ Error checking tables: {e}")

def main():
    print("=== RedRat Proxy Login Diagnostic ===\n")
    
    # Check database connection
    conn = test_db_connection()
    if conn:
        # Check admin user
        check_admin_user(conn)
        
        # Check database tables
        check_tables(conn)
        
        # Close connection
        conn.close()
        print("\nDiagnostic completed.")
    
    print("\nTo fix login issues:")
    print("1. Ensure the MySQL server is running and accessible")
    print("2. Run reset_admin_password.py to reset or create admin user")
    print("3. Check the browser console for any JavaScript errors")
    print("4. Clear browser cookies and cache, then try again")

if __name__ == "__main__":
    main()
