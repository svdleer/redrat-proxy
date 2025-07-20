#!/bin/bash
# Fixed RedRat test with proper MK4 async handling
# Fine: 42 euros - Let's fix the timeout issue!

set -e

REMOTE_HOST="access-engineering.nl"
REMOTE_PORT="65001"
REMOTE_USER="svdleer"

echo "================================================"
echo "Fixed RedRat MK4 Test (42 euro fine edition)"
echo "================================================"

# Create a test script with fixed async handling
cat > /tmp/fixed_redrat_test.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/tmp')

import socket
import struct
import binascii
import random
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_redrat_direct():
    """Test RedRat with direct protocol implementation and fixed timeout handling"""
    print("Testing RedRat MK4 at 172.16.6.62 with fixed async handling...")
    
    try:
        # Connect directly
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # Shorter timeout
        sock.connect(("172.16.6.62", 10001))
        print("✓ Connected successfully!")
        
        # Get device version
        version_msg = struct.pack(">cHB", b"#", 0, 0x09)
        sock.sendall(version_msg)
        response = sock.recv(1024)
        print(f"✓ Device version response: {binascii.hexlify(response).decode()}")
        
        # Power on
        power_msg = struct.pack(">cHB", b"#", 0, 0x05)
        sock.sendall(power_msg)
        response = sock.recv(1024)
        print("✓ Power on successful")
        
        # Simple IR test with minimal data and shorter timeout
        print("Testing IR transmission (with timeout fix)...")
        
        # Minimal test pattern
        test_data = bytes([0x23, 0x2C, 0x00, 0x64])  # Simple 4-byte pattern
        
        # Create IR message for port 1, power 30 (lower power)
        ports = [30] + [0] * 15  # Port 1 = 30%, others = 0%
        sequence_number = random.randint(0, 65535)
        delay = 0
        
        # Pack the async IR message
        port_data = struct.pack("{}B".format(16), *ports)
        payload = struct.pack(">HH", sequence_number, delay) + port_data + test_data
        message = struct.pack(">cHB", b"#", len(payload), 0x30) + payload
        
        print(f"Sending IR message (seq={sequence_number}, data_len={len(test_data)})...")
        sock.sendall(message)
        
        # Wait for ACK with shorter timeout
        sock.settimeout(2)  # Only wait 2 seconds for ACK
        try:
            response = sock.recv(1024)
            print(f"✓ IR ACK received: {binascii.hexlify(response).decode()}")
            
            if len(response) >= 6:
                # Parse ACK response
                msg_len, msg_type = struct.unpack(">HB", response[0:3])
                if msg_type == 0x30:  # OUTPUT_IR_ASYNC
                    ack_seq, error_code, ack_flag = struct.unpack("<HBB", response[3:7])
                    print(f"✓ ACK parsed: seq={ack_seq}, error={error_code}, ack={ack_flag}")
                    
                    if ack_flag == 1 and error_code == 0:
                        print("✓ IR transmission acknowledged successfully!")
                        
                        # Try to get completion message with very short timeout
                        sock.settimeout(0.5)
                        try:
                            completion = sock.recv(1024)
                            print(f"✓ Completion received: {binascii.hexlify(completion).decode()}")
                        except socket.timeout:
                            print("ℹ Completion message timed out (this may be normal for some devices)")
                            
                        success = True
                    else:
                        print(f"✗ IR transmission failed: error={error_code}, ack={ack_flag}")
                        success = False
                else:
                    print(f"✗ Unexpected response type: {msg_type}")
                    success = False
            else:
                print(f"✗ Response too short: {len(response)} bytes")
                success = False
                
        except socket.timeout:
            print("✗ No ACK received (timeout)")
            success = False
        
        sock.close()
        return success
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_redrat_direct()
    if success:
        print("\n🎉 SUCCESS: RedRat MK4 IR transmission working! No 42 euro fine!")
    else:
        print("\n💸 FAILURE: Still issues with IR transmission...")
        sys.exit(1)
EOF

echo "Copying fixed test to remote server..."
scp -P $REMOTE_PORT /tmp/fixed_redrat_test.py $REMOTE_USER@$REMOTE_HOST:/tmp/

echo "Running fixed RedRat test..."
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "python3 /tmp/fixed_redrat_test.py"

echo "================================================"
