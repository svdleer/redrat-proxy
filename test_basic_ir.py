#!/usr/bin/env python3
"""
Simple RedRat Connection and Basic IR Test
Tests basic connectivity and IR transmission
"""

import socket
import struct
import time
import binascii
import sys
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_connection(host, port=10001):
    """Test basic TCP connection to RedRat"""
    logger.info(f"Testing connection to {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        logger.info("✓ Connection successful")
        sock.close()
        return True
    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        return False

def test_redrat_protocol(host, port=10001):
    """Test RedRat protocol communication"""
    logger.info(f"Testing RedRat protocol on {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        # Send device version query (Type 0x09)
        message = struct.pack(">cHB", b"#", 0, 0x09)
        logger.info(f"Sending device version query: {binascii.hexlify(message).decode()}")
        
        sock.sendall(message)
        
        # Try to receive response
        response = sock.recv(1024)
        logger.info(f"Received response: {binascii.hexlify(response).decode()}")
        
        if len(response) > 3:
            logger.info("✓ Protocol communication successful")
            result = True
        else:
            logger.warning("Protocol response too short")
            result = False
            
        sock.close()
        return result
        
    except Exception as e:
        logger.error(f"✗ Protocol test failed: {e}")
        return False

def test_simple_ir_send(host, port=10001):
    """Test simple IR signal transmission"""
    logger.info(f"Testing IR transmission on {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        # Simple NEC-style IR pattern for testing
        test_pattern = [
            9000, -4500,     # Lead-in
            560, -560,       # Bit 0
            560, -1690,      # Bit 1
            560, -1690,      # Bit 1
            560, -560,       # Bit 0
            560, -39000      # End gap
        ]
        
        logger.info(f"Test pattern: {len(test_pattern)} elements")
        
        # Create IR send message (Type 0x23)
        ir_port = 1
        power = 50
        num_elements = len(test_pattern)
        
        # Pack the IR data
        ir_data = b""
        for value in test_pattern:
            if value > 0:
                # Positive values (mark periods)
                ir_data += struct.pack(">H", value)
            else:
                # Negative values (space periods) - convert to positive and set MSB
                ir_data += struct.pack(">H", (-value) | 0x8000)
        
        # Create the message header
        # Format: # + length + 0x23 + port + power + data
        payload = struct.pack(">BB", ir_port, power) + ir_data
        length = len(payload)
        
        message = struct.pack(">cHB", b"#", length, 0x23) + payload
        
        logger.info(f"Sending IR message: {len(message)} bytes")
        logger.info(f"Message header: {binascii.hexlify(message[:5]).decode()}")
        
        sock.sendall(message)
        
        # Wait for response
        response = sock.recv(1024)
        logger.info(f"IR send response: {binascii.hexlify(response).decode()}")
        
        if len(response) >= 4:
            # Check if it's an ACK response
            if response[0:1] == b"#" and len(response) >= 4:
                msg_type = response[3] if len(response) > 3 else 0
                logger.info(f"Response message type: 0x{msg_type:02x}")
                
                if msg_type == 0x00:  # ACK
                    logger.info("✓ IR transmission acknowledged")
                    result = True
                else:
                    logger.warning(f"Unexpected response type: 0x{msg_type:02x}")
                    result = False
            else:
                logger.warning("Invalid response format")
                result = False
        else:
            logger.warning("No proper response received")
            result = False
            
        sock.close()
        return result
        
    except Exception as e:
        logger.error(f"✗ IR transmission test failed: {e}")
        return False

def main():
    """Main test function"""
    print("RedRat Basic Connection and IR Test")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python test_basic_ir.py <redrat_host> [port]")
        print("Example: python test_basic_ir.py 192.168.1.100")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 10001
    
    print(f"Testing RedRat at {host}:{port}")
    print("-" * 30)
    
    # Run tests
    tests = [
        ("Connection Test", lambda: test_connection(host, port)),
        ("Protocol Test", lambda: test_redrat_protocol(host, port)),
        ("IR Transmission Test", lambda: test_simple_ir_send(host, port))
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}...")
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name}: {status}")
        if not success:
            all_passed = False
    
    print("\nDIAGNOSIS:")
    if results[0][1]:  # Connection test passed
        if results[1][1]:  # Protocol test passed
            if results[2][1]:  # IR test passed
                print("✓ All tests passed! RedRat device is working correctly.")
                print("  Issue may be in the application logic or database.")
            else:
                print("✗ IR transmission failed but connection/protocol OK.")
                print("  Check IR port settings, power levels, or signal format.")
        else:
            print("✗ Protocol communication failed.")
            print("  Check device firmware version or protocol implementation.")
    else:
        print("✗ Cannot connect to RedRat device.")
        print("  Check IP address, network connectivity, and device power.")
    
    print(f"\nDevice tested: {host}:{port}")
    print("If official RedRat tool works with same device, compare protocol details.")

if __name__ == "__main__":
    main()
