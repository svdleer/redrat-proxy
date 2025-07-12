#!/usr/bin/env python3
"""
Database health check script.
This script verifies that all expected tables exist in the database.
"""

import os
import sys
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'host.docker.internal'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'redrat'),
    'password': os.getenv('MYSQL_PASSWORD', 'redratpass'),
    'database': os.getenv('MYSQL_DB', 'redrat_proxy')
}

# Expected tables
EXPECTED_TABLES = [
    'remotes',
    'users',
    'sessions',
    'irdb_files',
    'commands',
    'command_sequences',
    'sequence_commands',
    'scheduled_tasks',
    'command_templates'
]

def check_table_structure(cursor, table_name):
    """Check the structure of a table and return column names"""
    try:
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        print(f"\n--- Structure of {table_name} ---")
        column_names = []
        for col in columns:
            print(f"  Column: {col[0]}, Type: {col[1]}")
            column_names.append(col[0])
        return column_names
    except Exception as e:
        print(f"Error checking table structure for {table_name}: {e}")
        return []

def check_database_health():
    """Check if all expected tables exist in the database"""
    try:
        # Connect to the database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get list of tables in the database
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        # Check if all expected tables exist
        missing_tables = [table for table in EXPECTED_TABLES if table not in tables]
        
        if missing_tables:
            print(f"❌ ERROR: The following tables are missing: {', '.join(missing_tables)}")
            return False
        
        # Check key table structures to make sure they're correct
        critical_tables = ['users', 'sessions', 'remotes']
        for table in critical_tables:
            columns = check_table_structure(cursor, table)
            if table == 'users' and 'username' not in columns:
                print(f"❌ ERROR: Table '{table}' is missing the username column!")
                return False
            elif table == 'sessions' and 'user_id' not in columns:
                print(f"❌ ERROR: Table '{table}' is missing the user_id column!")
                return False
        
        # Check if users table has at least one admin user
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = TRUE")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            print("⚠️ WARNING: No admin users found in the database")
        else:
            print(f"✅ Found {admin_count} admin user(s)")
            
            # Get admin user details
            cursor.execute("SELECT id, username FROM users WHERE is_admin = TRUE")
            admins = cursor.fetchall()
            for admin in admins:
                print(f"  Admin ID: {admin[0]}, Username: {admin[1]}")
        
        # Check foreign key relationships
        print("\nChecking foreign key relationships:")
        try:
            # Test sessions foreign key
            cursor.execute("SELECT COUNT(*) FROM sessions JOIN users ON sessions.user_id = users.id")
            print("✅ sessions -> users relationship is valid")
        except Exception as e:
            print(f"❌ sessions -> users relationship error: {e}")
        
        # Check table row counts
        print("\nTable statistics:")
        for table in EXPECTED_TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ Table '{table}' exists with {count} row(s)")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database health check passed!")
        return True
        
    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print(f"Checking database health for {DB_CONFIG['database']} at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    success = check_database_health()
    if not success:
        sys.exit(1)
