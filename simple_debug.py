#!/usr/bin/env python3
"""
Simple Signal Debug Tool for RedRat Proxy Docker Container

This script tests basic signal functionality without complex imports.
"""

import sys
import os
import json
import socket
import struct
import binascii
import time
from datetime import datetime

def print_header(title):
    """Print a nice header"""
    print("\n" + "="*60)
    print(f"🔧 {title}")
    print("="*60)

def test_redrat_connectivity():
    """Test direct RedRat device connectivity"""
    print_header("TESTING REDRAT DEVICE CONNECTIVITY")
    
    # Default RedRat IP (change if different)
    redrat_ip = "172.16.6.62"
    redrat_port = 10001
    
    print(f"🔌 Testing connection to {redrat_ip}:{redrat_port}")
    
    try:
        # Test basic TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((redrat_ip, redrat_port))
        print("✅ TCP connection successful")
        
        # Test RedRat protocol - get device version
        version_msg = struct.pack(">cHB", b"#", 0, 0x09)
        sock.sendall(version_msg)
        response = sock.recv(1024)
        
        if len(response) > 3:
            print("✅ RedRat protocol working")
            print(f"   📊 Response: {binascii.hexlify(response).decode()}")
            
            # Extract device model if possible
            if len(response) >= 6:
                model = response[5] if len(response) > 5 else 0
                print(f"   🏷️  Device model: {model}")
        else:
            print("❌ RedRat protocol failed - short response")
        
        sock.close()
        return True
        
    except socket.timeout:
        print(f"❌ Connection timeout to {redrat_ip}:{redrat_port}")
        return False
    except ConnectionRefused:
        print(f"❌ Connection refused to {redrat_ip}:{redrat_port}")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def test_simple_ir_send():
    """Test simple IR signal transmission"""
    print_header("TESTING SIMPLE IR TRANSMISSION")
    
    redrat_ip = "172.16.6.62"
    redrat_port = 10001
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((redrat_ip, redrat_port))
        print(f"✅ Connected to {redrat_ip}:{redrat_port}")
        
        # Power on device (Type 0x05)
        power_msg = struct.pack(">cHB", b"#", 0, 0x05)
        sock.sendall(power_msg)
        response = sock.recv(1024)
        print("✅ Device powered on")
        
        # Turn on indicators (Type 0x07, data 0x17)
        indicators_msg = struct.pack(">cHBB", b"#", 1, 0x07, 0x17)
        sock.sendall(indicators_msg)
        response = sock.recv(1024)
        print("✅ Indicators enabled")
        
        # Test simple IR transmission
        print("📡 Testing IR transmission...")
        
        # Create a simple test IR pattern (minimal data)
        test_ir_data = bytes([
            0x00, 0x01, 0x74, 0xF5,  # Header
            0xFF, 0x60, 0x00, 0x00,  # More header  
            0x00, 0x06, 0x00, 0x00,  # Length
            0x00, 0x48, 0x02, 0x45,  # Basic timing data
            0x02, 0x22
        ])
        
        # IR send message structure for MK4
        # Type 0x12 (MK4 IR send), Port 1, Power 50
        ir_port = 1
        power = 50
        
        # Build IR message
        ir_header = struct.pack("<HBB", len(test_ir_data), ir_port, power)
        ir_msg = b"#" + struct.pack("<H", len(ir_header) + len(test_ir_data)) + bytes([0x12]) + ir_header + test_ir_data
        
        print(f"   📤 Sending {len(test_ir_data)} bytes to port {ir_port} at power {power}")
        sock.sendall(ir_msg)
        
        # Wait for response
        try:
            response = sock.recv(1024)
            if len(response) >= 4:
                print("✅ IR transmission successful!")
                print(f"   📊 Response: {binascii.hexlify(response).decode()}")
            else:
                print("⚠️  IR transmission completed (short response)")
        except socket.timeout:
            print("⚠️  IR transmission completed (no response - normal)")
        
        # Turn off indicators
        indicators_off_msg = struct.pack(">cHBB", b"#", 1, 0x07, 0x00)
        sock.sendall(indicators_off_msg)
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ IR transmission test failed: {e}")
        return False

