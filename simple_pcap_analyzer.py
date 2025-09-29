#!/usr/bin/env python3
"""
Simple PCAP Analyzer for RedRat Traffic Debugging
Focuses on basic traffic analysis without complex timestamp handling
"""

import sys
import os
import argparse
from collections import defaultdict

try:
    import scapy.all as scapy
    from scapy.layers.inet import IP, TCP, UDP
    from scapy.layers.l2 import Ether
    SCAPY_AVAILABLE = True
except ImportError:
    print("Error: scapy not available. Install with: pip install scapy")
    sys.exit(1)

def simple_pcap_analysis(pcap_file):
    """Simple PCAP analysis focusing on key metrics"""
    print(f"📁 Analyzing: {pcap_file}")
    
    if not os.path.exists(pcap_file):
        print(f"❌ File not found: {pcap_file}")
        return None
    
    try:
        packets = scapy.rdpcap(pcap_file)
        total_packets = len(packets)
        
        if total_packets == 0:
            print("❌ No packets in file")
            return None
        
        print(f"📦 Total packets: {total_packets}")
        
        # Analyze packets
        ip_stats = defaultdict(int)
        protocol_stats = defaultdict(int)
        port_stats = defaultdict(int)
        packet_sizes = []
        gre_count = 0
        
        for packet in packets:
            packet_sizes.append(len(packet))
            
            if packet.haslayer(IP):
                ip_layer = packet[IP]
                src_ip = ip_layer.src
                dst_ip = ip_layer.dst
                protocol = ip_layer.proto
                
                # Count IPs
                ip_stats[f"{src_ip} -> {dst_ip}"] += 1
                
                # Count protocols
                protocol_name = get_protocol_name(protocol)
                protocol_stats[protocol_name] += 1
                
                # Check for GRE (ERSPAN)
                if protocol == 47:
                    gre_count += 1
                
                # Check for TCP/UDP ports
                if packet.haslayer(TCP):
                    tcp_layer = packet[TCP]
                    port_stats[f"TCP/{tcp_layer.dport}"] += 1
                elif packet.haslayer(UDP):
                    udp_layer = packet[UDP]
                    port_stats[f"UDP/{udp_layer.dport}"] += 1
        
        # Calculate statistics
        avg_size = sum(packet_sizes) / len(packet_sizes)
        min_size = min(packet_sizes)
        max_size = max(packet_sizes)
        
        # Display results
        print(f"📊 Packet sizes: avg={avg_size:.1f}, min={min_size}, max={max_size}")
        print(f"🌐 GRE packets (ERSPAN): {gre_count}")
        
        print("\n📍 Top IP Flows:")
        for flow, count in sorted(ip_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {flow}: {count} packets")
        
        print("\n🔬 Protocol Distribution:")
        for proto, count in sorted(protocol_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {proto}: {count} packets")
        
        if port_stats:
            print("\n🔌 Top Ports:")
            for port, count in sorted(port_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {port}: {count} packets")
        
        return {
            'total_packets': total_packets,
            'gre_packets': gre_count,
            'avg_size': avg_size,
            'ip_stats': dict(ip_stats),
            'protocol_stats': dict(protocol_stats),
            'port_stats': dict(port_stats)
        }
        
    except Exception as e:
        print(f"❌ Error analyzing {pcap_file}: {e}")
        return None

def compare_simple(file1, file2):
    """Simple comparison of two PCAP files"""
    print(f"🔍 COMPARING PCAP FILES")
    print(f"File 1: {os.path.basename(file1)}")
    print(f"File 2: {os.path.basename(file2)}")
    print("=" * 50)
    
    result1 = simple_pcap_analysis(file1)
    print("\n" + "=" * 50)
    result2 = simple_pcap_analysis(file2)
    
    if not result1 or not result2:
        print("❌ Could not analyze one or both files")
        return
    
    print("\n" + "=" * 50)
    print("📊 COMPARISON SUMMARY")
    print("=" * 50)
    
    # Packet count comparison
    print(f"📦 Total Packets:")
    print(f"  File 1: {result1['total_packets']}")
    print(f"  File 2: {result2['total_packets']}")
    print(f"  Difference: {result2['total_packets'] - result1['total_packets']:+d}")
    
    # GRE comparison
    print(f"\n🌐 GRE/ERSPAN Packets:")
    print(f"  File 1: {result1['gre_packets']}")
    print(f"  File 2: {result2['gre_packets']}")
    print(f"  Difference: {result2['gre_packets'] - result1['gre_packets']:+d}")
    
    # Size comparison
    print(f"\n📏 Average Packet Size:")
    print(f"  File 1: {result1['avg_size']:.1f} bytes")
    print(f"  File 2: {result2['avg_size']:.1f} bytes")
    print(f"  Difference: {result2['avg_size'] - result1['avg_size']:+.1f} bytes")
    
    # IP flows comparison
    print(f"\n📍 Unique IP Flows:")
    all_flows1 = set(result1['ip_stats'].keys())
    all_flows2 = set(result2['ip_stats'].keys())
    
    print(f"  File 1: {len(all_flows1)} unique flows")
    print(f"  File 2: {len(all_flows2)} unique flows")
    
    only_in_1 = all_flows1 - all_flows2
    only_in_2 = all_flows2 - all_flows1
    
    if only_in_1:
        print(f"  Only in File 1:")
        for flow in sorted(only_in_1)[:5]:  # Show top 5
            print(f"    {flow} ({result1['ip_stats'][flow]} packets)")
    
    if only_in_2:
        print(f"  Only in File 2:")
        for flow in sorted(only_in_2)[:5]:  # Show top 5
            print(f"    {flow} ({result2['ip_stats'][flow]} packets)")
    
    # Protocol comparison
    print(f"\n🔬 Protocol Differences:")
    all_protocols = set(result1['protocol_stats'].keys()) | set(result2['protocol_stats'].keys())
    
    for proto in sorted(all_protocols):
        count1 = result1['protocol_stats'].get(proto, 0)
        count2 = result2['protocol_stats'].get(proto, 0)
        diff = count2 - count1
        if diff != 0:
            print(f"  {proto}: {count1} -> {count2} ({diff:+d})")

def get_protocol_name(proto_num):
    """Get protocol name from number"""
    protocol_map = {
        1: "ICMP",
        6: "TCP",
        17: "UDP", 
        47: "GRE",
        50: "ESP",
        51: "AH",
        89: "OSPF"
    }
    return protocol_map.get(proto_num, f"Proto-{proto_num}")

def find_redrat_traffic(pcap_file, redrat_ips=None):
    """Find traffic related to RedRat IPs"""
    if redrat_ips is None:
        redrat_ips = ["172.16.6.62", "172.16.6.101", "172.16.6.5"]
    
    print(f"🔍 Looking for RedRat traffic in: {pcap_file}")
    print(f"RedRat IPs: {redrat_ips}")
    
    try:
        packets = scapy.rdpcap(pcap_file)
        redrat_packets = []
        
        for packet in packets:
            if packet.haslayer(IP):
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
                
                if any(ip in [src_ip, dst_ip] for ip in redrat_ips):
                    redrat_packets.append(packet)
        
        print(f"📊 Found {len(redrat_packets)} RedRat-related packets out of {len(packets)} total")
        
        if redrat_packets:
            print("\n📍 RedRat Traffic Summary:")
            redrat_flows = defaultdict(int)
            for packet in redrat_packets:
                if packet.haslayer(IP):
                    src_ip = packet[IP].src
                    dst_ip = packet[IP].dst
                    proto = get_protocol_name(packet[IP].proto)
                    redrat_flows[f"{src_ip} -> {dst_ip} ({proto})"] += 1
            
            for flow, count in sorted(redrat_flows.items(), key=lambda x: x[1], reverse=True):
                print(f"  {flow}: {count} packets")
        else:
            print("❌ No RedRat traffic found!")
            print("   This might indicate:")
            print("   - RedRat proxy not sending commands")
            print("   - ERSPAN not capturing the right traffic")
            print("   - Wrong IP addresses in filter")
        
        return len(redrat_packets)
        
    except Exception as e:
        print(f"❌ Error analyzing RedRat traffic: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description="Simple PCAP Analyzer for RedRat Traffic")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze single PCAP')
    analyze_parser.add_argument('pcap_file', help='PCAP file to analyze')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two PCAPs')
    compare_parser.add_argument('file1', help='First PCAP file')
    compare_parser.add_argument('file2', help='Second PCAP file')
    
    # RedRat command
    redrat_parser = subparsers.add_parser('redrat', help='Find RedRat traffic')
    redrat_parser.add_argument('pcap_file', help='PCAP file to analyze')
    redrat_parser.add_argument('--ips', nargs='+', 
                              default=["172.16.6.62", "172.16.6.101", "172.16.6.5"],
                              help='RedRat IP addresses to look for')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'analyze':
        simple_pcap_analysis(args.pcap_file)
    elif args.command == 'compare':
        compare_simple(args.file1, args.file2)
    elif args.command == 'redrat':
        find_redrat_traffic(args.pcap_file, args.ips)

if __name__ == "__main__":
    main()