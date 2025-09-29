#!/usr/bin/env python3
"""
Byte-by-Byte RedRat Protocol Comparison
Extract and compare exact message bytes between hub and proxy
"""
import subprocess
import re

def extract_hex_bytes_from_pcap(pcap_file, description):
    """Extract hex bytes from PCAP file"""
    print(f"\n🔍 Extracting bytes from {description}")
    print("="*60)
    
    try:
        # Get detailed hex dump
        result = subprocess.run([
            'tcpdump', '-r', pcap_file, '-nn', '-X', '-s', '0'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Error reading {pcap_file}: {result.stderr}")
            return []
        
        # Parse hex data from tcpdump output
        hex_messages = []
        lines = result.stdout.split('\n')
        current_packet = []
        
        for line in lines:
            # Look for hex data lines (format: 0x0000: xxxx xxxx ...)
            if re.match(r'\s*0x[0-9a-f]+:', line):
                # Extract hex bytes from line
                hex_part = line.split(':', 1)[1] if ':' in line else ""
                # Extract just the hex bytes (ignore ASCII part)
                hex_bytes = re.findall(r'[0-9a-f]{4}', hex_part.split()[0:8])  # First 8 groups
                current_packet.extend(hex_bytes)
            elif line.strip() == "" and current_packet:
                # End of packet
                if current_packet:
                    hex_messages.append(''.join(current_packet))
                    current_packet = []
        
        # Don't forget the last packet
        if current_packet:
            hex_messages.append(''.join(current_packet))
        
        return hex_messages
        
    except Exception as e:
        print(f"❌ Error extracting from {pcap_file}: {e}")
        return []

def find_redrat_messages(hex_data_list):
    """Find RedRat protocol messages (starting with '23' = '#')"""
    redrat_messages = []
    
    for hex_data in hex_data_list:
        # Look for RedRat message start pattern '23' (ASCII '#')
        # Search through the hex data for '23' followed by length and message type
        for i in range(0, len(hex_data) - 6, 2):  # Step by 2 (1 byte)
            if hex_data[i:i+2] == '23':  # Found '#'
                # Extract potential RedRat message
                # Format: '23' + length(4 hex chars) + type(2 hex chars) + sequence(4 hex chars) + data
                if i + 12 <= len(hex_data):  # At least header
                    message_start = i
                    length_hex = hex_data[i+2:i+6]  # Next 2 bytes (4 hex chars)
                    type_hex = hex_data[i+6:i+8]    # Next 1 byte (2 hex chars)
                    seq_hex = hex_data[i+8:i+12]    # Next 2 bytes (4 hex chars)
                    
                    try:
                        # Convert length from hex to int (big-endian)
                        length = int(length_hex, 16)
                        message_type = int(type_hex, 16)
                        sequence = int(seq_hex, 16)
                        
                        # Calculate total message length: 1('#') + 2(length) + 1(type) + 2(seq) + data
                        total_length = 12 + (length - 2) * 2  # -2 because length includes seq but not '#'+length+type
                        
                        if message_start + total_length <= len(hex_data):
                            full_message = hex_data[message_start:message_start + total_length]
                            
                            redrat_messages.append({
                                'hex': full_message,
                                'type': message_type,
                                'sequence': sequence,
                                'length': length,
                                'description': get_message_description(message_type)
                            })
                    except ValueError:
                        continue  # Not a valid RedRat message
    
    return redrat_messages

def get_message_description(msg_type):
    """Get human-readable description of RedRat message type"""
    descriptions = {
        0x05: "Power On",
        0x08: "IR Output Trigger", 
        0x09: "Get Device Version",
        0x30: "ASYNC IR Data Upload",
        0x12: "IR Send Complete Response"
    }
    return descriptions.get(msg_type, f"Unknown Type 0x{msg_type:02x}")

def format_hex_bytes(hex_string, bytes_per_line=16):
    """Format hex string with spaces and line breaks"""
    formatted = ""
    for i in range(0, len(hex_string), 2):
        if i > 0 and (i // 2) % bytes_per_line == 0:
            formatted += "\n    "
        formatted += hex_string[i:i+2] + " "
    return formatted.strip()

def compare_messages_byte_by_byte(hub_messages, proxy_messages):
    """Compare RedRat messages byte by byte"""
    print(f"\n🔬 BYTE-BY-BYTE MESSAGE COMPARISON")
    print("="*80)
    
    # Group messages by type for comparison
    hub_by_type = {}
    proxy_by_type = {}
    
    for msg in hub_messages:
        msg_type = msg['type']
        if msg_type not in hub_by_type:
            hub_by_type[msg_type] = []
        hub_by_type[msg_type].append(msg)
    
    for msg in proxy_messages:
        msg_type = msg['type']
        if msg_type not in proxy_by_type:
            proxy_by_type[msg_type] = []
        proxy_by_type[msg_type].append(msg)
    
    # Compare each message type
    all_types = set(hub_by_type.keys()) | set(proxy_by_type.keys())
    
    for msg_type in sorted(all_types):
        print(f"\n📨 Message Type 0x{msg_type:02x} - {get_message_description(msg_type)}")
        print("-" * 60)
        
        hub_msgs = hub_by_type.get(msg_type, [])
        proxy_msgs = proxy_by_type.get(msg_type, [])
        
        print(f"Hub messages: {len(hub_msgs)}, Proxy messages: {len(proxy_msgs)}")
        
        # Compare first message of each type
        if hub_msgs and proxy_msgs:
            hub_hex = hub_msgs[0]['hex']
            proxy_hex = proxy_msgs[0]['hex']
            
            print(f"\n🏢 HUB MESSAGE:")
            print(f"    Length: {len(hub_hex)//2} bytes")
            print(f"    Hex: {format_hex_bytes(hub_hex)}")
            
            print(f"\n🔧 PROXY MESSAGE:")
            print(f"    Length: {len(proxy_hex)//2} bytes") 
            print(f"    Hex: {format_hex_bytes(proxy_hex)}")
            
            # Byte-by-byte comparison
            print(f"\n🔍 BYTE DIFFERENCES:")
            min_len = min(len(hub_hex), len(proxy_hex))
            differences = 0
            
            for i in range(0, min_len, 2):
                hub_byte = hub_hex[i:i+2]
                proxy_byte = proxy_hex[i:i+2]
                
                if hub_byte != proxy_byte:
                    differences += 1
                    byte_pos = i // 2
                    print(f"    Byte {byte_pos:2d}: Hub={hub_byte} vs Proxy={proxy_byte}")
            
            if len(hub_hex) != len(proxy_hex):
                print(f"    Length difference: Hub={len(hub_hex)//2} vs Proxy={len(proxy_hex)//2}")
                differences += abs(len(hub_hex) - len(proxy_hex)) // 2
            
            if differences == 0:
                print(f"    ✅ IDENTICAL! No differences found.")
            else:
                print(f"    ⚠️  Found {differences} byte differences")
        
        elif hub_msgs:
            print(f"    🏢 Hub only: {format_hex_bytes(hub_msgs[0]['hex'])}")
        elif proxy_msgs:
            print(f"    🔧 Proxy only: {format_hex_bytes(proxy_msgs[0]['hex'])}")

def main():
    print("🔬 BYTE-BY-BYTE REDRAT PROTOCOL COMPARISON")
    print("="*80)
    
    hub_pcap = "redrat_proxy_working.pcap"
    proxy_pcap = "hub_vs_proxy_comparison.pcap"
    
    # Extract hex data from both captures
    print("📥 Extracting traffic data...")
    hub_hex_data = extract_hex_bytes_from_pcap(hub_pcap, "Hub Traffic")
    proxy_hex_data = extract_hex_bytes_from_pcap(proxy_pcap, "Proxy Traffic") 
    
    # Find RedRat protocol messages
    print("\n🔍 Locating RedRat protocol messages...")
    hub_messages = find_redrat_messages(hub_hex_data)
    proxy_messages = find_redrat_messages(proxy_hex_data)
    
    print(f"\n📊 DISCOVERY RESULTS:")
    print(f"Hub packets analyzed: {len(hub_hex_data)}")
    print(f"Hub RedRat messages found: {len(hub_messages)}")
    print(f"Proxy packets analyzed: {len(proxy_hex_data)}")
    print(f"Proxy RedRat messages found: {len(proxy_messages)}")
    
    # Show found messages
    print(f"\n🏢 HUB MESSAGES:")
    for i, msg in enumerate(hub_messages):
        print(f"  {i+1}. {msg['description']} (Type: 0x{msg['type']:02x}, Seq: {msg['sequence']}, Len: {len(msg['hex'])//2} bytes)")
    
    print(f"\n🔧 PROXY MESSAGES:")
    for i, msg in enumerate(proxy_messages):
        print(f"  {i+1}. {msg['description']} (Type: 0x{msg['type']:02x}, Seq: {msg['sequence']}, Len: {len(msg['hex'])//2} bytes)")
    
    # Detailed byte-by-byte comparison
    if hub_messages and proxy_messages:
        compare_messages_byte_by_byte(hub_messages, proxy_messages)
    else:
        print(f"\n❌ Cannot compare - insufficient messages found")
        if not hub_messages:
            print("   No hub messages found")
        if not proxy_messages:
            print("   No proxy messages found")
    
    print(f"\n🎯 SUMMARY:")
    print("This comparison shows the exact byte differences between")
    print("the original hub traffic and our proxy implementation.")

if __name__ == "__main__":
    main()