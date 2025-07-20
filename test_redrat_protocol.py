#!/usr/bin/env python3
"""
RedRat Protocol Investigation and Testing
This script helps identify the correct protocol version and format
"""
import socket
import struct
import time
import binascii
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RedRatProtocolTester:
    def __init__(self, host, port=10001):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        """Connect to RedRat device"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from RedRat device"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def test_binary_protocol(self):
        """Test the current binary protocol"""
        logger.info("=== Testing Binary Protocol (Current) ===")
        
        # Try device version query
        message = struct.pack(">cHB", b"#", 0, 0x09)  # DEVICE_VERSION
        
        try:
            self.socket.sendall(message)
            logger.info(f"Sent binary: {binascii.hexlify(message).decode()}")
            
            # Try to receive response
            response = self.socket.recv(1024)
            logger.info(f"Received: {binascii.hexlify(response).decode()}")
            
            if response:
                logger.info("Binary protocol appears to work")
                return True
            
        except Exception as e:
            logger.error(f"Binary protocol failed: {e}")
        
        return False
    
    def test_ascii_protocols(self):
        """Test various ASCII/text protocols"""
        logger.info("=== Testing ASCII Protocols ===")
        
        ascii_tests = [
            # HTTP-style
            b"GET /version HTTP/1.1\r\nHost: " + self.host.encode() + b"\r\n\r\n",
            
            # AT command style
            b"AT+VERSION\r\n",
            b"ATI\r\n",
            
            # Simple text commands
            b"VERSION\r\n",
            b"version\r\n",
            b"DEVICE_VERSION\r\n",
            
            # JSON style
            b'{"command":"version"}\r\n',
            b'{"cmd":"device_version"}\r\n',
            
            # Custom RedRat style
            b"RR:VERSION\r\n",
            b"REDRAT:VERSION\r\n",
            b"IR:VERSION\r\n",
        ]
        
        for i, test_cmd in enumerate(ascii_tests, 1):
            logger.info(f"Test {i}: {test_cmd}")
            
            try:
                # Send command
                self.socket.sendall(test_cmd)
                
                # Try to receive response
                self.socket.settimeout(2)
                response = self.socket.recv(1024)
                
                if response:
                    logger.info(f"Response: {response}")
                    try:
                        ascii_resp = response.decode('ascii', errors='ignore')
                        logger.info(f"ASCII: {ascii_resp}")
                    except:
                        pass
                    
                    if len(response) > 4:  # Got substantial response
                        logger.info(f"*** ASCII protocol test {i} got response! ***")
                        return i, test_cmd, response
                
            except socket.timeout:
                logger.debug(f"Test {i} timed out")
            except Exception as e:
                logger.error(f"Test {i} failed: {e}")
                # Reset connection for next test
                self.disconnect()
                if not self.connect():
                    return None
        
        return None
    
    def test_websocket_protocol(self):
        """Test WebSocket-style protocol"""
        logger.info("=== Testing WebSocket Protocol ===")
        
        # Basic WebSocket handshake
        handshake = (
            b"GET / HTTP/1.1\r\n"
            b"Host: " + self.host.encode() + b"\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
            b"Sec-WebSocket-Version: 13\r\n"
            b"\r\n"
        )
        
        try:
            self.socket.sendall(handshake)
            response = self.socket.recv(1024)
            
            if b"101 Switching Protocols" in response:
                logger.info("WebSocket handshake successful!")
                logger.info(f"Response: {response}")
                return True
                
        except Exception as e:
            logger.error(f"WebSocket test failed: {e}")
        
        return False

def main():
    # Test with your RedRat device IP
    redrat_ip = input("Enter RedRat device IP (or press Enter for 192.168.1.100): ").strip()
    if not redrat_ip:
        redrat_ip = "192.168.1.100"
    
    print(f"\n=== Testing RedRat Protocol at {redrat_ip} ===\n")
    
    tester = RedRatProtocolTester(redrat_ip)
    
    if not tester.connect():
        print("Failed to connect to RedRat device")
        return
    
    try:
        # Test current binary protocol
        binary_works = tester.test_binary_protocol()
        
        # Reset connection
        tester.disconnect()
        tester.connect()
        
        # Test ASCII protocols
        ascii_result = tester.test_ascii_protocols()
        
        # Reset connection  
        tester.disconnect()
        tester.connect()
        
        # Test WebSocket
        websocket_works = tester.test_websocket_protocol()
        
        # Summary
        print("\n=== PROTOCOL TEST RESULTS ===")
        print(f"Binary protocol (current): {'WORKS' if binary_works else 'FAILED'}")
        print(f"ASCII protocols: {'FOUND' if ascii_result else 'NOT FOUND'}")
        print(f"WebSocket protocol: {'WORKS' if websocket_works else 'FAILED'}")
        
        if ascii_result:
            test_num, command, response = ascii_result
            print(f"\nASCII Protocol Details:")
            print(f"  Test #{test_num} succeeded")
            print(f"  Command: {command}")
            print(f"  Response: {response}")
            
        print(f"\nRecommendation:")
        if binary_works and not ascii_result:
            print("  Current binary protocol works. Protocol differences may be due to:")
            print("  - Different message sequencing")
            print("  - Different power/timing settings") 
            print("  - Firmware version differences")
        elif ascii_result:
            print("  ASCII protocol detected! Consider updating to use text commands.")
        else:
            print("  Unable to determine correct protocol. Check:")
            print("  - Device IP and port")
            print("  - Firewall settings")
            print("  - Device firmware version")
    
    finally:
        tester.disconnect()

if __name__ == "__main__":
    main()
