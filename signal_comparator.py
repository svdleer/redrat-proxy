#!/usr/bin/env python3
"""
RedRat Signal Data Comparator
Captures and compares the actual signal data sent to RedRat device
"""

import sys
import os
import socket
import struct  
import time
import binascii
from datetime import datetime
from collections import defaultdict

# Add app to path
sys.path.insert(0, '/home/svdleer/redrat-proxy')

try:
    import scapy.all as scapy
    from scapy.layers.inet import IP, TCP
    from scapy.layers.l2 import Ether
    SCAPY_AVAILABLE = True
except ImportError:
    print("Warning: scapy not available for live capture")
    SCAPY_AVAILABLE = False

def extract_redrat_signals_from_pcap(pcap_file, name):
    """Extract RedRat signal data from PCAP (handles both ERSPAN and direct traffic)"""
    print(f"🔍 Extracting RedRat signals from: {name}")
    
    if not SCAPY_AVAILABLE:
        print("❌ scapy not available")
        return []
    
    try:
        packets = scapy.rdpcap(pcap_file)
        redrat_signals = []
        erspan_count = 0
        direct_count = 0
        
        for i, packet in enumerate(packets):
            # Try ERSPAN format first (GRE encapsulated)
            if packet.haslayer(IP) and packet[IP].proto == 47:  # GRE/ERSPAN
                try:
                    gre = packet[scapy.GRE]
                    if gre.proto == 0x88be:  # ERSPAN Type II
                        erspan_count += 1
                        # Skip ERSPAN header and parse inner frame
                        erspan_payload = bytes(gre.payload)[8:]
                        inner_frame = scapy.Ether(erspan_payload)
                        
                        if inner_frame.haslayer(IP) and inner_frame.haslayer(TCP):
                            inner_ip = inner_frame[IP]
                            tcp = inner_frame[TCP]
                            
                            # Check for RedRat traffic (port 10001)
                            if tcp.dport == 10001 or tcp.sport == 10001:
                                payload = bytes(tcp.payload) if tcp.payload else b''
                                signal = parse_redrat_message(payload, i+1, packet, inner_ip, tcp)
                                if signal:
                                    redrat_signals.append(signal)
                except Exception:
                    continue
            
            # Try direct RedRat traffic (no ERSPAN)
            elif packet.haslayer(IP) and packet.haslayer(TCP):
                ip = packet[IP]
                tcp = packet[TCP]
                
                # Check for RedRat traffic (port 10001)
                if tcp.dport == 10001 or tcp.sport == 10001:
                    direct_count += 1
                    payload = bytes(tcp.payload) if tcp.payload else b''
                    signal = parse_redrat_message(payload, i+1, packet, ip, tcp)
                    if signal:
                        redrat_signals.append(signal)
        
        print(f"📊 Found {len(redrat_signals)} RedRat protocol messages")
        print(f"   ERSPAN packets: {erspan_count}, Direct packets: {direct_count}")
        return redrat_signals
        
    except Exception as e:
        print(f"❌ Error extracting signals: {e}")
        return []

def parse_redrat_message(payload, packet_num, packet, ip, tcp):
    """Parse a RedRat protocol message from TCP payload"""
    if len(payload) > 4 and payload[0:1] == b'#':
        try:
            msg_len = struct.unpack('>H', payload[1:3])[0]
            msg_type = payload[3]
            msg_data = payload[4:4+msg_len] if msg_len > 0 else b''
            
            signal_info = {
                'packet_num': packet_num,
                'timestamp': float(packet.time) if hasattr(packet, 'time') else 0,
                'src_ip': ip.src,
                'dst_ip': ip.dst,
                'tcp_flags': tcp.flags,
                'msg_type': msg_type,
                'msg_len': msg_len,
                'msg_data': msg_data,
                'full_payload': payload,
                'direction': 'to_redrat' if tcp.dport == 10001 else 'from_redrat'
            }
            
            return signal_info
            
        except (struct.error, IndexError):
            # Not a valid RedRat message
            pass
    
    return None

