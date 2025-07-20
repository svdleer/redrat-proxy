#!/usr/bin/env python3
"""
Analyze RedRat protocol differences and test ASCII vs binary encoding
"""
import struct
import binascii
import socket
import scapy.all as scapy
from scapy.layers.inet import IP, TCP

def analyze_binary_protocol():
    """Show how the current library encodes messages"""
    print("=== CURRENT BINARY PROTOCOL (redratlib.py) ===")
    
    # Example: DOWNLOAD_SIGNAL message (type 0x11)
    sample_ir_data = b"\x00\x01\x74\xf8\x12\x34"  # Sample IR data
    
    # Binary message format: '#' + length(2) + type(1) + data
    message_type = 0x11  # DOWNLOAD_SIGNAL
    message_data = sample_ir_data
    
    message = struct.pack(
        ">cHB%ds" % len(message_data),
        b"#",                # Start marker
        len(message_data),   # Data length (big-endian ushort)
        message_type,        # Message type
        message_data         # IR data
    )
    
    print(f"Message type: 0x{message_type:02x} (DOWNLOAD_SIGNAL)")
    print(f"Data length: {len(message_data)} bytes")
    print(f"Full message: {binascii.hexlify(message).decode()}")
    print(f"Message breakdown:")
    print(f"  Start: {message[0:1]} (0x{message[0]:02x})")
    print(f"  Length: {struct.unpack('>H', message[1:3])[0]}")  
    print(f"  Type: 0x{message[3]:02x}")
    print(f"  Data: {binascii.hexlify(message[4:]).decode()}")
    print()

def analyze_official_packets(pcap_file):
    """Analyze packets from official RedRat tool"""
    print(f"=== ANALYZING OFFICIAL TOOL PACKETS: {pcap_file} ===")
    
    try:
        packets = scapy.rdpcap(pcap_file)
        tcp_packets = [p for p in packets if TCP in p and len(p[TCP].payload) > 0]
        
        print(f"Found {len(tcp_packets)} TCP packets with payload")
        
        for i, packet in enumerate(tcp_packets[:5]):  # Analyze first 5 packets
            payload = bytes(packet[TCP].payload)
            
            print(f"\nPacket {i+1}:")
            print(f"  Length: {len(payload)} bytes")
            print(f"  Hex: {binascii.hexlify(payload).decode()}")
            
            # Try to decode as ASCII/text
            try:
                ascii_data = payload.decode('ascii', errors='ignore')
                printable = ''.join(c if c.isprintable() else '.' for c in ascii_data)
                print(f"  ASCII: {printable}")
                
                # Look for common patterns
                if ascii_data.startswith('AT'):
                    print("  -> Looks like AT command protocol!")
                elif any(cmd in ascii_data.upper() for cmd in ['SEND', 'IR', 'POWER', 'PORT']):
                    print("  -> Looks like text-based IR command!")
                    
            except:
                print("  ASCII: Not decodable as ASCII")
            
            # Check if it matches binary protocol
            if len(payload) >= 4 and payload[0:1] == b'#':
                try:
                    length = struct.unpack('>H', payload[1:3])[0]
                    msg_type = payload[3]
                    print(f"  -> Matches binary protocol: type=0x{msg_type:02x}, length={length}")
                except:
                    print("  -> Doesn't match binary protocol")
                    
    except Exception as e:
        print(f"Error analyzing {pcap_file}: {e}")
        return
    print()

def suggest_fixes():
    """Suggest potential fixes based on analysis"""
    print("=== POTENTIAL PROTOCOL DIFFERENCES ===")
    print()
    print("1. ENCODING FORMAT:")
    print("   - Current library: Binary protocol with '#' + length + type + data")
    print("   - Official tool: Likely ASCII/text-based commands")
    print()
    print("2. POSSIBLE ASCII PROTOCOL:")
    print("   - Commands like: 'SEND PORT=1 POWER=50 DATA=<hex>'")  
    print("   - Or AT-style: 'AT+IRSEND=1,50,<hex>\\r\\n'")
    print("   - Or JSON: '{\"command\":\"send\",\"port\":1,\"power\":50,\"data\":\"<hex>\"}'")
    print()
    print("3. RECOMMENDED INVESTIGATION:")
    print("   - Check RedRat documentation for protocol versions")
    print("   - Test with ASCII command format")
    print("   - Compare timing and response patterns")
    print()

if __name__ == "__main__":
    # Analyze current binary protocol
    analyze_binary_protocol()
    
    # Try to analyze official tool packets
    official_pcap = "capture_official_POWER_223445.pcap"
    proxy_pcap = "capture_proxy_POWER_223416.pcap"
    
    for pcap_file in [official_pcap, proxy_pcap]:
        try:
            analyze_official_packets(pcap_file)
        except FileNotFoundError:
            print(f"File {pcap_file} not found - skipping analysis")
    
    suggest_fixes()
