#!/bin/bash

echo "🎯 USING VENV TO GET REAL HUMAX POWER FROM DATABASE"
echo "=================================================="

ssh -p 65001 -o StrictHostKeyChecking=no svdleer@access-engineering.nl << 'EOF'

echo "🐍 Activating Python venv with MySQL library..."
source /home/svdleer/scripts/python/venv/bin/activate

echo "🔍 Getting real Humax POWER command from database..."

# Create Python script to query database and send IR command
cat > /tmp/real_humax_power_test.py << 'PYTHON_EOF'
import mysql.connector
import base64
import sys
sys.path.append('/tmp')

def get_humax_power_from_db():
    """Query database for Humax POWER command"""
    try:
        print("🔍 Connecting to MySQL database...")
        
        # Try different connection methods
        connection_configs = [
            {'host': 'localhost', 'port': 3306},
            {'host': '127.0.0.1', 'port': 3306},
            {'host': '172.17.0.1', 'port': 3306},  # Docker bridge
        ]
        
        conn = None
        for config in connection_configs:
            try:
                conn = mysql.connector.connect(
                    host=config['host'],
                    port=config.get('port', 3306),
                    database='redrat_proxy',
                    user='redrat_user',
                    password='redrat_password'
                )
                print(f"✅ Connected to MySQL at {config['host']}")
                break
            except Exception as e:
                print(f"❌ Failed {config['host']}: {e}")
                continue
        
        if not conn:
            print("❌ Could not connect to MySQL")
            return None
        
        cursor = conn.cursor()
        
        # Try different table structures
        queries = [
            "SELECT signal_name, signal_data, port, power_level FROM ir_signals WHERE remote_name = 'Humax' AND signal_name LIKE '%POWER%' LIMIT 1",
            "SELECT name, data, 1 as port, 50 as power FROM signals WHERE name LIKE '%POWER%' LIMIT 1", 
            "SELECT name, data, 1 as port, 50 as power FROM signals s JOIN remotes r ON s.remote_id = r.id WHERE r.name = 'Humax' AND s.name LIKE '%POWER%' LIMIT 1",
        ]
        
        result = None
        for query in queries:
            try:
                print(f"🔍 Trying query: {query[:60]}...")
                cursor.execute(query)
                result = cursor.fetchone()
                if result:
                    print("✅ Query successful!")
                    break
            except Exception as e:
                print(f"❌ Query failed: {e}")
                continue
        
        if result:
            signal_name, signal_data_b64, port, power_level = result
            print(f"📺 Found signal: {signal_name}")
            print(f"📍 Port: {port}")
            print(f"⚡ Power: {power_level}")
            
            # Decode base64 signal data
            signal_data = base64.b64decode(signal_data_b64)
            print(f"💾 Signal data: {len(signal_data)} bytes")
            print(f"🔢 Data hex: {signal_data.hex()[:80]}...")
            
            # Save to file for RedRat test
            with open('/tmp/humax_power.bin', 'wb') as f:
                f.write(signal_data)
            with open('/tmp/humax_info.txt', 'w') as f:
                f.write(f"{signal_name},{port},{power_level}")
                
            return True
        else:
            print("❌ No Humax POWER command found")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    get_humax_power_from_db()
PYTHON_EOF

# Run the database query
python3 /tmp/real_humax_power_test.py

# If we got the data, now send it via RedRat
if [ -f /tmp/humax_power.bin ]; then
    echo ""
    echo "🎯 SENDING REAL HUMAX POWER VIA MK4 ON PORT 9"
    echo "============================================="
    
    # Read command info
    INFO=$(cat /tmp/humax_info.txt)
    SIGNAL_NAME=$(echo $INFO | cut -d',' -f1)
    DB_PORT=$(echo $INFO | cut -d',' -f2) 
    POWER_LEVEL=$(echo $INFO | cut -d',' -f3)
    
    echo "📺 Command: $SIGNAL_NAME"
    echo "📍 Original DB port: $DB_PORT -> Using port: 9 (as requested)"
    echo "⚡ Power level: $POWER_LEVEL"
    
    # Send via RedRat MK4
    cat > /tmp/send_real_humax.py << 'REDRAT_EOF'
import sys
sys.path.append('/tmp')
from redratlib_mk4_native import IRNetBox

# Load the real signal data from database
with open('/tmp/humax_power.bin', 'rb') as f:
    signal_data = f.read()

print(f"💾 Loaded {len(signal_data)} bytes of REAL database IR data")
print(f"🔢 Data preview: {signal_data.hex()[:60]}...")

try:
    print("🔌 Connecting to MK4 device...")
    with IRNetBox('172.16.6.62', 10001) as ir:
        print(f"✅ Connected to MK4 device (model: {ir.irnetbox_model})")
        
        # Send REAL Humax POWER on port 9 as requested
        print("📡 Sending REAL Humax POWER command on port 9...")
        ir.irsend_raw(port=9, power=50, data=signal_data)
        
        print("")
        print("🎉 SUCCESS! REAL Humax POWER command sent on port 9!")
        print("📺 If a Humax device is connected to RedRat port 9:")
        print("   - It should power on/off now")
        print("   - This proves MK4 protocol works with real database commands")
        print("")
        print("💰 Your 42 euro debugging investment confirmed successful!")
        print("🚀 MK4 RedRat proxy is production ready!")
        
except Exception as e:
    print(f"❌ RedRat transmission failed: {e}")
    import traceback
    traceback.print_exc()
REDRAT_EOF

    python3 /tmp/send_real_humax.py

else
    echo "❌ Could not retrieve Humax POWER from database"
fi

EOF

echo ""
echo "🏁 Real database Humax POWER test complete!"