def analyze_redrat_signals(signals, name):
    """Analyze RedRat signal patterns"""
    print(f"\n🔬 ANALYZING {name} SIGNALS")
    print("="*50)
    
    if not signals:
        print("❌ No signals to analyze")
        return {}
    
    # Categorize by message type
    by_type = defaultdict(list)
    ir_signals = []
    
    for sig in signals:
        by_type[sig['msg_type']].append(sig)
        
        # Look for IR transmission messages (type 0x12 or 0x30)
        if (sig['msg_type'] == 0x12 or sig['msg_type'] == 0x30) and sig['direction'] == 'to_redrat':
            ir_signals.append(sig)
    
    print(f"📡 Message types found:")
    for msg_type, msgs in by_type.items():
        type_name = get_redrat_message_type_name(msg_type)
        print(f"  0x{msg_type:02x} ({type_name}): {len(msgs)} messages")
    
    print(f"\n🎯 IR TRANSMISSION SIGNALS: {len(ir_signals)}")
    
    for i, sig in enumerate(ir_signals):
        print(f"\nIR Signal #{i+1}:")
        print(f"  Packet: #{sig['packet_num']}")
        print(f"  Time: {datetime.fromtimestamp(sig['timestamp']).strftime('%H:%M:%S.%f')[:-3]}")
        print(f"  Direction: {sig['src_ip']} -> {sig['dst_ip']}")
        print(f"  Data length: {len(sig['msg_data'])} bytes")
        
        if sig['msg_type'] == 0x12:  # Standard RedRat IR Send
            if len(sig['msg_data']) >= 2:
                ir_port = sig['msg_data'][0] if len(sig['msg_data']) > 0 else 0
                ir_power = sig['msg_data'][1] if len(sig['msg_data']) > 1 else 0
                ir_data = sig['msg_data'][2:] if len(sig['msg_data']) > 2 else b''
                
                print(f"  IR Port: {ir_port}")
                print(f"  IR Power: {ir_power}")
                print(f"  IR Data: {len(ir_data)} bytes")
                print(f"  First 32 bytes: {ir_data[:32].hex()}")
                print(f"  Last 32 bytes: {ir_data[-32:].hex()}")
                
                # Check for pattern signatures
                if len(ir_data) >= 4:
                    header = ir_data[:4].hex()
                    print(f"  Header signature: {header}")
        
        elif sig['msg_type'] == 0x30:  # IrNetbox MK3/4 ASYNC format
            ir_data = sig['msg_data']
            print(f"  MK3/4 ASYNC Format")
            print(f"  IR Data: {len(ir_data)} bytes")
            print(f"  First 32 bytes: {ir_data[:32].hex()}")
            print(f"  Last 32 bytes: {ir_data[-32:].hex()}")
            
            # Check for MK3/4 pattern signatures
            if len(ir_data) >= 4:
                header = ir_data[:4].hex()
                print(f"  Header signature: {header}")
        
        else:
            print(f"  Unknown IR format: 0x{sig['msg_type']:02x}")
        
        print(f"  Full message: {sig['full_payload'][:64].hex()}...")
    
    return {
        'total_signals': len(signals),
        'ir_signals': ir_signals,
        'by_type': dict(by_type)
    }

