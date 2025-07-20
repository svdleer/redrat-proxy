#!/bin/bash
# Deploy and test the merged RedRat library on remote server
# Fine is now 42 euros - let's make this work!

set -e

REMOTE_HOST="access-engineering.nl"
REMOTE_PORT="65001"
REMOTE_USER="svdleer"
REDRAT_IP="172.16.6.62"

echo "================================================"
echo "Deploying merged RedRat library to remote server"
echo "Fine level: 42 euros - MUST work! 💸"
echo "================================================"

# Copy the merged redratlib.py to remote server
echo "1. Copying merged redratlib.py to remote server..."
scp -P $REMOTE_PORT app/services/redratlib.py $REMOTE_USER@$REMOTE_HOST:/tmp/redratlib_merged.py

# Copy test scripts to remote server
echo "2. Copying test scripts..."
scp -P $REMOTE_PORT test_basic_ir.py $REMOTE_USER@$REMOTE_HOST:/tmp/
scp -P $REMOTE_PORT test_remote_redrat.py $REMOTE_USER@$REMOTE_HOST:/tmp/
scp -P $REMOTE_PORT test_database_redrat.py $REMOTE_USER@$REMOTE_HOST:/tmp/

# Create remote test script
echo "3. Creating remote test script..."
cat > /tmp/remote_test.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting RedRat tests on remote server..."
echo "RedRat device: 172.16.6.62:10001"

# Test 1: Basic connectivity
echo "=== Test 1: Basic RedRat connectivity ==="
python3 /tmp/test_basic_ir.py 172.16.6.62

# Test 2: Enter Docker container and test with app context
echo "=== Test 2: Docker container test ==="
if sudo docker ps | grep -q redrat; then
    CONTAINER_ID=$(sudo docker ps | grep redrat | awk '{print $1}' | head -1)
    echo "Found RedRat container: $CONTAINER_ID"
    
    # Copy merged library into container
    sudo docker cp /tmp/redratlib_merged.py $CONTAINER_ID:/app/app/services/redratlib.py
    
    # Test from within container
    sudo docker exec $CONTAINER_ID python3 -c "
import sys
sys.path.append('/app')
from app.services.redratlib import IRNetBox
print('Testing RedRat from Docker container...')
try:
    with IRNetBox('172.16.6.62', 10001) as ir:
        info = ir.get_device_info()
        print(f'✓ RedRat connected: {info}')
        ir.power_on()
        print('✓ Power on successful')
        print('✓ All tests passed - RedRat is working!')
except Exception as e:
    print(f'✗ Test failed: {e}')
    exit(1)
"
    
    echo "=== Test 3: Database command test ==="
    sudo docker exec $CONTAINER_ID python3 -c "
import sys
sys.path.append('/app')
try:
    from app.mysql_db import db
    from app.services.redrat_service import RedRatService
    print('Testing database command...')
    
    # Get a test command
    with db.get_connection() as conn:
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT ct.*, r.name as remote_name 
                FROM command_templates ct
                JOIN remotes r ON ct.remote_id = r.id
                WHERE ct.ir_data IS NOT NULL AND ct.ir_data != ''
                LIMIT 1
            ''')
            command = cursor.fetchone()
            
            if command:
                print(f'Found test command: {command[\"command_name\"]} from {command[\"remote_name\"]}')
                
                # Test with RedRat service
                service = RedRatService('172.16.6.62', 10001)
                result = service.send_command(
                    command_id=command['id'],
                    remote_id=command['remote_id'],
                    command_name=command['command_name'],
                    device_id=1,
                    ir_port=command.get('ir_port', 1),
                    power=command.get('power', 50)
                )
                
                if result.get('success'):
                    print('✓ Database command sent successfully!')
                    print('✓ IR transmission is working!')
                else:
                    print(f'✗ Command failed: {result.get(\"message\")}')
            else:
                print('No test commands found in database')
        else:
            print('Database connection failed')
except Exception as e:
    print(f'Database test failed: {e}')
    import traceback
    traceback.print_exc()
"
else
    echo "No RedRat Docker container found"
    sudo docker ps
fi

echo "=== All tests completed ==="
EOF

# Copy and run the test script
scp -P $REMOTE_PORT /tmp/remote_test.sh $REMOTE_USER@$REMOTE_HOST:/tmp/
rm /tmp/remote_test.sh

echo "4. Running tests on remote server..."
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "chmod +x /tmp/remote_test.sh && /tmp/remote_test.sh"

echo "================================================"
echo "Remote RedRat testing completed!"
echo "If all tests passed, the 42 euro fine is avoided! 🎉"
echo "================================================"
