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
    'host': os.getenv('MYSQL_HOST', 'localhost'),
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
        
        # Check if users table has at least one admin user
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = TRUE")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            print("⚠️ WARNING: No admin users found in the database")
        else:
            print(f"✅ Found {admin_count} admin user(s)")
        
        # Check table row counts
        for table in EXPECTED_TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ Table '{table}' exists with {count} row(s)")
        
        cursor.close()
        conn.close()
        
        print("✅ Database health check passed!")
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
