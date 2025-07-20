#!/bin/bash
# Test with minimal IR data to isolate the protocol issue
# Fine: 42 euros - Let's debug the exact protocol step!

set -e

REMOTE_HOST="access-engineering.nl"
REMOTE_PORT="65001"
REMOTE_USER="svdleer"

echo "================================================"
echo "Debugging RedRat Protocol Step by Step"
echo "Fine: 42 euros - Protocol detective work!"
echo "================================================"

# Create a step-by-step protocol debug script
cat > /tmp/protocol_debug.py << 'EOF'
#!/usr/bin/env python3
import socket
import struct
import binascii
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_protocol_steps():
    """Test each protocol step individually to find where it fails"""
    print("Testing RedRat MK4 protocol step by step...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(("172.16.6.62", 10001))
        print("✓ Step 1: Connected")
        
        # Step 2: Device version
        version_msg = struct.pack(">cHB", b"#", 0, 0x09)
        sock.sendall(version_msg)
        response = sock.recv(1024)
        print(f"✓ Step 2: Device version OK: {binascii.hexlify(response).decode()}")
        
        # Step 3: Power on
        power_msg = struct.pack(">cHB", b"#", 0, 0x05)
        sock.sendall(power_msg)
        response = sock.recv(1024)
        print(f"✓ Step 3: Power on OK: {binascii.hexlify(response).decode()}")
        
        # Step 4: Reset (CPLD instruction 0x00)
        reset_msg = struct.pack(">cHBB", b"#", 1, 0x07, 0x00)
        sock.sendall(reset_msg)
        response = sock.recv(1024)
        print(f"✓ Step 4: Reset OK: {binascii.hexlify(response).decode()}")
        
        # Step 5: Indicators on (CPLD instruction 0x17)
        indicators_msg = struct.pack(">cHBB", b"#", 1, 0x07, 0x17)
        sock.sendall(indicators_msg)
        response = sock.recv(1024)
        print(f"✓ Step 5: Indicators on OK: {binascii.hexlify(response).decode()}")
        
        # Step 6: Set memory
        memory_msg = struct.pack(">cHB", b"#", 0, 0x10)
        sock.sendall(memory_msg)
        response = sock.recv(1024)
        print(f"✓ Step 6: Set memory OK: {binascii.hexlify(response).decode()}")
        
        # Step 7: CPLD instruction 0x00 again
        cpld_msg = struct.pack(">cHBB", b"#", 1, 0x07, 0x00)
        sock.sendall(cpld_msg)
        response = sock.recv(1024)
        print(f"✓ Step 7: CPLD 0x00 OK: {binascii.hexlify(response).decode()}")
        
        # Step 8: Port power setting (port 1 + 31 for high power)
        port_msg = struct.pack(">cHBB", b"#", 1, 0x07, 0x20)  # port 1 + 31 = 32 (0x20)
        sock.sendall(port_msg)
        response = sock.recv(1024)
        print(f"✓ Step 8: Port power OK: {binascii.hexlify(response).decode()}")
        
        # Step 9: Download signal - THIS IS WHERE IT MIGHT FAIL
        # Try with minimal IR data first
        minimal_data = bytes([0x23, 0x2C, 0x00, 0x64])  # 4 bytes
        
        print(f"Step 9: Downloading signal ({len(minimal_data)} bytes)...")
        print(f"Signal data: {binascii.hexlify(minimal_data).decode()}")
        
        signal_msg = struct.pack(f">cHB{len(minimal_data)}s", b"#", len(minimal_data), 0x11, minimal_data)
        print(f"Sending: {binascii.hexlify(signal_msg).decode()}")
        
        sock.sendall(signal_msg)
        sock.settimeout(5)  # Shorter timeout for this step
        response = sock.recv(1024)
        print(f"✓ Step 9: Download signal OK: {binascii.hexlify(response).decode()}")
        
        # Step 10: Output IR signal
        output_msg = struct.pack(">cHB", b"#", 0, 0x12)
        sock.sendall(output_msg)
        response = sock.recv(1024)
        print(f"✓ Step 10: Output signal OK: {binascii.hexlify(response).decode()}")
        
        # Step 11: Final reset
        final_reset = struct.pack(">cHBB", b"#", 1, 0x07, 0x00)
        sock.sendall(final_reset)
        response = sock.recv(1024)
        print(f"✓ Step 11: Final reset OK: {binascii.hexlify(response).decode()}")
        
        print("🎉 SUCCESS: All protocol steps completed!")
        sock.close()
        return True
        
    except Exception as e:
        print(f"✗ Protocol failed at step: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_real_signal():
    """Test with a real RedRat signal from the database format"""
    print("\nTesting with database-format signal...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(("172.16.6.62", 10001))
        
        # Quick setup
        steps = [
            (0x05, b""),           # Power on
            (0x07, bytes([0x00])), # Reset
            (0x07, bytes([0x17])), # Indicators on
            (0x10, b""),           # Set memory
            (0x07, bytes([0x00])), # CPLD 0x00
            (0x07, bytes([0x20])), # Port power
        ]
        
        for msg_type, data in steps:
            msg = struct.pack(f">cHB{len(data)}s", b"#", len(data), msg_type, data)
            sock.sendall(msg)
            sock.recv(1024)
        
        # Try with RedRat timing format (mark/space pairs)
        # Simple NEC-like pattern: 9ms mark, 4.5ms space, some data bits
        timing_data = struct.pack(">HHHHHHHH",
            9000,          # 9ms mark
            4500 | 0x8000, # 4.5ms space (MSB = space)
            560,           # 560µs mark
            560 | 0x8000,  # 560µs space
            560,           # 560µs mark
            1690 | 0x8000, # 1.69ms space
            560,           # 560µs mark
            10000 | 0x8000 # 10ms space
        )
        
        print(f"Trying timing format: {len(timing_data)} bytes")
        print(f"Data: {binascii.hexlify(timing_data).decode()}")
        
        signal_msg = struct.pack(f">cHB{len(timing_data)}s", b"#", len(timing_data), 0x11, timing_data)
        sock.sendall(signal_msg)
        
        sock.settimeout(3)
        response = sock.recv(1024)
        print(f"✓ Timing format accepted: {binascii.hexlify(response).decode()}")
        
        # Output the signal
        output_msg = struct.pack(">cHB", b"#", 0, 0x12)
        sock.sendall(output_msg)
        response = sock.recv(1024)
        print(f"✓ Signal output: {binascii.hexlify(response).decode()}")
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"Real signal test failed: {e}")
        return False

if __name__ == "__main__":
    print("RedRat Protocol Step-by-Step Debug")
    print("=" * 40)
    
    # Test basic protocol
    success1 = test_protocol_steps()
    
    # Test with timing data
    success2 = test_with_real_signal()
    
    if success1 or success2:
        print("\n🎉 Found working protocol! No 42 euro fine!")
    else:
        print("\n💸 Protocol issues persist...")
EOF

echo "Copying protocol debug script..."
scp -P $REMOTE_PORT /tmp/protocol_debug.py $REMOTE_USER@$REMOTE_HOST:/tmp/

echo "Running step-by-step protocol debug..."
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "python3 /tmp/protocol_debug.py"

echo "================================================"
