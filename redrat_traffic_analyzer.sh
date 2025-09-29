#!/bin/bash
# RedRat Traffic Comparison Script
# Compares original working signals vs RedRat proxy signals

VENV_PATH="/home/svdleer/scripts/python/venv"

# Activate virtual environment
source $VENV_PATH/bin/activate

echo "🔍 RedRat Traffic Analysis & Comparison"
echo "======================================"
echo "Original signals:    172.16.6.5  → 172.16.6.62 (RedRat)"
echo "RedRat proxy signals: 172.16.6.101 → 172.16.6.62 (RedRat)"
echo ""

# Function to analyze a single PCAP for RedRat traffic
analyze_redrat_pcap() {
    local pcap_file="$1"
    local description="$2"
    
    if [ ! -f "$pcap_file" ]; then
        echo "❌ File not found: $pcap_file"
        return 1
    fi
    
    echo "📁 Analyzing: $description"
    echo "   File: $pcap_file"
    
    # Use tcpdump for basic analysis first
    echo "   Size: $(ls -lh "$pcap_file" | awk '{print $5}')"
    
    # Count total packets
    TOTAL_PACKETS=$(tcpdump -r "$pcap_file" 2>/dev/null | wc -l)
    echo "   Total packets: $TOTAL_PACKETS"
    
    # Count packets involving RedRat device (172.16.6.62)
    REDRAT_PACKETS=$(tcpdump -r "$pcap_file" "host 172.16.6.62" 2>/dev/null | wc -l)
    echo "   RedRat packets (172.16.6.62): $REDRAT_PACKETS"
    
    # Count packets from original source (172.16.6.5)
    ORIGINAL_PACKETS=$(tcpdump -r "$pcap_file" "src 172.16.6.5" 2>/dev/null | wc -l)
    echo "   From original (172.16.6.5): $ORIGINAL_PACKETS"
    
    # Count packets from proxy source (172.16.6.101)
    PROXY_PACKETS=$(tcpdump -r "$pcap_file" "src 172.16.6.101" 2>/dev/null | wc -l)
    echo "   From proxy (172.16.6.101): $PROXY_PACKETS"
    
    # Show unique IP addresses
    echo "   Unique IPs:"
    tcpdump -r "$pcap_file" -n 2>/dev/null | awk '{print $3, $5}' | tr '.' ' ' | awk '{print $1"."$2"."$3"."$4}' | sort -u | grep -E "^[0-9]+\." | head -10 | sed 's/^/      /'
    
    # Show protocols
    echo "   Protocols:"
    tcpdump -r "$pcap_file" -n 2>/dev/null | awk '{print $4}' | sort | uniq -c | sort -nr | head -5 | sed 's/^/      /'
    
    # Check for RedRat specific traffic (port 10001)
    REDRAT_PORT_PACKETS=$(tcpdump -r "$pcap_file" "port 10001" 2>/dev/null | wc -l)
    echo "   RedRat port 10001 packets: $REDRAT_PORT_PACKETS"
    
    echo ""
}

