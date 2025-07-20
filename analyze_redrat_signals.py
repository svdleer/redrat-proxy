#!/usr/bin/env python3
"""
RedRat Signal Analysis Tool
Analyzes captured RedRat IR signals from PCAP files
"""

import argparse
import json
import struct
import sys
from datetime import datetime
from pathlib import Path

try:
    import scapy.all as scapy
except ImportError:
    print("❌ Scapy not installed. Run: pip install scapy")
    sys.exit(1)

def parse_redrat_packet(packet):
    """Parse RedRat protocol packet and extract IR data"""
    if not packet.haslayer(scapy.TCP):
        return None
    
    tcp_payload = bytes(packet[scapy.TCP].payload)
    if len(tcp_payload) < 4:
        return None
    
    try:
        # RedRat protocol header (simplified)
        message_type = tcp_payload[0] if len(tcp_payload) > 0 else 0
        data_length = len(tcp_payload)
        
        return {
            'timestamp': float(packet.time),
            'src_port': packet[scapy.TCP].sport,
            'dst_port': packet[scapy.TCP].dport,
            'message_type': message_type,
            'data_length': data_length,
            'payload_hex': tcp_payload.hex(),
            'direction': 'to_device' if packet[scapy.TCP].dport == 10001 else 'from_device'
        }
    except Exception as e:
        print(f"⚠️  Error parsing packet: {e}")
        return None

def analyze_pcap(pcap_file):
    """Analyze RedRat traffic in a PCAP file"""
    print(f"🔍 Analyzing {pcap_file}")
    
    try:
        packets = scapy.rdpcap(str(pcap_file))
    except Exception as e:
        print(f"❌ Error reading PCAP file: {e}")
        return None
    
    redrat_packets = []
    
    # Filter RedRat packets (port 10001)
    for packet in packets:
        if packet.haslayer(scapy.TCP) and (
            packet[scapy.TCP].sport == 10001 or 
            packet[scapy.TCP].dport == 10001
        ):
            parsed = parse_redrat_packet(packet)
            if parsed:
                redrat_packets.append(parsed)
    
    if not redrat_packets:
        print(f"⚠️  No RedRat packets found in {pcap_file}")
        return None
    
    # Calculate timing statistics
    timestamps = [p['timestamp'] for p in redrat_packets]
    duration = max(timestamps) - min(timestamps)
    packet_intervals = []
    
    for i in range(1, len(timestamps)):
        interval = timestamps[i] - timestamps[i-1]
        packet_intervals.append(interval * 1000)  # Convert to ms
    
    analysis = {
        'file': str(pcap_file),
        'total_packets': len(redrat_packets),
        'duration_ms': duration * 1000,
        'packet_intervals_ms': packet_intervals,
        'avg_interval_ms': sum(packet_intervals) / len(packet_intervals) if packet_intervals else 0,
        'to_device_packets': len([p for p in redrat_packets if p['direction'] == 'to_device']),
        'from_device_packets': len([p for p in redrat_packets if p['direction'] == 'from_device']),
        'message_types': list(set(p['message_type'] for p in redrat_packets)),
        'packets': redrat_packets
    }
    
    return analysis

