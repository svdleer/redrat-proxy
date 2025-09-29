#!/usr/bin/env python3
"""
ERSPAN PCAP Analyzer for RedRat Signal Debugging
Compares ERSPAN captured traffic to identify signal transmission differences
"""

import sys
import os
import argparse
from datetime import datetime
import json

try:
    import scapy.all as scapy
    from scapy.layers.inet import IP, UDP
    from scapy.layers.l2 import Ether
    SCAPY_AVAILABLE = True
except ImportError:
    print("Warning: scapy not available. Install with: pip install scapy")
    SCAPY_AVAILABLE = False

def analyze_erspan_pcap(pcap_file):
    """Analyze ERSPAN pcap file and extract key metrics"""
    if not SCAPY_AVAILABLE:
        print("Error: scapy is required for PCAP analysis")
        return None
    
    if not os.path.exists(pcap_file):
        print(f"Error: PCAP file not found: {pcap_file}")
        return None
    
    print(f"📁 Analyzing ERSPAN PCAP: {pcap_file}")
    
    try:
        packets = scapy.rdpcap(pcap_file)
        
        analysis = {
            'file': pcap_file,
            'total_packets': len(packets),
            'erspan_packets': 0,
            'unique_ips': set(),
            'packet_sizes': [],
            'timestamps': [],
            'protocols': {},
            'erspan_sessions': set(),
            'gre_packets': 0,
            'first_packet_time': None,
            'last_packet_time': None,
            'duration': 0
        }
        
        for i, packet in enumerate(packets):
            # Basic packet info
            analysis['packet_sizes'].append(len(packet))
            
            # Handle packet timestamp conversion safely
            try:
                timestamp = float(packet.time)
                analysis['timestamps'].append(timestamp)
                
                if i == 0:
                    analysis['first_packet_time'] = datetime.fromtimestamp(timestamp)
                if i == len(packets) - 1:
                    analysis['last_packet_time'] = datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError) as e:
                # Handle decimal/timestamp conversion issues
                print(f"Warning: Could not convert timestamp for packet {i}: {e}")
                analysis['timestamps'].append(0.0)
                if i == 0:
                    analysis['first_packet_time'] = datetime.now()
                if i == len(packets) - 1:
                    analysis['last_packet_time'] = datetime.now()
            
            # Check for IP layer
            if packet.haslayer(IP):
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
                analysis['unique_ips'].add(src_ip)
                analysis['unique_ips'].add(dst_ip)
                
                # Protocol analysis
                protocol = packet[IP].proto
                if protocol in analysis['protocols']:
                    analysis['protocols'][protocol] += 1
                else:
                    analysis['protocols'][protocol] = 1
                
                # Check for GRE (protocol 47) - ERSPAN uses GRE
                if protocol == 47:
                    analysis['gre_packets'] += 1
                    analysis['erspan_packets'] += 1
                    
                    # Try to extract ERSPAN session ID if possible
                    if len(packet) > 50:  # Basic length check
                        try:
                            # ERSPAN header analysis (simplified)
                            erspan_data = bytes(packet)[42:46]  # Approximate ERSPAN header location
                            session_id = int.from_bytes(erspan_data[2:4], 'big') & 0x03FF
                            analysis['erspan_sessions'].add(session_id)
                        except:
                            pass
        
        # Calculate duration
        if analysis['timestamps']:
            analysis['duration'] = analysis['timestamps'][-1] - analysis['timestamps'][0]
        
        # Convert sets to lists for JSON serialization
        analysis['unique_ips'] = list(analysis['unique_ips'])
        analysis['erspan_sessions'] = list(analysis['erspan_sessions'])
        
        return analysis
        
    except Exception as e:
        print(f"Error analyzing PCAP: {e}")
        return None