def compare_signal_data(original_signals, proxy_signals):
    """Compare signal data between original and proxy"""
    print(f"\n📊 SIGNAL DATA COMPARISON")
    print("="*60)
    
    orig_ir = original_signals.get('ir_signals', [])
    proxy_ir = proxy_signals.get('ir_signals', [])
    
    print(f"IR Signals:")
    print(f"  Original: {len(orig_ir)}")
    print(f"  Proxy: {len(proxy_ir)}")
    
    if not orig_ir and not proxy_ir:
        print("❌ No IR signals found in either capture")
        return
    
    if not orig_ir:
        print("❌ No original IR signals to compare")
        return
    
    if not proxy_ir:
        print("❌ No proxy IR signals to compare")
        return
    
    # Compare first IR signal from each
    print(f"\n🔍 DETAILED COMPARISON (First IR signal from each):")
    print("="*60)
    
    orig_first = orig_ir[0]
    proxy_first = proxy_ir[0]
    
    # Extract IR data based on format
    if orig_first['msg_type'] == 0x12:  # Standard RedRat format
        orig_ir_data = orig_first['msg_data'][2:] if len(orig_first['msg_data']) > 2 else b''
        orig_port = orig_first['msg_data'][0] if len(orig_first['msg_data']) > 0 else 0
        orig_power = orig_first['msg_data'][1] if len(orig_first['msg_data']) > 1 else 0
    elif orig_first['msg_type'] == 0x30:  # MK3/4 ASYNC format
        orig_ir_data = orig_first['msg_data']
        orig_port = "MK3/4"
        orig_power = "N/A"
    else:
        orig_ir_data = orig_first['msg_data']
        orig_port = "Unknown"
        orig_power = "Unknown"
    
    if proxy_first['msg_type'] == 0x12:  # Standard RedRat format
        proxy_ir_data = proxy_first['msg_data'][2:] if len(proxy_first['msg_data']) > 2 else b''
        proxy_port = proxy_first['msg_data'][0] if len(proxy_first['msg_data']) > 0 else 0
        proxy_power = proxy_first['msg_data'][1] if len(proxy_first['msg_data']) > 1 else 0
    elif proxy_first['msg_type'] == 0x30:  # MK3/4 ASYNC format
        proxy_ir_data = proxy_first['msg_data']
        proxy_port = "MK3/4"
        proxy_power = "N/A"
    else:
        proxy_ir_data = proxy_first['msg_data']
        proxy_port = "Unknown"
        proxy_power = "Unknown"
    
    print(f"📏 Data lengths:")
    print(f"  Original: {len(orig_ir_data)} bytes")
    print(f"  Proxy: {len(proxy_ir_data)} bytes")
    print(f"  Difference: {len(proxy_ir_data) - len(orig_ir_data):+d} bytes")
    
    print(f"\n🎛️  IR Parameters:")
    print(f"  Original Format: 0x{orig_first['msg_type']:02x} ({get_redrat_message_type_name(orig_first['msg_type'])})")
    print(f"  Proxy Format:    0x{proxy_first['msg_type']:02x} ({get_redrat_message_type_name(proxy_first['msg_type'])})")
    print(f"  Port:  Original={orig_port}, Proxy={proxy_port}")
    print(f"  Power: Original={orig_power}, Proxy={proxy_power}")
    
    if orig_first['msg_type'] != proxy_first['msg_type']:
        print(f"  ⚠️  FORMAT MISMATCH! Different IR protocols used!")
    
    print(f"\n🔍 Signal Data Headers (first 32 bytes):")
    print(f"  Original: {orig_ir_data[:32].hex()}")
    print(f"  Proxy:    {proxy_ir_data[:32].hex()}")
    
    if orig_ir_data[:32] == proxy_ir_data[:32]:
        print("  ✅ Headers match!")
    else:
        print("  ❌ Headers differ!")
        
        # Show byte-by-byte differences
        print(f"\n📋 Byte-by-byte comparison (first 32 bytes):")
        min_len = min(len(orig_ir_data), len(proxy_ir_data), 32)
        for i in range(min_len):
            orig_byte = orig_ir_data[i]
            proxy_byte = proxy_ir_data[i]
            if orig_byte != proxy_byte:
                print(f"    Byte {i:2d}: Original=0x{orig_byte:02x}, Proxy=0x{proxy_byte:02x} ❌")
            else:
                print(f"    Byte {i:2d}: 0x{orig_byte:02x} ✅")
    
    print(f"\n🔍 Signal Data Tails (last 32 bytes):")
    print(f"  Original: {orig_ir_data[-32:].hex()}")
    print(f"  Proxy:    {proxy_ir_data[-32:].hex()}")
    
    if orig_ir_data[-32:] == proxy_ir_data[-32:]:
        print("  ✅ Tails match!")
    else:
        print("  ❌ Tails differ!")
    
    # Overall comparison
    if orig_first['msg_type'] != proxy_first['msg_type']:
        print(f"\n🚨 PROTOCOL MISMATCH!")
        print(f"   Original uses: 0x{orig_first['msg_type']:02x} ({get_redrat_message_type_name(orig_first['msg_type'])})")
        print(f"   Proxy uses:    0x{proxy_first['msg_type']:02x} ({get_redrat_message_type_name(proxy_first['msg_type'])})")
        print("   This is the ROOT CAUSE of the IR signal failure!")
        print("   The proxy needs to send MK3/4 ASYNC format (0x30) instead of standard IR Send (0x12)")
    elif orig_ir_data == proxy_ir_data:
        print(f"\n🎉 PERFECT MATCH! Signal data is identical!")
        print("   The issue might be:")
        print("   - IR port configuration")
        print("   - IR power levels") 
        print("   - Physical IR connections")
        print("   - Target device not responding")
    else:
        print(f"\n❌ SIGNAL DATA MISMATCH!")
        print("   This explains why the IR signals don't work.")
        print("   The proxy is sending different data to the RedRat device.")
        
        # Calculate similarity
        if len(orig_ir_data) > 0 and len(proxy_ir_data) > 0:
            min_len = min(len(orig_ir_data), len(proxy_ir_data))
            matching_bytes = sum(1 for i in range(min_len) if orig_ir_data[i] == proxy_ir_data[i])
            similarity = (matching_bytes / min_len) * 100
            print(f"   Similarity: {similarity:.1f}% ({matching_bytes}/{min_len} bytes match)")