def compare_analyses(analysis1, analysis2):
    """Compare two signal analyses"""
    print("\n📊 SIGNAL COMPARISON")
    print("=" * 50)
    
    file1 = Path(analysis1['file']).name
    file2 = Path(analysis2['file']).name
    
    print(f"File 1: {file1}")
    print(f"File 2: {file2}")
    print()
    
    # Basic statistics comparison
    print("📈 Basic Statistics:")
    print(f"  Packets:      {analysis1['total_packets']:>3} vs {analysis2['total_packets']:>3}")
    print(f"  Duration:     {analysis1['duration_ms']:>6.2f}ms vs {analysis2['duration_ms']:>6.2f}ms")
    print(f"  Avg Interval: {analysis1['avg_interval_ms']:>6.2f}ms vs {analysis2['avg_interval_ms']:>6.2f}ms")
    
    # Direction comparison
    print(f"  To Device:    {analysis1['to_device_packets']:>3} vs {analysis2['to_device_packets']:>3}")
    print(f"  From Device:  {analysis1['from_device_packets']:>3} vs {analysis2['from_device_packets']:>3}")
    print()
    
    # Message types comparison
    print("📋 Message Types:")
    all_types = set(analysis1['message_types'] + analysis2['message_types'])
    for msg_type in sorted(all_types):
        in_1 = msg_type in analysis1['message_types']
        in_2 = msg_type in analysis2['message_types']
        status = "✅" if in_1 and in_2 else "⚠️" if in_1 or in_2 else "❌"
        print(f"  Type 0x{msg_type:02x}: {status} {'Both' if in_1 and in_2 else 'Only in ' + (file1 if in_1 else file2)}")
    print()
    
    # Timing analysis
    print("⏱️  Timing Differences:")
    duration_diff = analysis1['duration_ms'] - analysis2['duration_ms']
    interval_diff = analysis1['avg_interval_ms'] - analysis2['avg_interval_ms']
    
    print(f"  Duration difference: {duration_diff:+.2f}ms")
    print(f"  Interval difference: {interval_diff:+.2f}ms")
    
    if abs(duration_diff) > 100:  # More than 100ms difference
        print("  ⚠️  Significant timing difference detected!")
    
    print()
    
    # Detailed packet comparison (first 5 packets)
    print("🔍 Packet-by-Packet Comparison (first 5):")
    max_packets = min(5, len(analysis1['packets']), len(analysis2['packets']))
    
    for i in range(max_packets):
        p1 = analysis1['packets'][i]
        p2 = analysis2['packets'][i]
        
        print(f"  Packet {i+1}:")
        print(f"    Type:   0x{p1['message_type']:02x} vs 0x{p2['message_type']:02x}")
        print(f"    Length: {p1['data_length']:>3} vs {p2['data_length']:>3}")
        
        # Compare payload (first 20 bytes)
        payload1 = p1['payload_hex'][:40]  # 20 bytes in hex
        payload2 = p2['payload_hex'][:40]
        
        if payload1 == payload2:
            print(f"    Payload: ✅ Identical")
        else:
            print(f"    Payload: ⚠️  Different")
            print(f"      File1: {payload1}")
            print(f"      File2: {payload2}")

def main():
    parser = argparse.ArgumentParser(description='Analyze RedRat IR signals from PCAP captures')
    parser.add_argument('pcap_files', nargs='+', help='PCAP files to analyze')
    parser.add_argument('--output', '-o', help='Output JSON file for detailed results')
    parser.add_argument('--compare', action='store_true', help='Compare first two PCAP files')
    
    args = parser.parse_args()
    
    if len(args.pcap_files) < 1:
        print("❌ At least one PCAP file required")
        sys.exit(1)
    
    print("🚀 RedRat Signal Analysis Tool")
    print("=" * 40)
    
    analyses = []
    
    # Analyze each PCAP file
    for pcap_file in args.pcap_files:
        pcap_path = Path(pcap_file)
        if not pcap_path.exists():
            print(f"❌ File not found: {pcap_file}")
            continue
        
        analysis = analyze_pcap(pcap_path)
        if analysis:
            analyses.append(analysis)
            
            print(f"\n📋 Results for {pcap_path.name}:")
            print(f"  Total packets: {analysis['total_packets']}")
            print(f"  Duration: {analysis['duration_ms']:.2f}ms")
            print(f"  Average interval: {analysis['avg_interval_ms']:.2f}ms")
            print(f"  To device: {analysis['to_device_packets']}")
            print(f"  From device: {analysis['from_device_packets']}")
            print(f"  Message types: {[hex(t) for t in analysis['message_types']]}")
    
    # Compare analyses if requested
    if args.compare and len(analyses) >= 2:
        compare_analyses(analyses[0], analyses[1])
    elif args.compare:
        print("\n⚠️  Need at least 2 PCAP files for comparison")
    
    # Save detailed results
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(analyses, f, indent=2)
        print(f"\n💾 Detailed results saved to: {output_path}")
    
    print(f"\n✅ Analysis complete!")

if __name__ == '__main__':
    main()
