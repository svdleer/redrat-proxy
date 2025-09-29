#!/usr/bin/env python3
"""
Packet-by-packet comparison of hub vs proxy RedRat traffic.
Extracts the actual RedRat protocol messages and compares them byte-for-byte.
"""

import subprocess
import re
import sys

def extract_redrat_packets(pcap_file, description):
    """Extract RedRat protocol packets from PCAP file."""
    print(f"\n{'='*60}")
    print(f"EXTRACTING {description}")
    print(f"{'='*60}")
    
    try:
        # Extract packets with RedRat protocol data (looking for 0x23 magic bytes)
        cmd = f"tcpdump -r {pcap_file} -nn -X | grep -A 10 -B 2 '2300'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        packets = []
        current_packet = None
        
        for line in result.stdout.split('\n'):
            # Look for hex data lines
            if re.match(r'\s+0x[0-9a-f]+:', line):
                hex_part = line.split(':', 1)[1].strip()
                # Extract hex bytes from the line
                hex_bytes = re.findall(r'[0-9a-f]{2}', hex_part.split()[0:16])  # First 16 hex values
                if current_packet is not None:
                    current_packet['hex_data'].extend(hex_bytes)
            
            # Look for RedRat protocol data (0x23 0x00)
            elif '2300' in line and '0x' in line:
                if current_packet:
                    packets.append(current_packet)
                
                # Extract timestamp and direction info
                timestamp_match = re.search(r'(\d+:\d+:\d+\.\d+)', line)
                direction_match = re.search(r'(In|Out)', line)
                
                current_packet = {
                    'timestamp': timestamp_match.group(1) if timestamp_match else 'unknown',
                    'direction': direction_match.group(1) if direction_match else 'unknown',
                    'hex_data': []
                }
                
                # Extract hex data from this line too
                hex_part = line.split(':', 1)[1].strip() if ':' in line else line
                hex_bytes = re.findall(r'[0-9a-f]{2}', hex_part)
                current_packet['hex_data'].extend(hex_bytes)
        
        if current_packet:
            packets.append(current_packet)
        
        print(f"Found {len(packets)} RedRat protocol packets")
        return packets
        
    except Exception as e:
        print(f"Error extracting packets from {pcap_file}: {e}")
        return []

def find_redrat_protocol_data(hex_data):
    """Find and extract RedRat protocol message from hex data."""
    hex_str = ''.join(hex_data)
    
    # Look for 0x2300 pattern (RedRat protocol header)
    pattern = '2300'
    pos = hex_str.find(pattern)
    
    if pos >= 0:
        # Extract the protocol message starting from 0x23
        protocol_start = pos
        protocol_hex = hex_str[protocol_start:]
        
        # Convert back to byte array for easier handling
        protocol_bytes = []
        for i in range(0, len(protocol_hex), 2):
            if i + 1 < len(protocol_hex):
                protocol_bytes.append(protocol_hex[i:i+2])
        
        return protocol_bytes
    
    return []

def compare_packets(hub_packets, proxy_packets):
    """Compare hub and proxy packets side by side."""
    print(f"\n{'='*80}")
    print(f"PACKET-BY-PACKET COMPARISON")
    print(f"{'='*80}")
    
    max_packets = max(len(hub_packets), len(proxy_packets))
    
    for i in range(max_packets):
        print(f"\n--- PACKET {i+1} ---")
        
        # Hub packet
        if i < len(hub_packets):
            hub_packet = hub_packets[i]
            hub_protocol = find_redrat_protocol_data(hub_packet['hex_data'])
            print(f"HUB     [{hub_packet['timestamp']}] {hub_packet['direction']}")
            if hub_protocol:
                print(f"        Protocol: {' '.join(hub_protocol[:20])}{'...' if len(hub_protocol) > 20 else ''}")
            else:
                print(f"        Raw hex:  {' '.join(hub_packet['hex_data'][:20])}{'...' if len(hub_packet['hex_data']) > 20 else ''}")
        else:
            print("HUB     [MISSING]")
            hub_protocol = []
        
        # Proxy packet
        if i < len(proxy_packets):
            proxy_packet = proxy_packets[i]
            proxy_protocol = find_redrat_protocol_data(proxy_packet['hex_data'])
            print(f"PROXY   [{proxy_packet['timestamp']}] {proxy_packet['direction']}")
            if proxy_protocol:
                print(f"        Protocol: {' '.join(proxy_protocol[:20])}{'...' if len(proxy_protocol) > 20 else ''}")
            else:
                print(f"        Raw hex:  {' '.join(proxy_packet['hex_data'][:20])}{'...' if len(proxy_packet['hex_data']) > 20 else ''}")
        else:
            print("PROXY   [MISSING]")
            proxy_protocol = []
        
        # Compare protocol data
        if hub_protocol and proxy_protocol:
            min_len = min(len(hub_protocol), len(proxy_protocol))
            differences = []
            
            for j in range(min_len):
                if hub_protocol[j] != proxy_protocol[j]:
                    differences.append(f"Byte {j}: hub={hub_protocol[j]} vs proxy={proxy_protocol[j]}")
            
            if len(hub_protocol) != len(proxy_protocol):
                differences.append(f"Length: hub={len(hub_protocol)} vs proxy={len(proxy_protocol)}")
            
            if differences:
                print(f"        DIFF:     {', '.join(differences[:3])}{'...' if len(differences) > 3 else ''}")
            else:
                print(f"        MATCH:    ✓ Identical protocol data")
        
        print()

def main():
    """Main comparison function."""
    # Extract packets from both captures
    print("Starting packet-by-packet comparison...")
    
    hub_packets = extract_redrat_packets("redrat_proxy_working.pcap", "HUB TRAFFIC (WORKING)")
    proxy_packets = extract_redrat_packets("hub_vs_proxy_comparison.pcap", "PROXY TRAFFIC (CURRENT)")
    
    if not hub_packets and not proxy_packets:
        print("No RedRat protocol packets found in either capture!")
        return
    
    # Perform detailed comparison
    compare_packets(hub_packets, proxy_packets)
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Hub packets:   {len(hub_packets)}")
    print(f"Proxy packets: {len(proxy_packets)}")
    
    if len(hub_packets) == len(proxy_packets):
        print("✓ Packet count matches")
    else:
        print("✗ Packet count mismatch!")

if __name__ == "__main__":
    main()