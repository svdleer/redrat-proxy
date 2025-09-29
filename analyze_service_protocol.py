#!/usr/bin/env python3

import scapy.all as scapy
import sys

def analyze_service_protocol(pcap_file):
    """Analyze the protocol packets sent by our service"""
    print(f"Analyzing service protocol from: {pcap_file}")
    print("=" * 60)
    
    packets = scapy.rdpcap(pcap_file)
    
    # Filter for TCP packets to the RedRat device
    redrat_packets = []
    for pkt in packets:
        if scapy.TCP in pkt and pkt[scapy.IP].dst == '172.16.6.62':
            redrat_packets.append(pkt)
    
    print(f"Found {len(redrat_packets)} packets to RedRat device")
    
    # Look for packets with payload (actual IR commands)
    command_packets = []
    for i, pkt in enumerate(redrat_packets):
        if scapy.Raw in pkt:
            payload = bytes(pkt[scapy.Raw])
            if len(payload) > 10:  # Skip small TCP handshake packets
                command_packets.append((i, pkt, payload))
                print(f"\nPacket {i}: {len(payload)} bytes")
                print(f"Hex: {payload.hex()}")
                
                # Try to identify protocol elements
                if len(payload) >= 4:
                    header = payload[:4]
                    print(f"Header: {header.hex()}")
                    
                    # Check for MK3/MK4 protocol markers
                    if payload[0] == 0x12:
                        print("Found OUTPUT_IR_SIGNAL (0x12) - MK3 protocol")
                    elif payload[0] == 0x30:
                        print("Found OUTPUT_IR_ASYNC (0x30) - MK4 protocol")
                    else:
                        print(f"Unknown command: 0x{payload[0]:02x}")
                
                # Look for signal data patterns
                if len(payload) > 20:
                    print(f"Potential signal data: {payload[20:40].hex()}...")
    
    if not command_packets:
        print("No IR command packets found!")
        print("Showing all packets to RedRat:")
        for i, pkt in enumerate(redrat_packets[:5]):  # Show first 5 packets
            if scapy.Raw in pkt:
                payload = bytes(pkt[scapy.Raw])
                print(f"Packet {i}: {len(payload)} bytes - {payload.hex()}")
    
    return command_packets

if __name__ == "__main__":
    pcap_file = "/tmp/service_protocol_test.pcap"
    analyze_service_protocol(pcap_file)