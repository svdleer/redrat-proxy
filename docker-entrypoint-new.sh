#!/bin/bash
set -e

echo "=== RedRat Proxy Docker Entrypoint ==="

# Activate virtual environment
source /app/venv/bin/activate

# Print Python version and location
echo "Using Python: $(which python)"
python --version

# Print Flask version
echo "Flask version: $(pip show flask | grep Version)"

# Wait for MySQL to be ready
echo "Waiting for MySQL on ${MYSQL_HOST:-host.docker.internal} to be ready..."
MAX_RETRIES=15
RETRY_INTERVAL=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -c "
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
    sys.exit(0)
except Exception as e:
    print(f'MySQL connection failed: {e}')
    sys.exit(1)
    " >/dev/null 2>&1; then
        echo "MySQL on host is ready!"
        break
    else
        echo "Waiting for MySQL on host... Retry $((RETRY_COUNT+1))/$MAX_RETRIES"
        RETRY_COUNT=$((RETRY_COUNT+1))
        sleep $RETRY_INTERVAL
    fi
done

# Important: Continue even if MySQL connection check fails
if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Warning: Could not connect to MySQL after $MAX_RETRIES retries."
    echo "Will try to set up the database anyway."
fi

# Create data directories if they don't exist
mkdir -p /app/app/static/uploads/irdb
mkdir -p /app/app/static/uploads/temp
mkdir -p /app/app/static/remote_images
chmod -R 777 /app/app/static

# Try to initialize the database
echo "Initializing database..."
python -m app.database.init_db || {
    echo "Database initialization using app module failed. Trying direct script..."
    # Direct approach if module fails
    DB_NAME=${MYSQL_DB:-redrat_proxy}
    MYSQL_CMD="mysql -h ${MYSQL_HOST:-host.docker.internal} -u ${MYSQL_USER:-redrat} -p${MYSQL_PASSWORD:-redratpass} -P ${MYSQL_PORT:-3306}"
    
    # Create database if it doesn't exist
    echo "Creating database $DB_NAME if it doesn't exist..."
    $MYSQL_CMD -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"
    
    # Import schema
    echo "Importing schema from mysql_schema.sql..."
    $MYSQL_CMD $DB_NAME < /app/mysql_schema.sql
    
    # Verify admin user exists
    echo "Verifying admin user..."
    ADMIN_COUNT=$($MYSQL_CMD -N -e "SELECT COUNT(*) FROM $DB_NAME.users WHERE username='admin';")
    
    if [ "$ADMIN_COUNT" -eq 0 ]; then
        echo "Creating admin user..."
        $MYSQL_CMD $DB_NAME -e "INSERT INTO users (id, username, password_hash, is_admin) VALUES ('admin-id', 'admin', '\$2b\$12\$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', TRUE);"
    fi
}

# Reset the admin password if DB exists but login fails
echo "Resetting admin password to ensure login works..."
python -c "
import bcrypt
import mysql.connector
import os
import sys

try:
    # Connect to the database
    conn = mysql.connector.connect(
        host=os.environ.get('MYSQL_HOST', 'host.docker.internal'),
        user=os.environ.get('MYSQL_USER', 'redrat'),
        password=os.environ.get('MYSQL_PASSWORD', 'redratpass'),
        database=os.environ.get('MYSQL_DB', 'redrat_proxy'),
        port=int(os.environ.get('MYSQL_PORT', '3306'))
    )
    
    cursor = conn.cursor()
    
    # Generate new admin password hash
    password = 'admin123'
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    # Update admin password
    cursor.execute('UPDATE users SET password_hash = %s WHERE username = %s', 
                   (hashed_password, 'admin'))
    
    if cursor.rowcount == 0:
        # Admin user doesn't exist, create it
        cursor.execute(
            'INSERT INTO users (id, username, password_hash, is_admin) VALUES (%s, %s, %s, %s)',
            ('admin-id', 'admin', hashed_password, True)
        )
        
    conn.commit()
    cursor.close()
    conn.close()
    
    print('Admin password reset successfully to: admin123')
    
except Exception as e:
    print(f'Error resetting admin password: {e}')
    # Continue even if this fails
" || echo "Failed to reset admin password, but continuing..."

echo "Initialization complete. Starting application..."

# Execute the command passed to docker-entrypoint.sh
exec "$@"
