#!/usr/bin/env python3

import scapy.all as scapy
import sys

def analyze_working_protocol(pcap_file):
    """Analyze the working protocol from send_test_signal_new.py"""
    print(f"Analyzing working protocol from: {pcap_file}")
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
                print(f"Full hex: {payload.hex()}")
                
                # Analyze structure
                if len(payload) >= 4:
                    if payload[0] == 0x23:  # '#' character
                        length = (payload[1] << 8) | payload[2]  # Big-endian length
                        msg_type = payload[3]
                        print(f"Structure: '#' + length({length}) + type(0x{msg_type:02x}) + data")
                        
                        # Identify message type
                        type_names = {
                            0x04: "MSG_READ_FIRMWARE",
                            0x05: "MSG_CPLD_POWER_ON", 
                            0x07: "MSG_CPLD_INSTRUCTION",
                            0x08: "MSG_READ_SERIAL",
                            0x10: "MSG_ALLOCATE_MEMORY",
                            0x11: "MSG_DOWNLOAD_SIGNAL",
                            0x12: "MSG_OUTPUT_SIGNAL",
                            0x30: "MSG_ASYNC_OUTPUT"
                        }
                        type_name = type_names.get(msg_type, f"UNKNOWN_0x{msg_type:02x}")
                        print(f"Message type: {type_name}")
                        
                        if len(payload) > 4:
                            data_part = payload[4:]
                            print(f"Data: {data_part[:20].hex()}{'...' if len(data_part) > 20 else ''}")
                    else:
                        print(f"Unexpected first byte: 0x{payload[0]:02x}")
    
    return command_packets

if __name__ == "__main__":
    pcap_file = "/tmp/working_protocol.pcap"
    analyze_working_protocol(pcap_file)