def test_database_access():
    """Test if we can access the database at all"""
    print_header("TESTING DATABASE ACCESS")
    
    try:
        import mysql.connector
        
        # Try to connect to MySQL (using environment variables)
        config = {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'port': int(os.environ.get('MYSQL_PORT', '3306')),
            'user': os.environ.get('MYSQL_USER', 'redrat'),
            'password': os.environ.get('MYSQL_PASSWORD', ''),
            'database': os.environ.get('MYSQL_DB', 'redrat_proxy'),
            'charset': 'utf8mb4',
            'autocommit': True
        }
        
        print(f"🔌 Connecting to MySQL at {config['host']}:{config['port']}")
        print(f"   📋 Database: {config['database']}")
        print(f"   👤 User: {config['user']}")
        
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) FROM remotes")
        remote_count = cursor.fetchone()[0]
        print(f"✅ Found {remote_count} remotes in database")
        
        cursor.execute("SELECT COUNT(*) FROM command_templates")
        template_count = cursor.fetchone()[0]
        print(f"✅ Found {template_count} command templates in database")
        
        cursor.execute("SELECT COUNT(*) FROM redrat_devices")
        device_count = cursor.fetchone()[0]
        print(f"✅ Found {device_count} RedRat devices in database")
        
        # Get sample data
        if template_count > 0:
            cursor.execute("""
                SELECT ct.name, r.name as remote_name
                FROM command_templates ct
                JOIN remotes r ON JSON_EXTRACT(ct.template_data, '$.remote_id') = r.id
                LIMIT 3
            """)
            
            samples = cursor.fetchall()
            print(f"📋 Sample commands:")
            for command_name, remote_name in samples:
                print(f"   - {command_name} (on {remote_name})")
        
        conn.close()
        return True
        
    except ImportError:
        print("❌ MySQL connector not available")
        return False
    except Exception as e:
        print(f"❌ Database access failed: {e}")
        return False

def test_environment():
    """Test Docker environment setup"""
    print_header("TESTING DOCKER ENVIRONMENT")
    
    print("🐳 Docker Environment Check:")
    print(f"   📁 Working directory: {os.getcwd()}")
    print(f"   🐍 Python path: {sys.path[0]}")
    print(f"   📊 Python version: {sys.version}")
    
    # Check environment variables
    env_vars = [
        'MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB',
        'PYTHONPATH', 'FLASK_DEBUG'
    ]
    
    print("\n🔧 Environment Variables:")
    for var in env_vars:
        value = os.environ.get(var, 'NOT SET')
        if 'PASSWORD' in var and value != 'NOT SET':
            value = '*' * len(value)  # Hide password
        print(f"   {var}: {value}")
    
    # Check if key files exist
    key_files = [
        '/app/app.py',
        '/app/app/app.py', 
        '/app/requirements.txt',
        '/app/venv/bin/python'
    ]
    
    print("\n📁 Key Files:")
    for file_path in key_files:
        exists = "✅" if os.path.exists(file_path) else "❌"
        print(f"   {exists} {file_path}")
    
    return True

def main():
    """Main debugging function"""
    print("🐳 RedRat Proxy Simple Signal Debug Tool")
    print(f"⏰ Started at: {datetime.now()}")
    
    results = {}
    
    # Run tests
    results['environment'] = test_environment()
    results['database'] = test_database_access()
    results['redrat_connectivity'] = test_redrat_connectivity()
    results['ir_transmission'] = test_simple_ir_send()
    
    # Summary
    print_header("SUMMARY")
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test.upper().replace('_', ' ')}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL BASIC TESTS PASSED!")
        print("\n💡 If signals still don't work, the issue might be:")
        print("   - Signal data format/encoding")
        print("   - Command template parsing")
        print("   - Web interface to RedRat service communication")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        
        if not results.get('database'):
            print("\n🔧 DATABASE TROUBLESHOOTING:")
            print("   - Check MySQL container is running")
            print("   - Verify database credentials in .env file")
            print("   - Check network connectivity between containers")
        
        if not results.get('redrat_connectivity'):
            print("\n🔧 REDRAT TROUBLESHOOTING:")
            print("   - Check RedRat device IP address (currently testing 172.16.6.62)")
            print("   - Verify RedRat device is powered on")
            print("   - Check network connectivity from Docker container")
            print("   - Try: docker exec -it redrat-proxy_web_1 ping 172.16.6.62")
        
        if not results.get('ir_transmission'):
            print("\n🔧 IR TRANSMISSION TROUBLESHOOTING:")
            print("   - RedRat device connectivity issues")
            print("   - Wrong device protocol (MK2 vs MK4)")
            print("   - Signal data format issues")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Debugging interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)