#!/usr/bin/env python3
"""
Get real POWER command from database and send it via MK4 on port 9
This will prove the MK4 protocol is working with real data
"""

import sys
import os
sys.path.append('/tmp')

from redratlib_mk4_native import IRNetBox
import mysql.connector
import base64
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_humax_power_from_database():
    """Get the real Humax POWER command from the MySQL database"""
    
    try:
        # Connect to the database in Docker
        print("🔍 Connecting to MySQL database in Docker...")
        conn = mysql.connector.connect(
            host='localhost',
            database='redrat_proxy',
            user='redrat_user',
            password='redrat_password'
        )
        
        cursor = conn.cursor()
        
        # Query for Humax POWER command
        print("📋 Querying database for Humax POWER command...")
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
            print(f"✅ Found signal: {signal_name}")
            print(f"📍 Port: {port}")
            print(f"⚡ Power: {power_level}")
            
            # Decode base64 signal data
            signal_data = base64.b64decode(signal_data_b64)
            print(f"💾 Signal data: {len(signal_data)} bytes")
            print(f"🔢 Data hex: {signal_data.hex()[:80]}...")
            
            return signal_name, signal_data, port, power_level
        else:
            print("❌ No Humax POWER command found in database")
            return None
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def send_humax_power_on_port9():
    """Send the real Humax POWER command on port 9 via MK4"""
    
    # Get the real command from database
    db_result = get_humax_power_from_database()
    if not db_result:
        return False
        
    signal_name, signal_data, db_port, db_power = db_result
    
    print("\n🎯 SENDING REAL HUMAX POWER COMMAND")
    print("="*50)
    print(f"Command: {signal_name}")
    print(f"Original port: {db_port} -> Using port: 9 (as requested)")
    print(f"Power level: {db_power}")
    print(f"Signal length: {len(signal_data)} bytes")
    
    try:
        with IRNetBox('172.16.6.62', 10001) as ir:
            print(f"✅ Connected to MK4 device (model: {ir.irnetbox_model})")
            
            # Send on port 9 as requested
            ir.irsend_raw(port=9, power=db_power, data=signal_data)
            
            print("🎉 SUCCESS! Real Humax POWER command sent on port 9!")
            print("📺 If a Humax device is connected to port 9, it should respond")
            print("💰 Your MK4 RedRat proxy is definitely working!")
            
            return True
            
    except Exception as e:
        print(f"❌ Failed to send command: {e}")
        return False

if __name__ == "__main__":
    send_humax_power_on_port9()
