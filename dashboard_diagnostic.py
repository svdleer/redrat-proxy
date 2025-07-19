#!/usr/bin/env python3
"""
Dashboard Data Diagnostic Script
Checks database connectivity and content to troubleshoot missing dashboard data
"""

import sys
import os
sys.path.append('/app')

try:
    from app.mysql_db import get_db_connection
    from app.models.api_key import ApiKey
    from app.models.redrat_device import RedratDevice
    from app.models.remote import Remote
    from app.models.user import User
    import mysql.connector
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the correct directory with proper Python path")
    sys.exit(1)

def test_database_connection():
    """Test basic database connectivity"""
    print("=== Database Connection Test ===")
    try:
        conn = get_db_connection()
        if conn:
            print("✓ Database connection successful")
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✓ MySQL version: {version[0]}")
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✓ Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
            
            conn.close()
            return True
        else:
            print("✗ Failed to connect to database")
            return False
    except Exception as e:
        print(f"✗ Database connection error: {e}")
        return False

def check_table_data():
    """Check if tables have data"""
    print("\n=== Table Data Check ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check each important table
        tables_to_check = [
            ('users', 'User accounts'),
            ('api_keys', 'API Keys'), 
            ('redrat_devices', 'RedRat Devices'),
            ('remotes', 'Remote Controls'),
            ('templates', 'IR Templates'),
            ('sequences', 'Command Sequences'),
            ('schedules', 'Scheduled Commands')
        ]
        
        for table_name, description in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"✓ {description}: {count} records")
                else:
                    print(f"⚠ {description}: EMPTY (0 records)")
            except Exception as e:
                print(f"✗ {description}: Error - {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ Error checking table data: {e}")

def check_admin_user():
    """Check if admin user exists"""
    print("\n=== Admin User Check ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT username, is_admin FROM users WHERE is_admin = 1")
        admin_users = cursor.fetchall()
        
        if admin_users:
            print(f"✓ Found {len(admin_users)} admin user(s):")
            for username, is_admin in admin_users:
                print(f"  - {username} (admin: {bool(is_admin)})")
        else:
            print("⚠ No admin users found")
            print("  This could explain why admin features are missing from the dashboard")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ Error checking admin users: {e}")

def check_flask_app_config():
    """Check Flask app configuration"""
    print("\n=== Flask App Configuration ===")
    
    try:
        # Check environment variables
        env_vars = [
            'MYSQL_HOST',
            'MYSQL_USER', 
            'MYSQL_PASSWORD',
            'MYSQL_DATABASE',
            'FLASK_ENV',
            'SECRET_KEY'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                if 'PASSWORD' in var or 'SECRET' in var:
                    print(f"✓ {var}: ***HIDDEN***")
                else:
                    print(f"✓ {var}: {value}")
            else:
                print(f"⚠ {var}: Not set")
                
    except Exception as e:
        print(f"✗ Error checking Flask config: {e}")

def check_recent_logs():
    """Check for recent application logs"""
    print("\n=== Recent Application Activity ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if there's a logs table
        cursor.execute("SHOW TABLES LIKE 'logs'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM logs WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)")
            recent_logs = cursor.fetchone()[0]
            print(f"Recent log entries (last hour): {recent_logs}")
            
            if recent_logs > 0:
                cursor.execute("SELECT level, message, created_at FROM logs ORDER BY created_at DESC LIMIT 5")
                logs = cursor.fetchall()
                print("Most recent log entries:")
                for level, message, created_at in logs:
                    print(f"  [{created_at}] {level}: {message[:100]}...")
        else:
            print("No logs table found")
        
        conn.close()
        
    except Exception as e:
        print(f"Could not check logs: {e}")

def main():
    """Main diagnostic function"""
    print("RedRat Dashboard Data Diagnostic")
    print("=" * 50)
    
    # Test database connectivity
    db_ok = test_database_connection()
    
    if db_ok:
        # Check table data
        check_table_data()
        check_admin_user()
        check_recent_logs()
    
    # Check app configuration regardless
    check_flask_app_config()
    
    print("\n" + "=" * 50)
    print("Diagnostic completed!")
    print("\nIf tables are empty, you may need to:")
    print("1. Run database migrations")
    print("2. Create admin user: docker-compose exec web python /app/docker-reset-admin.sh")
    print("3. Import/recreate your data")
    print("\nIf database connection fails, check:")
    print("1. MySQL container is running")
    print("2. Environment variables are correct")
    print("3. Network connectivity between containers")

if __name__ == "__main__":
    main()
