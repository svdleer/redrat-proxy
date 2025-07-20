#!/bin/bash
# RedRat test with proper IR data format for MK4
# Fine: 42 euros - Fix the IR data format!

set -e

REMOTE_HOST="access-engineering.nl"
REMOTE_PORT="65001"
REMOTE_USER="svdleer"

echo "================================================"
echo "RedRat MK4 with Proper IR Data Format"
echo "Error 51 = Invalid IR data - let's fix it!"
echo "================================================"

# Create test with proper RedRat IR data format
cat > /tmp/proper_ir_test.py << 'EOF'
#!/usr/bin/env python3
import sys
import socket
import struct
import binascii
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_with_real_ir_data():
    """Test with properly formatted RedRat IR data"""
    print("Testing with proper RedRat IR data format...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("172.16.6.62", 10001))
        print("✓ Connected to RedRat MK4")
        
        # Power on first
        power_msg = struct.pack(">cHB", b"#", 0, 0x05)
        sock.sendall(power_msg)
        sock.recv(1024)
        print("✓ Powered on")
        
        # Use a real RedRat signal format (from a typical power command)
        # This is a properly formatted RedRat signal with correct header
        real_ir_data = binascii.unhexlify(
            "000174F5FF600000000600000048024502222F704540D12116A464F000000000000000000000000000000000000000000000" +
            "01020202020202020202020202020202020202020202030202020202020202020202030202020202020203020202030203020202030203020302020203027F0004027F"
        )
        
        print(f"Using real IR data: {len(real_ir_data)} bytes")
        print(f"IR data preview: {binascii.hexlify(real_ir_data[:20]).decode()}...")
        
        # Set up for async transmission
        ports = [50] + [0] * 15  # 50% power on port 1
        sequence_number = random.randint(0, 65535)
        delay = 0  # Default delay
        
        # Create the async message
        port_data = struct.pack("{}B".format(16), *ports)
        payload = struct.pack(">HH", sequence_number, delay) + port_data + real_ir_data
        message = struct.pack(">cHB", b"#", len(payload), 0x30) + payload
        
        print(f"Sending IR message: seq={sequence_number}, total_size={len(message)} bytes")
        sock.sendall(message)
        
        # Wait for response
        sock.settimeout(3)
        response = sock.recv(1024)
        print(f"✓ Response: {binascii.hexlify(response).decode()}")
        
        if len(response) >= 6:
            msg_len, msg_type = struct.unpack(">HB", response[0:3])
            if msg_type == 0x30:
                ack_seq, error_code, ack_flag = struct.unpack("<HBB", response[3:7])
                print(f"Response: seq={ack_seq}, error={error_code}, ack={ack_flag}")
                
                if ack_flag == 1 and error_code == 0:
                    print("✅ SUCCESS: IR signal accepted!")
                    
                    # Try to get completion (optional)
                    try:
                        sock.settimeout(1)
                        completion = sock.recv(1024)
                        print(f"✓ Completion: {binascii.hexlify(completion).decode()}")
                    except socket.timeout:
                        print("ℹ No completion message (normal for some signals)")
                    
                    sock.close()
                    return True
                else:
                    print(f"✗ IR rejected: error={error_code}, ack={ack_flag}")
                    # Common error codes:
                    # 51 = Invalid data format
                    # 52 = Data too long
                    # 53 = Invalid port
                    error_meanings = {
                        51: "Invalid IR data format",
                        52: "IR data too long", 
                        53: "Invalid port number",
                        54: "Invalid power level"
                    }
                    if error_code in error_meanings:
                        print(f"Error meaning: {error_meanings[error_code]}")
        
        sock.close()
        return False
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_simple_pattern():
    """Test with a very simple IR pattern"""
    print("\nTesting with minimal IR pattern...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("172.16.6.62", 10001))
        
        # Power on
        power_msg = struct.pack(">cHB", b"#", 0, 0x05)
        sock.sendall(power_msg)
        sock.recv(1024)
        
        # Create minimal valid IR signal
        # RedRat format: timing pairs in microseconds
        simple_pattern = struct.pack(">HHHHHHHH", 
            9000,       # 9ms mark
            0x8000 + 4500,  # 4.5ms space (MSB set for space)
            560,        # 560μs mark
            0x8000 + 560,   # 560μs space
            560,        # 560μs mark  
            0x8000 + 1690,  # 1.69ms space
            560,        # 560μs mark
            0x8000 + 10000  # 10ms final space
        )
        
        print(f"Simple pattern: {len(simple_pattern)} bytes")
        print(f"Pattern hex: {binascii.hexlify(simple_pattern).decode()}")
        
        # Send with async protocol
        ports = [30] + [0] * 15  # Lower power
        sequence_number = random.randint(0, 65535)
        delay = 0
        
        port_data = struct.pack("{}B".format(16), *ports)
        payload = struct.pack(">HH", sequence_number, delay) + port_data + simple_pattern
        message = struct.pack(">cHB", b"#", len(payload), 0x30) + payload
        
        sock.sendall(message)
        sock.settimeout(2)
        response = sock.recv(1024)
        
        if len(response) >= 6:
            msg_len, msg_type = struct.unpack(">HB", response[0:3])
            if msg_type == 0x30:
                ack_seq, error_code, ack_flag = struct.unpack("<HBB", response[3:7])
                print(f"Simple pattern result: error={error_code}, ack={ack_flag}")
                
                if ack_flag == 1 and error_code == 0:
                    print("✅ Simple pattern SUCCESS!")
                    sock.close()
                    return True
        
        sock.close()
        return False
        
    except Exception as e:
        print(f"Simple pattern failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing RedRat MK4 IR data formats...")
    
    # Try real IR data first
    success1 = test_with_real_ir_data()
    
    # Try simple pattern
    success2 = test_simple_pattern()
    
    if success1 or success2:
        print("\n🎉 SUCCESS: Found working IR format! No 42 euro fine!")
    else:
        print("\n💸 Still having IR data format issues...")
EOF

echo "Copying proper IR test to remote server..."
scp -P $REMOTE_PORT /tmp/proper_ir_test.py $REMOTE_USER@$REMOTE_HOST:/tmp/

echo "Running proper IR format test..."
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "python3 /tmp/proper_ir_test.py"

echo "================================================"
