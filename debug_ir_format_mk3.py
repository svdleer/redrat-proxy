#!/usr/bin/env python3
"""
Debug IR data format for MK3 protocol
Focus on understanding what format the device expects
"""

import socket
import struct
import time
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def connect_to_device():
    """Connect to RedRat device"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)
    sock.connect(('172.16.6.62', 10001))
    return sock

def send_message(sock, msg_type, data=b''):
    """Send a message to the device"""
    header = struct.pack('<HH', len(data), msg_type)
    message = b'\x23' + header[1:] + data  # 0x23 prefix, skip first header byte
    logger.debug(f"Sending message: type=0x{msg_type:02x}, data_length={len(data)}")
    logger.debug(f"Message hex: {message.hex()}")
    sock.send(message)
    
def receive_response(sock):
    """Receive response from device"""
    # Read header
    header = sock.recv(4)
    if len(header) != 4:
        raise Exception(f"Invalid header length: {len(header)}")
    
    prefix, data_len, msg_type = struct.unpack('<BHB', header)
    logger.debug(f"Received response: type=0x{msg_type:02x}, data_length={data_len}")
    
    # Read data if present
    data = b''
    if data_len > 0:
        data = sock.recv(data_len)
        logger.debug(f"Response data hex: {data.hex()}")
    
    return msg_type, data

def test_simple_ir_formats():
    """Test different IR data formats to see what works"""
    
    # Test different IR data formats
    test_formats = [
        # Format 1: Simple timing pairs (on/off microseconds)
        {
            'name': 'Simple timing pairs',
            'data': struct.pack('<HHHHHHHH', 
                2000, 1000,  # Header burst/space
                500, 500,    # Bit 1
                500, 1500,   # Bit 0  
                500, 50000   # Final burst/gap
            )
        },
        
        # Format 2: RedRat protocol format (what we've been using)
        {
            'name': 'RedRat protocol format',
            'data': bytes.fromhex('2328d194023082300230869a0230a710')
        },
        
        # Format 3: Raw microsecond timing
        {
            'name': 'Raw microsecond timing',
            'data': struct.pack('<HHHH', 9000, 4500, 560, 560)
        },
        
        # Format 4: Minimal test pattern
        {
            'name': 'Minimal test pattern',
            'data': struct.pack('<HH', 1000, 1000)
        }
    ]
    
    sock = connect_to_device()
    
    try:
        # Get device version first
        send_message(sock, 0x09)
        msg_type, data = receive_response(sock)
        logger.info(f"Device version response: {data.hex()}")
        
        # Power on
        send_message(sock, 0x05)
        msg_type, data = receive_response(sock)
        logger.info("Device powered on")
        
        for test_format in test_formats:
            logger.info(f"\n=== Testing {test_format['name']} ===")
            logger.info(f"Data length: {len(test_format['data'])} bytes")
            logger.info(f"Data hex: {test_format['data'].hex()}")
            
            try:
                # Create MK3 async message
                seq_num = 12345
                delay = 0
                port_powers = [30] + [0] * 15  # Port 1 at power 30, rest off
                
                # MK3 async message format: seq(2) + delay(2) + ports(16) + ir_data
                msg_data = struct.pack('<HH', seq_num, delay)
                msg_data += struct.pack('B' * 16, *port_powers)
                msg_data += test_format['data']
                
                send_message(sock, 0x30, msg_data)  # MK3 async IR send
                msg_type, response_data = receive_response(sock)
                
                if len(response_data) >= 4:
                    resp_seq, error_code, ack = struct.unpack('<HBB', response_data[:4])
                    logger.info(f"Response: seq={resp_seq}, error={error_code}, ack={ack}")
                    
                    if error_code == 0:
                        logger.info("✓ SUCCESS! This format works")
                        break
                    else:
                        logger.info(f"✗ NACK with error code: {error_code}")
                else:
                    logger.info(f"Unexpected response: {response_data.hex()}")
                    
            except Exception as e:
                logger.error(f"Test failed: {e}")
                
        # Try to get more device info
        logger.info("\n=== Getting device capabilities ===")
        try:
            # Try message type 0x0A (device capabilities)
            send_message(sock, 0x0A)
            msg_type, data = receive_response(sock)
            logger.info(f"Device capabilities: {data.hex()}")
        except:
            logger.info("Device capabilities not available")
            
    finally:
        sock.close()

if __name__ == "__main__":
    test_simple_ir_formats()