def compare_erspan_captures(baseline_file, new_file):
    """Compare two ERSPAN captures and highlight differences"""
    print(f"🔍 Comparing ERSPAN captures:")
    print(f"  Baseline: {baseline_file}")
    print(f"  New:      {new_file}")
    print("=" * 60)
    
    baseline_analysis = analyze_erspan_pcap(baseline_file)
    new_analysis = analyze_erspan_pcap(new_file)
    
    if not baseline_analysis or not new_analysis:
        print("❌ Failed to analyze one or both PCAP files")
        return
    
    print("\n📊 COMPARISON RESULTS:")
    print("=" * 60)
    
    # Packet count comparison
    baseline_packets = baseline_analysis['total_packets']
    new_packets = new_analysis['total_packets']
    print(f"📦 Total Packets:")
    print(f"  Baseline: {baseline_packets}")
    print(f"  New:      {new_packets}")
    print(f"  Diff:     {new_packets - baseline_packets:+d}")
    
    # ERSPAN packet comparison
    baseline_erspan = baseline_analysis['erspan_packets']
    new_erspan = new_analysis['erspan_packets']
    print(f"\n🌐 ERSPAN Packets (GRE Protocol 47):")
    print(f"  Baseline: {baseline_erspan}")
    print(f"  New:      {new_erspan}")
    print(f"  Diff:     {new_erspan - baseline_erspan:+d}")
    
    # Duration comparison
    print(f"\n⏱️  Capture Duration:")
    print(f"  Baseline: {baseline_analysis['duration']:.2f} seconds")
    print(f"  New:      {new_analysis['duration']:.2f} seconds")
    print(f"  Diff:     {new_analysis['duration'] - baseline_analysis['duration']:+.2f} seconds")
    
    # IP addresses
    baseline_ips = set(baseline_analysis['unique_ips'])
    new_ips = set(new_analysis['unique_ips'])
    print(f"\n🌍 IP Addresses:")
    print(f"  Baseline IPs: {sorted(baseline_ips)}")
    print(f"  New IPs:      {sorted(new_ips)}")
    print(f"  Only in baseline: {sorted(baseline_ips - new_ips)}")
    print(f"  Only in new:      {sorted(new_ips - baseline_ips)}")
    
    # ERSPAN sessions
    baseline_sessions = set(baseline_analysis['erspan_sessions'])
    new_sessions = set(new_analysis['erspan_sessions'])
    print(f"\n🔗 ERSPAN Sessions:")
    print(f"  Baseline: {sorted(baseline_sessions)}")
    print(f"  New:      {sorted(new_sessions)}")
    print(f"  Only in baseline: {sorted(baseline_sessions - new_sessions)}")
    print(f"  Only in new:      {sorted(new_sessions - baseline_sessions)}")
    
    # Packet size analysis
    baseline_avg_size = sum(baseline_analysis['packet_sizes']) / len(baseline_analysis['packet_sizes'])
    new_avg_size = sum(new_analysis['packet_sizes']) / len(new_analysis['packet_sizes'])
    print(f"\n📏 Average Packet Size:")
    print(f"  Baseline: {baseline_avg_size:.1f} bytes")
    print(f"  New:      {new_avg_size:.1f} bytes")
    print(f"  Diff:     {new_avg_size - baseline_avg_size:+.1f} bytes")
    
    # Protocol distribution
    print(f"\n🔬 Protocol Distribution:")
    all_protocols = set(baseline_analysis['protocols'].keys()) | set(new_analysis['protocols'].keys())
    for proto in sorted(all_protocols):
        baseline_count = baseline_analysis['protocols'].get(proto, 0)
        new_count = new_analysis['protocols'].get(proto, 0)
        protocol_name = get_protocol_name(proto)
        print(f"  Protocol {proto} ({protocol_name}):")
        print(f"    Baseline: {baseline_count}")
        print(f"    New:      {new_count}")
        print(f"    Diff:     {new_count - baseline_count:+d}")

def get_protocol_name(proto_num):
    """Get protocol name from number"""
    protocol_map = {
        1: "ICMP",
        6: "TCP", 
        17: "UDP",
        47: "GRE",
        50: "ESP",
        51: "AH"
    }
    return protocol_map.get(proto_num, "Unknown")

def monitor_erspan_live(interface="any", filter_expr="proto 47"):
    """Monitor live ERSPAN traffic (requires root privileges)"""
    if not SCAPY_AVAILABLE:
        print("Error: scapy is required for live monitoring")
        return
    
    print(f"🔴 LIVE MONITORING ERSPAN traffic on {interface}")
    print(f"   Filter: {filter_expr}")
    print("   Press Ctrl+C to stop")
    print("=" * 50)
    
    def packet_handler(packet):
        try:
            timestamp = datetime.fromtimestamp(float(packet.time)).strftime("%H:%M:%S.%f")[:-3]
        except (ValueError, TypeError):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        if packet.haslayer(IP):
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst
            size = len(packet)
            
            print(f"[{timestamp}] {src_ip} → {dst_ip} | Size: {size} bytes")
            
            # Try to decode ERSPAN info
            if packet[IP].proto == 47:  # GRE
                try:
                    gre_data = bytes(packet)[34:]  # Skip IP header
                    if len(gre_data) >= 8:
                        # Basic GRE header analysis
                        gre_flags = int.from_bytes(gre_data[0:2], 'big')
                        gre_proto = int.from_bytes(gre_data[2:4], 'big')
                        print(f"    GRE: flags=0x{gre_flags:04x}, proto=0x{gre_proto:04x}")
                except:
                    pass
    
    try:
        scapy.sniff(iface=interface, filter=filter_expr, prn=packet_handler)
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped")
    except Exception as e:
        print(f"Error during monitoring: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="ERSPAN PCAP Analyzer for RedRat Signal Debugging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single PCAP file
  python erspan_analyzer.py analyze baseline.pcap
  
  # Compare two PCAP files
  python erspan_analyzer.py compare baseline.pcap new_capture.pcap
  
  # Monitor live ERSPAN traffic (requires root)
  sudo python erspan_analyzer.py monitor
  
  # Monitor on specific interface with custom filter
  sudo python erspan_analyzer.py monitor --interface eth0 --filter "host 192.168.1.100"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a single PCAP file')
    analyze_parser.add_argument('pcap_file', help='PCAP file to analyze')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two PCAP files')
    compare_parser.add_argument('baseline_file', help='Baseline PCAP file')
    compare_parser.add_argument('new_file', help='New PCAP file to compare')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor live ERSPAN traffic')
    monitor_parser.add_argument('--interface', default='any', help='Network interface to monitor')
    monitor_parser.add_argument('--filter', default='proto 47', help='BPF filter expression')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print(f"🚀 ERSPAN Analyzer - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if args.command == 'analyze':
        result = analyze_erspan_pcap(args.pcap_file)
        if result:
            print(f"\n📋 ANALYSIS SUMMARY:")
            print(f"  File: {result['file']}")
            print(f"  Total packets: {result['total_packets']}")
            print(f"  ERSPAN packets: {result['erspan_packets']}")
            print(f"  Duration: {result['duration']:.2f} seconds")
            print(f"  Unique IPs: {len(result['unique_ips'])}")
            print(f"  ERSPAN sessions: {result['erspan_sessions']}")
    
    elif args.command == 'compare':
        compare_erspan_captures(args.baseline_file, args.new_file)
    
    elif args.command == 'monitor':
        monitor_erspan_live(args.interface, args.filter)

if __name__ == "__main__":
    main()