# Function to compare two PCAPs in detail
compare_pcaps() {
    local original_pcap="$1"
    local proxy_pcap="$2"
    
    echo "🔬 DETAILED COMPARISON"
    echo "====================="
    echo "Original: $original_pcap"
    echo "Proxy:    $proxy_pcap"
    echo ""
    
    if [ ! -f "$original_pcap" ] || [ ! -f "$proxy_pcap" ]; then
        echo "❌ One or both PCAP files not found"
        return 1
    fi
    
    # Use Python script for detailed analysis
    python3 << EOF
import sys
sys.path.append('.')

try:
    from scapy.all import *
    from scapy.layers.inet import IP, TCP, UDP
    import json
    
    def analyze_pcap_detailed(filename, description):
        print(f"📊 {description}")
        print("-" * 40)
        
        try:
            packets = rdpcap(filename)
            
            analysis = {
                'total_packets': len(packets),
                'redrat_ip_packets': 0,
                'port_10001_packets': 0,
                'tcp_packets': 0,
                'udp_packets': 0,
                'unique_src_ips': set(),
                'unique_dst_ips': set(),
                'packet_sizes': [],
                'redrat_conversations': [],
                'port_10001_data': []
            }
            
            for pkt in packets:
                analysis['packet_sizes'].append(len(pkt))
                
                if pkt.haslayer(IP):
                    src_ip = pkt[IP].src
                    dst_ip = pkt[IP].dst
                    
                    analysis['unique_src_ips'].add(src_ip)
                    analysis['unique_dst_ips'].add(dst_ip)
                    
                    # Check for RedRat device involvement
                    if src_ip == '172.16.6.62' or dst_ip == '172.16.6.62':
                        analysis['redrat_ip_packets'] += 1
                        analysis['redrat_conversations'].append({
                            'src': src_ip,
                            'dst': dst_ip,
                            'size': len(pkt),
                            'time': float(pkt.time)
                        })
                    
                    if pkt.haslayer(TCP):
                        analysis['tcp_packets'] += 1
                        if pkt[TCP].sport == 10001 or pkt[TCP].dport == 10001:
                            analysis['port_10001_packets'] += 1
                            # Capture some payload data if available
                            if pkt.haslayer(Raw):
                                payload = bytes(pkt[Raw])[:50]  # First 50 bytes
                                analysis['port_10001_data'].append({
                                    'src': src_ip,
                                    'dst': dst_ip,
                                    'payload_hex': payload.hex(),
                                    'payload_len': len(bytes(pkt[Raw])),
                                    'time': float(pkt.time)
                                })
                    
                    elif pkt.haslayer(UDP):
                        analysis['udp_packets'] += 1
            
            # Print analysis
            print(f"Total packets: {analysis['total_packets']}")
            print(f"RedRat IP involved: {analysis['redrat_ip_packets']}")
            print(f"Port 10001 packets: {analysis['port_10001_packets']}")
            print(f"TCP packets: {analysis['tcp_packets']}")
            print(f"UDP packets: {analysis['udp_packets']}")
            print(f"Average packet size: {sum(analysis['packet_sizes'])/len(analysis['packet_sizes']):.1f} bytes")
            
            print(f"Source IPs: {sorted(list(analysis['unique_src_ips']))[:10]}")
            print(f"Dest IPs: {sorted(list(analysis['unique_dst_ips']))[:10]}")
            
            # Show RedRat conversations
            if analysis['redrat_conversations']:
                print("\\nRedRat conversations (first 5):")
                for i, conv in enumerate(analysis['redrat_conversations'][:5]):
                    print(f"  {conv['src']} → {conv['dst']} ({conv['size']} bytes)")
            
            # Show port 10001 data
            if analysis['port_10001_data']:
                print("\\nPort 10001 data (first 3):")
                for i, data in enumerate(analysis['port_10001_data'][:3]):
                    print(f"  {data['src']} → {data['dst']}: {data['payload_len']} bytes")
                    print(f"    Hex: {data['payload_hex'][:40]}...")
            
            print("")
            return analysis
            
        except Exception as e:
            print(f"Error analyzing {filename}: {str(e)}")
            return None
    
    # Analyze both files
    original_analysis = analyze_pcap_detailed("$original_pcap", "ORIGINAL SIGNALS")
    proxy_analysis = analyze_pcap_detailed("$proxy_pcap", "PROXY SIGNALS")
    
    # Compare key metrics
    if original_analysis and proxy_analysis:
        print("🔍 KEY DIFFERENCES")
        print("=" * 30)
        
        print(f"Total packets: {original_analysis['total_packets']} → {proxy_analysis['total_packets']} (diff: {proxy_analysis['total_packets'] - original_analysis['total_packets']:+d})")
        
        print(f"RedRat packets: {original_analysis['redrat_ip_packets']} → {proxy_analysis['redrat_ip_packets']} (diff: {proxy_analysis['redrat_ip_packets'] - original_analysis['redrat_ip_packets']:+d})")
        
        print(f"Port 10001 packets: {original_analysis['port_10001_packets']} → {proxy_analysis['port_10001_packets']} (diff: {proxy_analysis['port_10001_packets'] - original_analysis['port_10001_packets']:+d})")
        
        # Check if proxy has any RedRat communication at all
        if proxy_analysis['redrat_ip_packets'] == 0:
            print("\\n❌ CRITICAL: Proxy PCAP has NO packets involving RedRat device (172.16.6.62)")
            print("   This suggests network connectivity issues between proxy and RedRat")
        
        if proxy_analysis['port_10001_packets'] == 0:
            print("\\n❌ CRITICAL: Proxy PCAP has NO packets on RedRat port 10001")
            print("   This suggests the proxy is not communicating with RedRat service")
            
        # Check source IPs
        original_src_ips = original_analysis['unique_src_ips']
        proxy_src_ips = proxy_analysis['unique_src_ips']
        
        if '172.16.6.5' in original_src_ips and '172.16.6.101' not in proxy_src_ips:
            print("\\n⚠️  Expected proxy source IP (172.16.6.101) not found in proxy PCAP")
        
        if '172.16.6.101' in proxy_src_ips:
            print("\\n✅ Proxy source IP (172.16.6.101) found in proxy PCAP")

except ImportError:
    print("❌ Scapy not available for detailed analysis")
except Exception as e:
    print(f"❌ Analysis error: {str(e)}")
EOF
}

