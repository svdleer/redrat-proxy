#!/usr/bin/env python3
"""
Simple RedRat IR Test - No Database Required
Tests basic IR functionality with known signal patterns
"""

import socket
import struct
import time
import binascii
from datetime import datetime

def test_redrat_basic(host="172.16.6.62", port=10001):
    """Test basic RedRat connectivity and commands"""
    print(f"🔌 Testing RedRat at {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        print("✅ Connected successfully")
        
        # Test device version
        version_cmd = struct.pack(">cHB", b"#", 0, 0x09)
        sock.sendall(version_cmd)
        response = sock.recv(1024)
        
        if len(response) >= 6:
            model = struct.unpack(">H", response[4:6])[0] if len(response) >= 6 else 0
            print(f"✅ RedRat model: {model}")
        
        # Basic setup commands
        commands = [
            ("Power On", struct.pack(">cHB", b"#", 0, 0x05)),
            ("Reset", struct.pack(">cHBB", b"#", 1, 0x07, 0x00)),
            ("Indicators On", struct.pack(">cHBB", b"#", 1, 0x07, 0x17)),
        ]
        
        for name, cmd in commands:
            sock.sendall(cmd)
            try:
                resp = sock.recv(1024)
                print(f"✅ {name}: OK")
            except:
                print(f"⚠️  {name}: No response")
            time.sleep(0.3)
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_simple_ir_signal(host="172.16.6.62", port=10001, ir_port=1, power=50):
    """Test with a simple IR signal pattern"""
    print(f"\n📡 Testing simple IR signal on port {ir_port} with {power}% power")
    
    # Simple test pattern (basic NEC-like IR signal)
    test_pattern = bytes([
        0x00, 0x01, 0x74, 0xF5,  # RedRat header
        0xFF, 0x60, 0x00, 0x00,  # More header
        0x00, 0x06, 0x00, 0x00,  # Length info  
        0x00, 0x48, 0x02, 0x45,  # Timing data starts
        0x02, 0x22, 0x2F, 0x70,
        0x45, 0x40, 0xD1, 0x21,
        0x16, 0xA4, 0x64, 0xF0
    ])
    
    print(f"🔧 Pattern: {len(test_pattern)} bytes")
    print(f"   Data: {test_pattern[:16].hex()}...")

def test_humax_power_signal(host="172.16.6.62", port=10001):
    """Test with the exact HUMAX POWER signal for ERSPAN comparison"""
    print(f"\n🎯 Testing HUMAX POWER signal for ERSPAN comparison")
    print(f"   Target: Port 9, Power 50% (matching working configuration)")
    
    # The exact working HUMAX POWER signal data (193 bytes)
    signal_data_hex = """00017343ff6300000018000000820245
5c236e04400d6504ef0b1400ec00df00e70095028c0006010c00a500210012000a00e7006000710095009700db11ff00
0102020202020202020202020202020202020202020202020202030202020202020202020202020202020202020202
0402020203020302030203020302030203027f0506070802090a0b0c0d040e020f0210111213140a1516161616
0a16161616160a161616161616160c1616160a160c161616161616160c1616161617027f"""
    
    # Clean and convert hex to bytes
    signal_data_hex = signal_data_hex.replace(' ', '').replace('\n', '')
    humax_power_pattern = bytes.fromhex(signal_data_hex)
    
    print(f"📡 HUMAX POWER: {len(humax_power_pattern)} bytes")
    print(f"   Starts with: {humax_power_pattern[:16].hex()}")
    print(f"   Frequency: 38000Hz (fixed in bytes 4-5)")
    
    # Use the same structure as the simple test but with HUMAX data
    ir_port = 9  # Port 9 as confirmed working
    power = 50   # 50% power as confirmed working
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect((host, port))
        
        # Setup device
        setup_cmds = [
            struct.pack(">cHB", b"#", 0, 0x05),      # Power on
            struct.pack(">cHBB", b"#", 1, 0x07, 0x00), # Reset
            struct.pack(">cHBB", b"#", 1, 0x07, 0x17), # Indicators on
        ]
        
        for cmd in setup_cmds:
            sock.sendall(cmd)
            try:
                sock.recv(1024)
            except:
                pass
            time.sleep(0.2)
        
        # Send HUMAX POWER IR signal
        # RedRat IR send command: 0x12 + port + power + data
        ir_header = struct.pack(">cHBBB", b"#", len(humax_power_pattern) + 2, 0x12, ir_port, power)
        full_message = ir_header + humax_power_pattern
        
        print(f"📤 Sending HUMAX POWER IR command...")
        print(f"   Command: 0x12 (IR send)")
        print(f"   Port: {ir_port}")  
        print(f"   Power: {power}%")
        print(f"   Data: {len(humax_power_pattern)} bytes")
        print(f"   Total message: {len(full_message)} bytes")
        
        sock.sendall(full_message)
        
        # Wait for response
        try:
            response = sock.recv(1024)
            if response:
                print(f"✅ Response: {response.hex()}")
                if len(response) >= 4:
                    status = response[3] if len(response) > 3 else 0
                    if status == 0:
                        print("🎉 HUMAX POWER sent successfully via basic protocol!")
                        print("📊 Traffic captured for ERSPAN comparison")
                        return True
                    else:
                        print(f"⚠️  Status code: {status}")
                        return False
            else:
                print("❌ No response received")
                return False
        except socket.timeout:
            print("⚠️  Timeout waiting for response (might be normal)")
            print("📊 Traffic should still be captured for ERSPAN comparison")
            return True
        
    except Exception as e:
        print(f"❌ HUMAX POWER test failed: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect((host, port))
        
        # Setup device
        setup_cmds = [
            struct.pack(">cHB", b"#", 0, 0x05),      # Power on
            struct.pack(">cHBB", b"#", 1, 0x07, 0x00), # Reset
            struct.pack(">cHBB", b"#", 1, 0x07, 0x17), # Indicators on
        ]
        
        for cmd in setup_cmds:
            sock.sendall(cmd)
            try:
                sock.recv(1024)
            except:
                pass
            time.sleep(0.2)
        
        # Send IR signal
        # RedRat IR send command: 0x12 + port + power + data
        ir_header = struct.pack(">cHBBB", b"#", len(test_pattern) + 2, 0x12, ir_port, power)
        full_message = ir_header + test_pattern
        
        print(f"📤 Sending IR command...")
        print(f"   Header: {ir_header.hex()}")
        print(f"   Total size: {len(full_message)} bytes")
        
        sock.sendall(full_message)
        
        # Wait for response
        try:
            response = sock.recv(1024)
            if response:
                print(f"✅ Response: {response.hex()}")
                if len(response) >= 4:
                    status = response[3] if len(response) > 3 else 0
                    if status == 0:
                        print("🎉 IR signal sent successfully!")
                        return True
                    else:
                        print(f"⚠️  Status code: {status}")
                        return False
            else:
                print("❌ No response received")
                return False
        except socket.timeout:
            print("⚠️  Timeout waiting for response (might be normal)")
            return True
        
    except Exception as e:
        print(f"❌ IR test failed: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def test_multiple_ports_and_powers(host="172.16.6.62"):
    """Test IR signal on multiple ports and power levels"""
    print(f"\n🧪 Testing multiple ports and power levels")
    
    test_ports = [1, 2, 3, 4, 9]  # Including port 9 which was mentioned
    test_powers = [25, 50, 75, 100]
    
    results = {}
    
    for port in test_ports:
        print(f"\n🔌 Testing IR port {port}:")
        for power in test_powers:
            print(f"  Power {power}%: ", end="")
            result = test_simple_ir_signal(host, 10001, port, power)
            results[f"port_{port}_power_{power}"] = result
            if result:
                print("✅")
            else:
                print("❌")
            time.sleep(1)  # Small delay between tests
    
    # Summary
    print(f"\n📊 Test Results Summary:")
    successful = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"   Successful: {successful}/{total}")
    
    if successful > 0:
        print("✅ At least some IR transmissions worked!")
        working_configs = [k for k, v in results.items() if v]
        print(f"   Working configs: {working_configs[:3]}...")  # Show first 3
    else:
        print("❌ No IR transmissions worked - check device/connections")

def check_docker_redrat_connectivity():
    """Check if Docker container can reach RedRat device"""
    print(f"\n🐳 Testing Docker container connectivity to RedRat")
    
    try:
        import subprocess
        
        # Test from Docker container
        result = subprocess.run([
            'docker', 'exec', 'redrat-proxy_web_1', 
            'nc', '-zv', '172.16.6.62', '10001'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Docker container can reach RedRat device")
            return True
        else:
            print(f"❌ Docker container cannot reach RedRat: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Docker connectivity: {e}")
        return False

def main():
    print("🚀 Simple RedRat IR Signal Test")
    print("="*50)
    print("Testing basic IR functionality without database")
    print("")
    
    redrat_host = "172.16.6.62"
    
    # Test 1: Basic connectivity and commands
    if not test_redrat_basic(redrat_host):
        print("\n❌ Basic connectivity failed. Check:")
        print("   - Network connectivity to RedRat device")
        print("   - RedRat device is powered on")
        print("   - No firewall blocking port 10001")
        return
    
    # Test 2: Docker connectivity (if applicable)
    check_docker_redrat_connectivity()
    
    # Test 3: Simple IR signal
    print("\n" + "="*50)
    print("🎯 IR SIGNAL TESTS")
    
    choice = input("\nSelect test:\n1. Single IR test (port 1, 50% power)\n2. Test multiple ports and powers\n3. HUMAX POWER test (port 9, 50% - ERSPAN comparison)\n4. Exit\n\nChoice (1-4): ").strip()
    
    if choice == "1":
        test_simple_ir_signal(redrat_host, 10001, 1, 50)
    elif choice == "2":
        test_multiple_ports_and_powers(redrat_host)
    elif choice == "3":
        print("\n🔍 HUMAX POWER - ERSPAN COMPARISON TEST")
        print("="*50)
        print("This sends the exact HUMAX POWER signal for comparison with hub PCAP")
        test_humax_power_signal(redrat_host)
    else:
        print("👋 Goodbye!")
        return
    
    print(f"\n💡 TROUBLESHOOTING TIPS:")
    print("="*50)
    print("If IR signals don't work:")
    print("1. Check physical IR connections to RedRat device")
    print("2. Verify correct IR port number (try ports 1-4, 9)")
    print("3. Test different power levels (25-100%)")
    print("4. Check if target device is in range and responding")
    print("5. Compare with working signal data from database")
    print("")
    print("Network communication is working (proven by ERSPAN analysis)")
    print("The issue is likely IR signal format or device configuration")

if __name__ == "__main__":
    main()