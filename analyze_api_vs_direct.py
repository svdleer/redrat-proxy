#!/usr/bin/env python3

import scapy.all as scapy

def analyze_api_vs_direct():
    """Compare API call vs direct library call protocols"""
    print("Analyzing API vs Direct Library Protocol Comparison")
    print("=" * 60)
    
    packets = scapy.rdpcap('/tmp/api_vs_direct.pcap')
    
    # Find all async/download commands
    command_packets = []
    for i, pkt in enumerate(packets):
        if scapy.TCP in pkt and scapy.Raw in pkt and pkt[scapy.IP].dst == '172.16.6.62':
            payload = bytes(pkt[scapy.Raw])
            if len(payload) > 20 and payload[0] == 0x23:  # '#' header
                length = (payload[1] << 8) | payload[2]
                msg_type = payload[3]
                if msg_type in [0x30, 0x11, 0x12]:  # ASYNC_OUTPUT, DOWNLOAD_SIGNAL, OUTPUT_SIGNAL
                    command_packets.append((i, msg_type, payload))
    
    print(f"Found {len(command_packets)} IR command packets")
    
    # Group by message type and analyze differences
    for i, (pkt_num, msg_type, payload) in enumerate(command_packets):
        type_names = {0x30: "ASYNC_OUTPUT", 0x11: "DOWNLOAD_SIGNAL", 0x12: "OUTPUT_SIGNAL"}
        type_name = type_names.get(msg_type, f"TYPE_0x{msg_type:02x}")
        
        print(f"\nPacket {i+1}: {type_name} ({len(payload)} bytes)")
        print(f"Full: {payload.hex()}")
        
        if msg_type == 0x30:  # ASYNC_OUTPUT - focus on data structure
            data = payload[4:]  # Skip header
            print(f"Async data: {data[:20].hex()}...")
            
            if len(data) >= 4:
                seq_num = (data[1] << 8) | data[0]  # Little-endian
                delay = (data[3] << 8) | data[2]    # Little-endian
                print(f"Sequence: {seq_num}, Delay: {delay}ms")
                
                # Check power levels (next 16 bytes)
                if len(data) >= 20:
                    power_levels = data[4:20]
                    active_ports = [i+1 for i, power in enumerate(power_levels) if power > 0]
                    print(f"Active ports: {active_ports}")

if __name__ == "__main__":
    analyze_api_vs_direct()