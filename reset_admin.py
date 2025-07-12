#!/usr/bin/env python3
"""
Admin password reset utility.
Run this script to reset the admin password to 'admin123'.
"""

import bcrypt
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables if .env file exists
load_dotenv()

# Database configuration
db_config = {
    'host': os.getenv('MYSQL_HOST', 'host.docker.internal'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'redrat'),
    'password': os.getenv('MYSQL_PASSWORD', 'redratpass'),
    'database': os.getenv('MYSQL_DB', 'redrat_proxy')
}

def hash_password(password):
    """Generate a bcrypt hash for the given password."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def reset_admin_password():
    """Reset the admin user's password to 'admin123'."""
    # Generate new password hash
    new_password = 'admin123'
    password_hash = hash_password(new_password)
    
    # Connect to the database
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Check if admin user exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        
        if admin:
            # Update existing admin
            cursor.execute("UPDATE users SET password_hash = %s WHERE username = 'admin'", (password_hash,))
            print(f"✅ Updated admin password to '{new_password}'")
        else:
            # Create admin user if it doesn't exist
            admin_id = 'admin-id'
            cursor.execute(
                "INSERT INTO users (id, username, password_hash, is_admin) VALUES (%s, %s, %s, TRUE)",
                (admin_id, 'admin', password_hash)
            )
            print(f"✅ Created admin user with password '{new_password}'")
        
        conn.commit()
        
        # Verify the password was updated
        cursor.execute("SELECT password_hash FROM users WHERE username = 'admin'")
        result = cursor.fetchone()
        if result:
            print(f"Current password hash in database: {result[0][:20]}...")
            print("Login credentials:")
            print("- Username: admin")
            print(f"- Password: {new_password}")
        else:
            print("❌ Failed to verify admin user")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    reset_admin_password()
