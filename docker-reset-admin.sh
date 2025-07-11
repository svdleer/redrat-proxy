#!/bin/bash
# Docker-compatible admin password reset script
# This works inside the Docker container without requiring external tools

echo "=== RedRat Proxy Admin Password Reset ==="
echo "This script will reset the admin password to 'admin123'"

# Activate virtual environment if it exists
if [ -d "/app/venv" ]; then
    source /app/venv/bin/activate
fi

# Run Python script to reset password
python -c "
import bcrypt
import mysql.connector
import os
import sys
import uuid

# Password to set
new_password = 'admin123'

# Generate bcrypt hash
def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Database configuration
db_config = {
    'host': os.environ.get('MYSQL_HOST', 'host.docker.internal'),
    'user': os.environ.get('MYSQL_USER', 'redrat'),
    'password': os.environ.get('MYSQL_PASSWORD', 'redratpass'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'database': os.environ.get('MYSQL_DB', 'redrat_proxy')
}

try:
    # Generate password hash
    password_hash = hash_password(new_password)
    
    print('Connecting to database...')
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # First check if admin user exists
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = %s', ('admin',))
    admin_count = cursor.fetchone()[0]
    
    if admin_count > 0:
        # Update existing admin user
        print('Updating existing admin password...')
        cursor.execute(
            'UPDATE users SET password_hash = %s WHERE username = %s',
            (password_hash, 'admin')
        )
    else:
        # Create new admin user
        print('Creating new admin user...')
        admin_id = 'admin-' + str(uuid.uuid4())
        cursor.execute(
            'INSERT INTO users (id, username, password_hash, is_admin) VALUES (%s, %s, %s, %s)',
            (admin_id, 'admin', password_hash, True)
        )
    
    conn.commit()
    
    # Verify the change
    cursor.execute('SELECT id, username, is_admin FROM users WHERE username = %s', ('admin',))
    admin_user = cursor.fetchone()
    
    if admin_user:
        print('✓ Admin user updated successfully:')
        print(f'  ID: {admin_user[0]}')
        print(f'  Username: {admin_user[1]}')
        print(f'  Is Admin: {\"Yes\" if admin_user[2] else \"No\"}')
        print(f'  Password: {new_password}')
    else:
        print('⚠ Admin user not found after update!')
    
    # Close connection
    cursor.close()
    conn.close()

except Exception as e:
    print(f'Error resetting admin password: {e}')
    sys.exit(1)
"

# Print success message
echo ""
echo "If no errors were shown above, the admin password has been reset to 'admin123'"
echo "You should now be able to log in with:"
echo "  Username: admin"
echo "  Password: admin123"
