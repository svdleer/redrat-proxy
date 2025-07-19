#!/bin/bash
# Docker Reset Admin Script
# This script resets the admin password inside the Docker container

set -e

echo "🔧 Docker Reset Admin: Resetting admin password..."

# Activate virtual environment
source /app/venv/bin/activate

# Set Python path
export PYTHONPATH="/app"

# Reset admin password
python -c "
import sys
sys.path.append('/app')
try:
    from app.mysql_db import db
    from app.auth import hash_password
    
    # Create a new password hash for 'admin'
    new_password_hash = hash_password('admin')
    print(f'🔑 Generated new password hash')
    
    # Update the admin user's password
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = %s WHERE username = %s', (new_password_hash, 'admin'))
        conn.commit()
        print('✅ Admin password reset to: admin')
        print('🌐 You can now login with username: admin, password: admin')
        
except Exception as e:
    print(f'❌ Error resetting admin password: {e}')
    exit(1)
"

echo "🎉 Admin password reset completed successfully!"