# Function to capture new proxy traffic
capture_proxy_traffic() {
    echo "📡 CAPTURING NEW PROXY TRAFFIC"
    echo "=============================="
    echo "This will capture traffic while you send commands via RedRat proxy"
    echo ""
    
    local capture_file="./captures/proxy_capture_$(date +%Y%m%d_%H%M%S).pcap"
    mkdir -p ./captures
    
    echo "Instructions:"
    echo "1. This will capture for 30 seconds"
    echo "2. Open RedRat proxy web interface"
    echo "3. Send multiple commands during capture"
    echo "4. Try different remotes/commands"
    echo ""
    echo "Press Enter to start capture..."
    read -r
    
    echo "🚨 STARTING CAPTURE IN 3 SECONDS..."
    sleep 1 && echo "2..."
    sleep 1 && echo "1..."
    sleep 1 && echo ""
    echo "🔴 CAPTURING - SEND REDRAT PROXY COMMANDS NOW!"
    
    # Capture all traffic involving RedRat IPs
    timeout 30 tcpdump -i any -w "$capture_file" "host 172.16.6.62 or host 172.16.6.101 or host 172.16.6.5 or port 10001" 2>/dev/null &
    TCPDUMP_PID=$!
    
    # Countdown
    for i in $(seq 30 -1 1); do
        echo -ne "\r📡 SEND COMMANDS! Time: ${i}s  "
        sleep 1
    done
    echo ""
    
    wait $TCPDUMP_PID
    
    if [ -f "$capture_file" ]; then
        echo "✅ Capture saved: $capture_file"
        analyze_redrat_pcap "$capture_file" "NEW PROXY CAPTURE"
        echo "$capture_file" > ./captures/latest_proxy_capture.txt
    else
        echo "❌ Capture failed"
    fi
}

# Function to list available PCAPs
list_pcaps() {
    echo "📋 AVAILABLE PCAP FILES"
    echo "======================"
    
    echo "Current directory:"
    ls -la *.pcap 2>/dev/null | while read -r line; do
        file=$(echo $line | awk '{print $9}')
        size=$(echo $line | awk '{print $5}')
        echo "  $file ($size bytes)"
    done
    
    echo ""
    echo "Captures directory:"
    ls -la ./captures/*.pcap 2>/dev/null | while read -r line; do
        file=$(echo $line | awk '{print $9}')
        size=$(echo $line | awk '{print $5}')
        echo "  $file ($size bytes)"
    done
    
    if [ ! "$(ls -A *.pcap ./captures/*.pcap 2>/dev/null)" ]; then
        echo "No PCAP files found"
    fi
}

# Function to test connectivity
test_connectivity() {
    echo "🔌 TESTING REDRAT CONNECTIVITY"
    echo "============================="
    
    # Test from host
    echo "Testing from host server (172.16.6.101):"
    
    if ping -c 2 -W 2 172.16.6.62 >/dev/null 2>&1; then
        echo "  ✅ Ping to RedRat (172.16.6.62): OK"
    else
        echo "  ❌ Ping to RedRat (172.16.6.62): FAILED"
    fi
    
    if nc -zv 172.16.6.62 10001 2>/dev/null; then
        echo "  ✅ RedRat port 10001: OPEN"
    else
        echo "  ❌ RedRat port 10001: CLOSED or FILTERED"
    fi
    
    # Test from Docker container
    echo ""
    echo "Testing from Docker container:"
    
    if docker exec redrat-proxy_web_1 ping -c 2 172.16.6.62 >/dev/null 2>&1; then
        echo "  ✅ Docker ping to RedRat: OK"
    else
        echo "  ❌ Docker ping to RedRat: FAILED"
    fi
    
    if docker exec redrat-proxy_web_1 nc -zv 172.16.6.62 10001 2>/dev/null; then
        echo "  ✅ Docker RedRat port 10001: OPEN"
    else
        echo "  ❌ Docker RedRat port 10001: CLOSED"
    fi
    
    # Check Docker network mode
    echo ""
    echo "Docker network configuration:"
    docker inspect redrat-proxy_web_1 | grep -A 5 NetworkMode || echo "  Could not get network info"
}

# Main menu
show_menu() {
    echo ""
    echo "🛠️  REDRAT TRAFFIC ANALYSIS MENU"
    echo "==============================="
    echo "1) List available PCAP files"
    echo "2) Analyze single PCAP file"
    echo "3) Compare original vs proxy PCAPs"
    echo "4) Capture new proxy traffic"
    echo "5) Test RedRat connectivity"
    echo "6) Exit"
    echo ""
    echo -n "Select option (1-6): "
}

# Main loop
main() {
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1) list_pcaps ;;
            2) 
                echo "Enter PCAP file path:"
                read -r pcap_file
                if [ -n "$pcap_file" ]; then
                    analyze_redrat_pcap "$pcap_file" "USER SPECIFIED"
                fi
                ;;
            3)
                echo "Enter original PCAP file path:"
                read -r original_pcap
                echo "Enter proxy PCAP file path:"
                read -r proxy_pcap
                if [ -n "$original_pcap" ] && [ -n "$proxy_pcap" ]; then
                    compare_pcaps "$original_pcap" "$proxy_pcap"
                fi
                ;;
            4) capture_proxy_traffic ;;
            5) test_connectivity ;;
            6) echo "👋 Goodbye!"; exit 0 ;;
            *) echo "❌ Invalid option. Please select 1-6." ;;
        esac
        
        echo ""
        echo "Press Enter to continue..."
        read -r
    done
}

# Run main menu
main