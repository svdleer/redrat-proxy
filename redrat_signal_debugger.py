#!/usr/bin/env python3
"""
RedRat IR Signal Debugger
Connects directly to RedRat device to test and debug IR signal transmission
"""

import sys
import os
import socket
import struct
import time
import binascii
from datetime import datetime

# Add app to path for imports
sys.path.insert(0, '/home/svdleer/redrat-proxy')

def test_redrat_connectivity(host="172.16.6.62", port=10001):
    """Test basic connectivity to RedRat device"""
    print(f"🔌 Testing RedRat connectivity: {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
        print("✅ TCP connection successful")
        
        # Test device version query
        version_msg = struct.pack(">cHB", b"#", 0, 0x09)
        sock.sendall(version_msg)
        response = sock.recv(1024)
        
        if len(response) >= 6:
            print(f"✅ Device responds to version query: {binascii.hexlify(response).decode()}")
            
            # Parse version response
            if len(response) >= 8:
                model = struct.unpack(">H", response[4:6])[0]
                print(f"📡 RedRat model: {model}")
                return True, model
        else:
            print("❌ Invalid version response")
            
        sock.close()
        return True, None
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False, None

def test_redrat_basic_commands(host="172.16.6.62", port=10001):
    """Test basic RedRat commands"""
    print(f"\n🔧 Testing basic RedRat commands")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        commands = [
            ("Power On", struct.pack(">cHB", b"#", 0, 0x05)),
            ("Reset", struct.pack(">cHBB", b"#", 1, 0x07, 0x00)),
            ("Indicators On", struct.pack(">cHBB", b"#", 1, 0x07, 0x17)),
        ]
        
        for name, cmd in commands:
            print(f"  Sending {name}...")
            sock.sendall(cmd)
            try:
                response = sock.recv(1024)
                if response:
                    print(f"  ✅ {name}: {binascii.hexlify(response).decode()}")
                else:
                    print(f"  ⚠️  {name}: No response")
            except socket.timeout:
                print(f"  ⚠️  {name}: Timeout")
            
            time.sleep(0.5)
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ Basic commands failed: {e}")
        return False

def get_signal_from_database():
    """Get a real signal from the database to test with"""
    print(f"\n💾 Getting signal from database")
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Import mysql connector directly
        import mysql.connector
        import json
        
        # Get database credentials from environment
        db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', '3306')),
            'user': os.getenv('MYSQL_USER', 'redrat'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DB', 'redrat_proxy')
        }
        
        print(f"🔌 Connecting to database: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        # Connect to database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Get a command template with signal data
        cursor.execute("""
            SELECT ct.name, ct.template_data, r.name as remote_name
            FROM command_templates ct
            JOIN remotes r ON JSON_EXTRACT(ct.template_data, '$.remote_id') = r.id
            WHERE ct.template_data IS NOT NULL 
            AND JSON_LENGTH(ct.template_data) > 10
            LIMIT 5
        """)
        
        templates = cursor.fetchall()
        
        if templates:
            print(f"📋 Found {len(templates)} signal templates:")
            for i, (cmd_name, template_data, remote_name) in enumerate(templates):
                print(f"  {i+1}. {cmd_name} ({remote_name})")
            
            # Use the first template
            selected = templates[0]
            cmd_name, template_data, remote_name = selected
            
            print(f"🎯 Selected: {cmd_name} from {remote_name}")
            
            # Parse template data
            if isinstance(template_data, bytes):
                template_data = template_data.decode('utf-8')
            if isinstance(template_data, str):
                template_data = json.loads(template_data)
            
            conn.close()
            return cmd_name, template_data, remote_name
        else:
            print("❌ No signal templates found in database")
            conn.close()
            return None, None, None
            
    except mysql.connector.Error as e:
        print(f"❌ MySQL error: {e}")
        return None, None, None
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None, None, None

def extract_ir_data(template_data):
    """Extract IR data from template"""
    print(f"\n🔍 Extracting IR data from template")
    
    try:
        # Check for different data formats
        if 'SigData' in template_data:
            sig_data = template_data['SigData']
            print(f"📡 Found SigData: {type(sig_data)}")
        elif 'signal_data' in template_data:
            sig_data = template_data['signal_data']
            print(f"📡 Found signal_data: {type(sig_data)}")
        elif 'IRPacket' in template_data and 'SigData' in template_data['IRPacket']:
            sig_data = template_data['IRPacket']['SigData']
            print(f"📡 Found IRPacket.SigData: {type(sig_data)}")
        else:
            print(f"❌ No signal data found. Keys: {list(template_data.keys())}")
            return None
        
        # Convert to bytes
        if isinstance(sig_data, str):
            # Try hex decode
            try:
                cleaned = ''.join(c for c in sig_data if c in '0123456789abcdefABCDEF')
                if len(cleaned) % 2 != 0:
                    cleaned = '0' + cleaned
                ir_data = binascii.unhexlify(cleaned)
                print(f"✅ Converted hex string to {len(ir_data)} bytes")
                return ir_data
            except:
                # Try base64
                try:
                    import base64
                    ir_data = base64.b64decode(sig_data)
                    print(f"✅ Converted base64 to {len(ir_data)} bytes")
                    return ir_data
                except:
                    print(f"❌ Could not decode string data")
                    return None
        elif isinstance(sig_data, bytes):
            print(f"✅ Already bytes: {len(sig_data)} bytes")
            return sig_data
        elif isinstance(sig_data, list):
            ir_data = bytes(sig_data)
            print(f"✅ Converted list to {len(ir_data)} bytes")
            return ir_data
        else:
            print(f"❌ Unknown data type: {type(sig_data)}")
            return None
            
    except Exception as e:
        print(f"❌ Error extracting IR data: {e}")
        return None

def test_ir_transmission(host="172.16.6.62", port=10001, ir_data=None, ir_port=1, power=50):
    """Test actual IR transmission"""
    print(f"\n📡 Testing IR transmission")
    print(f"   Port: {ir_port}, Power: {power}, Data length: {len(ir_data) if ir_data else 0} bytes")
    
    if not ir_data:
        print("❌ No IR data provided")
        return False
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect((host, port))
        
        # Power on and setup
        setup_commands = [
            ("Power On", struct.pack(">cHB", b"#", 0, 0x05)),
            ("Reset", struct.pack(">cHBB", b"#", 1, 0x07, 0x00)),
            ("Indicators On", struct.pack(">cHBB", b"#", 1, 0x07, 0x17)),
        ]
        
        for name, cmd in setup_commands:
            sock.sendall(cmd)
            try:
                response = sock.recv(1024)
                print(f"  {name}: OK")
            except:
                print(f"  {name}: No response")
            time.sleep(0.2)
        
        # Prepare IR data for transmission
        print(f"📤 Sending IR data...")
        print(f"   First 32 bytes: {ir_data[:32].hex()}")
        
        # IR Send command structure for RedRat
        # Message type 0x12 for IR send
        ir_command = struct.pack(">cHBBB", b"#", len(ir_data) + 2, 0x12, ir_port, power)
        full_message = ir_command + ir_data
        
        print(f"🔧 IR command: {ir_command.hex()}")
        print(f"📡 Sending {len(full_message)} bytes total...")
        
        # Send IR data
        sock.sendall(full_message)
        
        # Wait for response with longer timeout for IR transmission
        try:
            response = sock.recv(1024)
            if response:
                print(f"✅ IR transmission response: {response.hex()}")
                
                # Check if response indicates success
                if len(response) >= 4:
                    status = response[3] if len(response) > 3 else 0
                    if status == 0:
                        print("🎉 IR transmission appears successful!")
                    else:
                        print(f"⚠️  IR transmission status: {status}")
                
                return True
            else:
                print("❌ No response to IR transmission")
                return False
        except socket.timeout:
            print("⚠️  IR transmission timeout - this might be normal for some devices")
            return True  # Timeout might be normal
        
    except Exception as e:
        print(f"❌ IR transmission failed: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def test_with_simple_pattern(host="172.16.6.62", port=10001):
    """Test with a simple known IR pattern"""
    print(f"\n🧪 Testing with simple IR pattern")
    
    # Simple NEC protocol pattern
    simple_pattern = bytes([
        0x00, 0x01, 0x74, 0xF5,  # Header
        0xFF, 0x60, 0x00, 0x00,  # More header  
        0x00, 0x06, 0x00, 0x00,  # Length info
        0x00, 0x48, 0x02, 0x45,  # Timing data
        0x02, 0x22, 0x2F, 0x70,
        0x45, 0x40, 0xD1, 0x21,
        0x16, 0xA4, 0x64, 0xF0
    ])
    
    print(f"🔧 Simple pattern: {len(simple_pattern)} bytes")
    print(f"   Data: {simple_pattern.hex()}")
    
    return test_ir_transmission(host, port, simple_pattern, ir_port=1, power=30)

def compare_with_working_signal():
    """Compare our signals with the working original"""
    print(f"\n🔍 SIGNAL COMPARISON ANALYSIS")
    print("="*50)
    
    # Get signal from database
    cmd_name, template_data, remote_name = get_signal_from_database()
    if not template_data:
        return
    
    ir_data = extract_ir_data(template_data)
    if not ir_data:
        return
    
    print(f"\n📊 SIGNAL ANALYSIS:")
    print(f"Command: {cmd_name}")
    print(f"Remote: {remote_name}")
    print(f"Data length: {len(ir_data)} bytes")
    print(f"First 32 bytes: {ir_data[:32].hex()}")
    print(f"Last 32 bytes: {ir_data[-32:].hex()}")
    
    # Check for common RedRat signal patterns
    if len(ir_data) >= 12:
        header = ir_data[:12].hex()
        print(f"Header pattern: {header}")
        
        # Check if it looks like a valid RedRat signal
        if ir_data[0:2] == b'\x00\x01':
            print("✅ Looks like valid RedRat format (starts with 0001)")
        else:
            print("⚠️  Unusual header - might need format conversion")
    
    # Test parameters from template
    modulation_freq = template_data.get('modulation_freq')
    no_repeats = template_data.get('no_repeats', 1)
    power = template_data.get('power', 50)
    
    print(f"\n🎛️  SIGNAL PARAMETERS:")
    print(f"Modulation frequency: {modulation_freq}")
    print(f"Repeats: {no_repeats}")
    print(f"Power: {power}")
    
    return ir_data, template_data

def main():
    print("🚀 RedRat IR Signal Debugger")
    print("="*50)
    print("This tool tests the actual IR signal transmission")
    print("We know network communication works - now testing IR signals")
    print("")
    
    redrat_host = "172.16.6.62"
    
    # Test 1: Basic connectivity
    connected, model = test_redrat_connectivity(redrat_host)
    if not connected:
        print("❌ Cannot connect to RedRat device. Check network connectivity.")
        return
    
    # Test 2: Basic commands
    basic_ok = test_redrat_basic_commands(redrat_host)
    if not basic_ok:
        print("❌ Basic RedRat commands failed")
        return
    
    print("\n" + "="*50)
    print("🎯 SIGNAL TESTING MENU")
    print("="*50)
    
    while True:
        print("\nSelect test:")
        print("1. Test with database signal")
        print("2. Test with simple pattern")
        print("3. Compare signals and analyze")
        print("4. Test multiple IR ports")
        print("5. Test different power levels")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == "1":
            cmd_name, template_data, remote_name = get_signal_from_database()
            if template_data:
                ir_data = extract_ir_data(template_data)
                if ir_data:
                    test_ir_transmission(redrat_host, 10001, ir_data, ir_port=1, power=50)
        
        elif choice == "2":
            test_with_simple_pattern(redrat_host)
        
        elif choice == "3":
            compare_with_working_signal()
        
        elif choice == "4":
            print("\n🔌 Testing different IR ports...")
            ir_data, _ = compare_with_working_signal()
            if ir_data:
                for port in [1, 2, 3, 4, 9]:  # Test common ports including 9
                    print(f"\nTesting IR port {port}:")
                    test_ir_transmission(redrat_host, 10001, ir_data, ir_port=port, power=50)
                    time.sleep(1)
        
        elif choice == "5":
            print("\n⚡ Testing different power levels...")
            ir_data, _ = compare_with_working_signal()
            if ir_data:
                for power in [25, 50, 75, 100]:
                    print(f"\nTesting power level {power}%:")
                    test_ir_transmission(redrat_host, 10001, ir_data, ir_port=1, power=power)
                    time.sleep(1)
        
        elif choice == "6":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()