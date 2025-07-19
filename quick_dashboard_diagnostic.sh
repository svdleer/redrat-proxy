#!/bin/bash

# Quick Dashboard Diagnostic for Docker Environment
# Run this on your server to check why dashboard data is missing

echo "RedRat Dashboard Quick Diagnostic"
echo "================================="
echo ""

# Check if containers are running
echo "=== Container Status ==="
docker-compose ps
echo ""

# Check database connectivity from the web container
echo "=== Database Connection Test ==="
docker-compose exec web python -c "
import sys
sys.path.append('/app')
try:
    from app.mysql_db import get_db_connection
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('SHOW TABLES')
        tables = cursor.fetchall()
        print(f'✓ Database connected. Found {len(tables)} tables:')
        for table in tables:
            print(f'  - {table[0]}')
        conn.close()
    else:
        print('✗ Database connection failed')
except Exception as e:
    print(f'✗ Database error: {e}')
"
echo ""

# Check table data counts
echo "=== Table Data Counts ==="
docker-compose exec web python -c "
import sys
sys.path.append('/app')
try:
    from app.mysql_db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    tables = ['users', 'api_keys', 'redrat_devices', 'remotes', 'templates']
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            status = '✓' if count > 0 else '⚠'
            print(f'{status} {table}: {count} records')
        except Exception as e:
            print(f'✗ {table}: Error - {e}')
    conn.close()
except Exception as e:
    print(f'Database error: {e}')
"
echo ""

# Check admin user
echo "=== Admin User Check ==="
docker-compose exec web python -c "
import sys
sys.path.append('/app')
try:
    from app.mysql_db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, is_admin FROM users WHERE is_admin = 1')
    admins = cursor.fetchall()
    if admins:
        print('✓ Admin users found:')
        for username, is_admin in admins:
            print(f'  - {username}')
    else:
        print('⚠ No admin users found!')
        print('  Run: docker-compose exec web bash /app/docker-reset-admin.sh')
    conn.close()
except Exception as e:
    print(f'Error: {e}')
"
echo ""

# Check recent application logs
echo "=== Recent Application Logs ==="
echo "Last 10 log entries from web container:"
docker-compose logs --tail=10 web
echo ""

# Check if the web app is responding
echo "=== Web Application Test ==="
echo "Testing if web app responds to HTTP requests..."
docker-compose exec web curl -s -o /dev/null -w "HTTP Status: %{http_code}\\n" http://localhost:5000/ || echo "Could not test HTTP - curl not available"
echo ""

echo "=== Quick Fix Suggestions ==="
echo "If tables are empty:"
echo "  1. docker-compose exec web bash /app/docker-reset-admin.sh"
echo "  2. Re-create your RedRat devices and remotes"
echo ""
echo "If database connection fails:"
echo "  1. docker-compose restart mysql"
echo "  2. Check docker-compose.yml database settings"
echo ""
echo "If containers are not running:"
echo "  1. docker-compose down && docker-compose up -d"
echo ""
echo "To see full logs: docker-compose logs -f web"