def get_redrat_message_type_name(msg_type):
    """Get human-readable name for RedRat message type"""
    types = {
        0x05: "Power On",
        0x06: "Power Off", 
        0x07: "Reset/Control",
        0x09: "Get Version",
        0x10: "Set Memory",
        0x12: "IR Send (Standard)",
        0x13: "IR Receive",
        0x17: "Indicators",
        0x30: "IR Send (IrNetbox MK3/4 ASYNC)"
    }
    return types.get(msg_type, f"Unknown-{msg_type}")

def save_signal_data(signals, filename):
    """Save extracted signal data for further analysis"""
    ir_signals = signals.get('ir_signals', [])
    
    if not ir_signals:
        print(f"❌ No IR signals to save")
        return
    
    try:
        with open(filename, 'wb') as f:
            for i, sig in enumerate(ir_signals):
                ir_data = sig['msg_data'][2:] if len(sig['msg_data']) > 2 else b''
                f.write(f"# IR Signal {i+1} ({len(ir_data)} bytes)\n".encode())
                f.write(ir_data)
                f.write(b'\n\n')
        
        print(f"💾 Saved {len(ir_signals)} IR signals to {filename}")
    except Exception as e:
        print(f"❌ Error saving signals: {e}")

def main():
    print("🔍 RedRat Signal Data Comparator")
    print("="*50)
    print("Extracts and compares actual IR signal data sent to RedRat device")
    print("")
    
    # File paths
    original_pcap = "./captures/hub_baseline_20250927_110524.pcap"
    proxy_pcap = "./captures/redrat_proxy_final_20250928_191758.pcap"
    
    print(f"📁 Analyzing PCAP files:")
    print(f"  Original: {original_pcap}")
    print(f"  Proxy:    {proxy_pcap}")
    
    # Check files exist
    if not os.path.exists(original_pcap):
        print(f"❌ Original PCAP not found: {original_pcap}")
        return
    
    if not os.path.exists(proxy_pcap):
        print(f"❌ Proxy PCAP not found: {proxy_pcap}")
        return
    
    # Extract signals
    print(f"\n🔍 EXTRACTING SIGNALS...")
    original_signals_raw = extract_redrat_signals_from_pcap(original_pcap, "ORIGINAL")
    proxy_signals_raw = extract_redrat_signals_from_pcap(proxy_pcap, "PROXY")
    
    # Analyze signals
    original_analysis = analyze_redrat_signals(original_signals_raw, "ORIGINAL")
    proxy_analysis = analyze_redrat_signals(proxy_signals_raw, "PROXY")
    
    # Compare signals
    compare_signal_data(original_analysis, proxy_analysis)
    
    # Save signal data for manual inspection
    print(f"\n💾 SAVING SIGNAL DATA...")
    save_signal_data(original_analysis, "original_ir_signals.bin") 
    save_signal_data(proxy_analysis, "proxy_ir_signals.bin")
    
    print(f"\n💡 NEXT STEPS:")
    print("="*50)
    print("1. Check the comparison results above")
    print("2. If signals differ, investigate signal conversion in RedRat proxy")
    print("3. Look at saved .bin files for manual hex comparison")
    print("4. Check database signal templates vs actual transmitted data")
    print("5. Verify signal format conversion in redrat_service.py")

if __name__ == "__main__":
    main()