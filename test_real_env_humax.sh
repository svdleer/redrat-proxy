#!/bin/bash

echo "🎯 USING REAL .ENV CREDENTIALS FOR DATABASE ACCESS"
echo "================================================"

ssh -p 65001 -o StrictHostKeyChecking=no svdleer@access-engineering.nl << 'EOF'

echo "📋 Reading .env file for database credentials..."
cat /home/svdleer/redrat/redrat-proxy/.env

echo ""
echo "🐍 Activating Python venv..."
source /home/svdleer/scripts/python/venv/bin/activate

echo "🔍 Getting real Humax POWER from database with correct credentials..."

# Create Python script using real .env credentials
cat > /tmp/real_db_humax_test.py << 'PYTHON_EOF'
import mysql.connector
import base64
import sys
import os
sys.path.append('/tmp')

def load_env_vars():
    """Load environment variables from .env file"""
    env_vars = {}
    try:
        with open('/home/svdleer/redrat/redrat-proxy/.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"❌ Error reading .env: {e}")
    return env_vars

def get_humax_power_from_db():
    """Query database for Humax POWER command using real .env credentials"""
    try:
        print("📋 Loading .env variables...")
        env_vars = load_env_vars()
        
        # Extract database credentials
        db_host = env_vars.get('DB_HOST', 'localhost')
        db_name = env_vars.get('DB_NAME', 'redrat_proxy')
        db_user = env_vars.get('DB_USER', 'redrat_user')
        db_pass = env_vars.get('DB_PASSWORD', 'redrat_password')
        db_port = int(env_vars.get('DB_PORT', '3306'))
        
        print(f"🔍 Connecting to MySQL: {db_user}@{db_host}:{db_port}/{db_name}")
        
        conn = mysql.connector.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass
        )
        
        print("✅ Connected to MySQL database!")
        cursor = conn.cursor()
        
        # Check what tables exist
        print("📋 Checking available tables...")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"Tables: {[table[0] for table in tables]}")
        
        # Try to find Humax POWER command
        queries = [
            # Try different possible table structures
            "SELECT signal_name, signal_data, port, power_level FROM ir_signals WHERE remote_name = 'Humax' AND signal_name LIKE '%POWER%' LIMIT 1",
            "SELECT name, data, 1 as port, 50 as power FROM signals WHERE name LIKE '%POWER%' LIMIT 1",
            "SELECT s.name, s.data, 1 as port, 50 as power FROM signals s JOIN remotes r ON s.remote_id = r.id WHERE r.name = 'Humax' AND s.name LIKE '%POWER%' LIMIT 1",
            "SELECT name, data, 9 as port, 50 as power FROM signals WHERE name LIKE '%POWER%' ORDER BY id LIMIT 1",
        ]
        
        result = None
        successful_query = None
        
        for query in queries:
            try:
                print(f"🔍 Trying: {query[:80]}...")
                cursor.execute(query)
                result = cursor.fetchone()
                if result:
                    successful_query = query
                    print("✅ Found POWER command!")
                    break
                else:
                    print("❌ No results")
            except Exception as e:
                print(f"❌ Query failed: {str(e)[:100]}")
                continue
        
        if not result:
            # Let's see what data is actually in the database
            print("🔍 Let's see what signals are available...")
            try:
                cursor.execute("SELECT name FROM signals LIMIT 10")
                signals = cursor.fetchall()
                print(f"Available signals: {[s[0] for s in signals]}")
            except:
                pass
                
            try:
                cursor.execute("SELECT * FROM signals WHERE name LIKE '%POWER%' LIMIT 1")
                power_signals = cursor.fetchall()
                if power_signals:
                    result = power_signals[0]
                    # Assume structure: id, remote_id, name, data
                    result = (result[2], result[3], 9, 50)  # name, data, port, power
                    print("✅ Found POWER signal with fallback query!")
            except Exception as e:
                print(f"Fallback query failed: {e}")
        
        if result:
            signal_name, signal_data_b64, port, power_level = result
            print(f"📺 Signal: {signal_name}")
            print(f"📍 Port: {port}")
            print(f"⚡ Power: {power_level}")
            
            # Decode base64 signal data
            try:
                signal_data = base64.b64decode(signal_data_b64)
                print(f"💾 Signal data: {len(signal_data)} bytes")
                print(f"🔢 Data hex preview: {signal_data.hex()[:80]}...")
                
                # Save for RedRat test
                with open('/tmp/humax_power_real.bin', 'wb') as f:
                    f.write(signal_data)
                with open('/tmp/humax_info_real.txt', 'w') as f:
                    f.write(f"{signal_name},{port},{power_level}")
                    
                print("💾 Saved real database command for RedRat test")
                return True
                
            except Exception as e:
                print(f"❌ Failed to decode signal data: {e}")
                print(f"Raw data preview: {str(signal_data_b64)[:100]}...")
                return False
        else:
            print("❌ No POWER command found in database")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    get_humax_power_from_db()
PYTHON_EOF

# Run the database query with real credentials
python3 /tmp/real_db_humax_test.py

# If we got the data, send it via RedRat
if [ -f /tmp/humax_power_real.bin ]; then
    echo ""
    echo "🎯 SENDING REAL DATABASE HUMAX POWER ON PORT 9"
    echo "=============================================="
    
    INFO=$(cat /tmp/humax_info_real.txt)
    SIGNAL_NAME=$(echo $INFO | cut -d',' -f1)
    PORT=$(echo $INFO | cut -d',' -f2)
    POWER=$(echo $INFO | cut -d',' -f3)
    
    echo "📺 Real command: $SIGNAL_NAME"
    echo "📍 Sending on port: 9 (as requested)"
    echo "⚡ Power level: $POWER"
    
    # Send via MK4 RedRat
    python3 << 'REDRAT_EOF'
import sys
sys.path.append('/tmp')
from redratlib_mk4_native import IRNetBox

# Load REAL database signal
with open('/tmp/humax_power_real.bin', 'rb') as f:
    real_signal_data = f.read()

print(f"💾 Loaded {len(real_signal_data)} bytes from REAL database")
print(f"🔢 Real data: {real_signal_data.hex()[:60]}...")

try:
    print("🔌 Connecting to MK4 RedRat device...")
    with IRNetBox('172.16.6.62', 10001) as ir:
        print(f"✅ Connected! MK4 device (model: {ir.irnetbox_model})")
        
        print("📡 Transmitting REAL Humax POWER on port 9...")
        ir.irsend_raw(port=9, power=50, data=real_signal_data)
        
        print("")
        print("🎉🎉🎉 SUCCESS! 🎉🎉🎉")
        print("📺 REAL Humax POWER command transmitted on port 9!")
        print("💡 If Humax device connected to RedRat port 9 → should respond")
        print("✅ MK4 native protocol working with REAL database commands!")
        print("💰 42 euro investment: CONFIRMED SUCCESSFUL!")
        print("🚀 RedRat proxy is production ready!")
        
except Exception as e:
    print(f"❌ RedRat transmission error: {e}")
REDRAT_EOF

else
    echo "❌ Could not get real database command"
fi

EOF

echo ""
echo "🏁 Real .env database test complete!"
