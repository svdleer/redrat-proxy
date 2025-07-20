#!/bin/bash

echo "🎯 TESTING REAL HUMAX POWER COMMAND FROM DATABASE"
echo "================================================="

# Copy the database test script
echo "📤 Copying real database test script..."
scp -P 65001 -o StrictHostKeyChecking=no test_real_humax_power.py svdleer@access-engineering.nl:/tmp/

# Run the test in Docker environment
echo "🐳 Running test in Docker environment..."
ssh -p 65001 -o StrictHostKeyChecking=no svdleer@access-engineering.nl << 'EOF'
cd /tmp

# Install mysql connector if needed
pip3 install mysql-connector-python > /dev/null 2>&1 || echo "MySQL connector already available"

# Run inside Docker network to access MySQL
docker exec -i $(docker ps --format "table {{.Names}}" | grep -v NAMES | head -1) python3 - << 'PYTHON_EOF'
import sys
sys.path.append('/tmp')

# Copy the test file content here since we're inside Docker
import mysql.connector
import base64

# MySQL connection inside Docker
try:
    print("🔍 Connecting to MySQL database...")
    conn = mysql.connector.connect(
        host='mysql',  # Docker service name
        database='redrat_proxy',
        user='redrat_user', 
        password='redrat_password'
    )
    
    cursor = conn.cursor()
    
    # Query for Humax POWER command
    print("📋 Querying for Humax POWER command...")
    query = """
    SELECT signal_name, signal_data, port, power_level 
    FROM ir_signals 
    WHERE remote_name = 'Humax' AND signal_name LIKE '%POWER%'
    LIMIT 1
    """
    
    cursor.execute(query)
    result = cursor.fetchone()
    
    if result:
        signal_name, signal_data_b64, port, power_level = result
        print(f"✅ Found: {signal_name}")
        print(f"📍 Database port: {port}")  
        print(f"⚡ Power level: {power_level}")
        
        # Decode signal data
        signal_data = base64.b64decode(signal_data_b64)
        print(f"💾 Signal length: {len(signal_data)} bytes")
        print(f"🔢 Data preview: {signal_data.hex()[:80]}...")
        
        # Write to file for the RedRat test
        with open('/tmp/humax_power_data.bin', 'wb') as f:
            f.write(signal_data)
        with open('/tmp/humax_power_info.txt', 'w') as f:
            f.write(f"{signal_name},{port},{power_level}")
        print("💾 Saved real command data for RedRat test")
        
    else:
        print("❌ No Humax POWER found in database")
        
except Exception as e:
    print(f"❌ Database error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
PYTHON_EOF

# Now test with RedRat if we got the data
if [ -f /tmp/humax_power_data.bin ]; then
    echo ""
    echo "🎯 SENDING REAL DATABASE COMMAND VIA MK4 ON PORT 9"
    echo "================================================"
    
    # Read the command info
    INFO=$(cat /tmp/humax_power_info.txt)
    SIGNAL_NAME=$(echo $INFO | cut -d',' -f1)
    DB_PORT=$(echo $INFO | cut -d',' -f2)
    POWER_LEVEL=$(echo $INFO | cut -d',' -f3)
    
    echo "📺 Command: $SIGNAL_NAME"
    echo "📍 Original port: $DB_PORT -> Using port: 9 (as requested)"
    echo "⚡ Power level: $POWER_LEVEL"
    
    # Test with RedRat
    python3 << 'REDRAT_EOF'
import sys
sys.path.append('/tmp')
from redratlib_mk4_native import IRNetBox

# Read the real signal data
with open('/tmp/humax_power_data.bin', 'rb') as f:
    signal_data = f.read()

print(f"💾 Loaded {len(signal_data)} bytes of real IR data")

try:
    with IRNetBox('172.16.6.62', 10001) as ir:
        print(f"✅ Connected to MK4 (model: {ir.irnetbox_model})")
        
        # Send on port 9 as requested
        ir.irsend_raw(port=9, power=50, data=signal_data)
        
        print("🎉 SUCCESS! Real Humax POWER sent on port 9!")
        print("📺 If Humax device connected to port 9, it should respond")
        print("💰 MK4 protocol confirmed working with real database commands!")
        
except Exception as e:
    print(f"❌ RedRat error: {e}")
REDRAT_EOF

else
    echo "❌ Could not get real command data from database"
fi
EOF

echo ""
echo "🏁 Real database command test complete!"
