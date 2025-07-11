#!/usr/bin/env python3
"""
Reset admin password utility for RedRat Proxy
"""
import sys
import os
import bcrypt
import mysql.connector
from mysql.connector import Error

def hash_password(password):
    """Generate bcrypt hash for password"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def main():
    # Database connection parameters
    db_config = {
        'host': os.environ.get('MYSQL_HOST', 'host.docker.internal'),
        'user': os.environ.get('MYSQL_USER', 'redrat'),
        'password': os.environ.get('MYSQL_PASSWORD', 'redratpass'),
        'database': os.environ.get('MYSQL_DB', 'redrat_proxy')
    }
    
    # New admin credentials
    admin_password = 'admin123'
    password_hash = hash_password(admin_password)
    
    try:
        # Connect to MySQL
        connection = mysql.connector.connect(**db_config)
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Check if admin user exists
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            result = cursor.fetchone()
            
            if result:
                # Update existing admin password
                admin_id = result[0]
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (password_hash, admin_id)
                )
                connection.commit()
                print(f"Admin password updated successfully to: {admin_password}")
            else:
                # Create new admin user
                admin_id = 'admin-id'
                cursor.execute(
                    "INSERT INTO users (id, username, password_hash, is_admin) VALUES (%s, %s, %s, %s)",
                    (admin_id, 'admin', password_hash, True)
                )
                connection.commit()
                print(f"Admin user created successfully with password: {admin_password}")
                
            print("\nLogin credentials:")
            print("Username: admin")
            print(f"Password: {admin_password}")
            
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

if __name__ == "__main__":
    main()
