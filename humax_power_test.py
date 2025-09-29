#!/usr/bin/env python3
"""
HUMAX POWER Test for ERSPAN Comparison
Generates traffic using the exact working ASYNC protocol
"""
import socket
import struct
import time
import binascii

def send_humax_power_async():
    """Send HUMAX POWER using working ASYNC protocol (0x30) with sequence numbers"""
    print("🎯 Sending HUMAX POWER via ASYNC protocol (0x30)")
    print("Target: Port 9, Power 50")
    
    # HUMAX POWER signal data (193 bytes) - the working signal
    signal_data_hex = """00017343ff6300000018000000820245
5c236e04400d6504ef0b1400ec00df00e70095028c0006010c00a500210012000a00e7006000710095009700db11ff00
0102020202020202020202020202020202020202020202020202030202020202020202020202020202020202020202
0402020203020302030203020302030203027f0506070802090a0b0c0d040e020f0210111213140a1516161616
0a16161616160a161616161616160c1616160a160c161616161616160c1616161617027f"""
    
    # Clean and convert hex to bytes
    signal_data_hex = signal_data_hex.replace(' ', '').replace('\n', '')
    ir_data = bytes.fromhex(signal_data_hex)
    
    print(f"Signal: {len(ir_data)} bytes")
    print(f"Data starts with: {ir_data[:16].hex()}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect(('172.16.6.62', 10001))
        print("✅ Connected to RedRat device")
        
        sequence_number = 1
        
        # STEP 1: Get device version (with sequence number)
        print(f"📋 Step 1: Getting device version (seq={sequence_number})")
        version_msg = struct.pack(">cHBH", b"#", 2, 0x09, sequence_number)
        sock.sendall(version_msg)
        response = sock.recv(1024)
        print(f"   Response: {response.hex()}")
        sequence_number += 1
        time.sleep(0.1)
        
        # STEP 2: Power on device (with sequence number)
        print(f"⚡ Step 2: Power on device (seq={sequence_number})")
        power_msg = struct.pack(">cHBH", b"#", 2, 0x05, sequence_number)
        sock.sendall(power_msg)
        response = sock.recv(1024)
        print(f"   Response: {response.hex()}")
        sequence_number += 1
        time.sleep(0.1)
        
        # STEP 3: Send ASYNC IR data (0x30) with sequence number
        print(f"🚀 Step 3: Sending ASYNC IR data (0x30, seq={sequence_number})")
        
        # Port configuration (16 ports, port 9 = power 50, others = 0)
        ports = [0, 0, 0, 0, 0, 0, 0, 0, 50, 0, 0, 0, 0, 0, 0, 0]
        
        # Number of lengths (96 for this signal)
        num_lengths = 96
        
        # Build ASYNC payload: ports (16 bytes) + num_lengths (2 bytes) + signal_data
        async_payload = struct.pack("16BH", *ports, num_lengths) + ir_data
        
        # Message format: '#' + length + type + sequence + payload
        total_length = 2 + len(async_payload)  # 2 bytes for sequence + payload
        async_msg = struct.pack(">cHBH", b"#", total_length, 0x30, sequence_number) + async_payload
        
        sock.sendall(async_msg)
        print(f"   ASYNC message sent: {len(async_msg)} bytes")
        print(f"   Payload: ports + {num_lengths} lengths + {len(ir_data)} signal bytes")
        
        response = sock.recv(1024)
        print(f"   Response: {response.hex()}")
        sequence_number += 1
        time.sleep(0.1)
        
        # STEP 4: Trigger IR output (0x08) with sequence number
        print(f"🎯 Step 4: Triggering IR output (0x08, seq={sequence_number})")
        trigger_msg = struct.pack(">cHBH", b"#", 2, 0x08, sequence_number)
        sock.sendall(trigger_msg)
        response = sock.recv(1024)
        print(f"   Response: {response.hex()}")
        
        print("✅ HUMAX POWER command sequence completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

if __name__ == "__main__":
    print("🔥 HUMAX POWER Test - ASYNC Protocol with Sequence Numbers")
    print("="*60)
    send_humax_power_async()