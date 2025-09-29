#!/usr/bin/env python3
"""
Extract real IR signal data from the database and test power comman    print(f"\n📆 Database Command Analysis:")
    print(f"   Name: {db_command['name']}")
    print(f"   UID: {db_command['uid']}")
    print(f"   Modulation: {db_command['modulation_freq']} Hz")
    print(f"   Lengths: {db_command['lengths']}")
    print(f"   Repeats: {db_command['no_repeats']}")
    print(f"   Pause: {db_command['intra_sig_pause']} ms")
    print(f"   Signal Data: {len(db_command['sig_data'])} bytes")
    print(f"   Data Hex: {db_command['sig_data'].hex()}")port sys
import os
import time
import base64
import mysql.connector
from mysql.connector import Error

# Add the app directory to the Python path
sys.path.insert(0, '/home/svdleer/redrat-proxy')

def get_power_command_from_db():
    """Get the actual POWER command from the database"""
    
    print("🗄️  EXTRACTING POWER COMMAND FROM DATABASE")
    print("=" * 50)
    
    try:
        # Database connection using credentials from .env
        connection = mysql.connector.connect(
            host='localhost',
            database='redrat_proxy',
            user='redrat',
            password='Clad6DytmucAr'
        )
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            
            # Search for power-related commands
            power_queries = [
                "SELECT * FROM command_templates WHERE name LIKE '%power%' OR name LIKE '%POWER%'",
                "SELECT * FROM command_templates WHERE name LIKE '%on%' OR name LIKE '%ON%'",
                "SELECT * FROM command_templates WHERE name LIKE '%standby%' OR name LIKE '%STANDBY%'",
                "SELECT * FROM command_templates LIMIT 10"  # Show first 10 commands as fallback
            ]
            
            found_signals = []
            
            for query in power_queries:
                print(f"\n🔍 Searching: {query}")
                cursor.execute(query)
                results = cursor.fetchall()
                
                if results:
                    print(f"   Found {len(results)} commands:")
                    for command in results:
                        print(f"     - {command.get('name', 'Unknown')} (ID: {command.get('id', 'N/A')})")
                        found_signals.extend(results)
                    break
            
            if found_signals:
                # Use the first power command found
                power_command = found_signals[0]
                print(f"\n✅ Using command: {power_command['name']}")
                
                return {
                    'name': power_command['name'],
                    'uid': power_command.get('uid', ''),
                    'modulation_freq': int(power_command.get('modulation_freq', 38000)),
                    'lengths': eval(power_command.get('lengths', '[0.56, 0.56, 0.56, 1.68]')),  # Parse array
                    'sig_data': base64.b64decode(power_command.get('sig_data', '')),
                    'no_repeats': int(power_command.get('no_repeats', 1)),
                    'intra_sig_pause': float(power_command.get('intra_sig_pause', 0.0))
                }
            else:
                print("❌ No power commands found in database")
                return None
                
    except Error as e:
        print(f"❌ Database error: {e}")
        return None
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def test_db_power_command():
    """Test the real power command from database"""
    
    print("\n🚀 TESTING DATABASE POWER COMMAND")
    print("=" * 50)
    
    # Get command from database
    db_command = get_power_command_from_db()
    if not db_command:
        print("❌ Could not get command from database")
        return
    
    print(f"\n📊 Database Signal Analysis:")
    print(f"   Name: {db_signal['name']}")
    print(f"   UID: {db_signal['uid']}")
    print(f"   Modulation: {db_signal['modulation_freq']} Hz")
    print(f"   Lengths: {db_signal['lengths']}")
    print(f"   Repeats: {db_signal['no_repeats']}")
    print(f"   Pause: {db_signal['intra_sig_pause']} ms")
    print(f"   Signal Data: {len(db_signal['sig_data'])} bytes")
    print(f"   Data Hex: {db_signal['sig_data'].hex()}")
    
    try:
        from app.services.irnetbox_lib_new import IRNetBox, IRSignal, OutputConfig, PowerLevel
        
        # Create IRSignal from database data
        power_signal = IRSignal(
            name=db_command['name'],
            uid=db_command['uid'],
            modulation_freq=db_command['modulation_freq'],
            lengths=db_command['lengths'],
            sig_data=db_command['sig_data'],
            no_repeats=db_command['no_repeats'],
            intra_sig_pause=db_command['intra_sig_pause']
        )
        
        # Connect to RedRat
        redrat = IRNetBox()
        if not redrat.connect("172.16.6.62"):
            print("❌ Could not connect to RedRat device")
            return
        
        print("\n✅ Connected to RedRat device")
        print(f"   Device Type: {redrat.device_type.value}")
        
        # Test with HIGH power on port 9
        print(f"\n🔋 Sending REAL power signal with HIGH power on Port 9...")
        
        try:
            output_config = OutputConfig(port=9, power_level=PowerLevel.HIGH)
            seq_num = redrat.send_signal_async(power_signal, [output_config], 
                                              post_delay_ms=1000)
            
            print(f"   ✅ Real power signal sent! (seq: {seq_num})")
            print(f"   💡 Check if your device powered on!")
            
            # Wait a bit, then try with more repeats if device supports it
            time.sleep(3)
            
            if db_command['no_repeats'] == 1:
                print(f"\n🔁 Trying with multiple repeats...")
                power_signal_repeat = IRSignal(
                    name=f"{db_command['name']}_REPEAT",
                    uid=f"{db_command['uid']}_repeat",
                    modulation_freq=db_command['modulation_freq'],
                    lengths=db_command['lengths'],
                    sig_data=db_command['sig_data'],
                    no_repeats=3,  # Try 3 repeats
                    intra_sig_pause=100.0  # 100ms pause between repeats
                )
                
                seq_num2 = redrat.send_signal_async(power_signal_repeat, [output_config], 
                                                   post_delay_ms=1500)
                print(f"   ✅ Repeat signal sent! (seq: {seq_num2})")
                print(f"   💡 Check if your device responded to repeated signal!")
            
        except Exception as e:
            print(f"   ❌ Failed to send signal: {e}")
        
        redrat.disconnect()
        print("\n🔌 Disconnected from RedRat device")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def list_all_commands():
    """List all commands in the database to help identify the right one"""
    
    print("\n📋 ALL COMMANDS IN DATABASE")
    print("=" * 50)
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='redrat_proxy',
            user='redrat',
            password='Clad6DytmucAr'
        )
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name, modulation_freq, no_repeats FROM command_templates ORDER BY name")
            results = cursor.fetchall()
            
            if results:
                print(f"Found {len(results)} commands:")
                for command in results:
                    print(f"  ID {command['id']:3d}: {command['name']} ({command['modulation_freq']}Hz, {command['no_repeats']} repeats)")
            else:
                print("No commands found in database")
                
    except Error as e:
        print(f"❌ Database error: {e}")
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    print("🎯 DATABASE POWER SIGNAL TEST")
    print("=" * 50)
    print("This script will:")
    print("1. Connect to your MySQL database")
    print("2. Find power-related IR signals")
    print("3. Test the real signal with your RedRat device")
    print()
    
    # Database credentials loaded from .env
    print("✅ Database credentials loaded from .env file")
    print()
    
    # Run the tests
    list_all_commands()
    test_db_power_command()