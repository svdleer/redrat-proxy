#!/bin/bash
# ERSPAN Capture Script for RedRat Proxy Traffic Analysis
# Captures ERSPAN mirrored traffic landing on 172.16.6.101

VENV_PATH="/home/svdleer/scripts/python/venv"
CAPTURE_DIR="./captures"
SERVER_IP="172.16.6.101"
REDRAT_PROXY_IP="172.16.6.101"  # RedRat proxy source
REDRAT_DEVICE_IP="172.16.6.62"  # RedRat device target
ORIGINAL_SOURCE_IP="172.16.6.5"  # Original working source for comparison

# Activate virtual environment
source $VENV_PATH/bin/activate

# Create captures directory
mkdir -p $CAPTURE_DIR

echo "🌐 ERSPAN RedRat Proxy Traffic Capture"
echo "======================================"
echo "Server IP (ERSPAN destination): $SERVER_IP"
echo "RedRat Proxy IP: $REDRAT_PROXY_IP" 
echo "RedRat Device IP: $REDRAT_DEVICE_IP"
echo "Original Source IP: $ORIGINAL_SOURCE_IP (for comparison)"
echo "Capture directory: $CAPTURE_DIR"
echo ""

# Function to show current network interfaces and ERSPAN status
show_network_status() {
    echo "🔍 NETWORK STATUS CHECK"
    echo "======================"
    echo ""
    
    echo "📡 Network Interfaces:"
    ip addr show | grep -E "inet.*$SERVER_IP" -A 2 -B 2
    echo ""
    
    echo "🔌 Active Connections to/from key IPs:"
    netstat -an | grep -E "$REDRAT_DEVICE_IP|$ORIGINAL_SOURCE_IP" | head -10
    echo ""
    
    echo "📊 Current ERSPAN/GRE Traffic (5 second sample):"
    timeout 5 tcpdump -i any -c 10 "proto 47" 2>/dev/null | head -10
    echo ""
}

# Function to capture ERSPAN traffic for RedRat proxy
capture_proxy_traffic() {
    echo "📡 CAPTURING REDRAT PROXY ERSPAN TRAFFIC"
    echo "========================================"
    echo "This captures ERSPAN mirrored traffic from RedRat proxy"
    echo ""
    
    PROXY_FILE="$CAPTURE_DIR/redrat_proxy_$(date +%Y%m%d_%H%M%S).pcap"
    DURATION=${1:-30}
    
    # Build specific filter for RedRat proxy traffic
    FILTER="proto 47 and (host $REDRAT_PROXY_IP or host $REDRAT_DEVICE_IP)"
    
    echo "Capture settings:"
    echo "  File: $PROXY_FILE"
    echo "  Duration: ${DURATION}s"
    echo "  Filter: $FILTER"
    echo "  Interface: any"
    echo ""
    
    echo "Instructions:"
    echo "1. This capture will run for ${DURATION} seconds"
    echo "2. Open RedRat web interface: http://$REDRAT_PROXY_IP:5000"
    echo "3. Send multiple test commands during capture"
    echo "4. Try different remotes and commands"
    echo ""
    echo "Press Enter when ready to start capture..."
    read -r
    
    echo "🚨 STARTING PROXY TRAFFIC CAPTURE IN 3 SECONDS..."
    echo "   PREPARE TO SEND REDRAT COMMANDS!"
    sleep 1 && echo "2..."
    sleep 1 && echo "1..."
    sleep 1 && echo ""
    echo "🔴 CAPTURING NOW - SEND REDRAT COMMANDS VIA WEB UI!"
    echo ""
    
    # Start tcpdump with specific filter
    timeout $DURATION tcpdump -i any -w $PROXY_FILE "$FILTER" 2>/dev/null &
    TCPDUMP_PID=$!
    
    # Show countdown with instructions
    for i in $(seq $DURATION -1 1); do
        if [ $i -gt $((DURATION-5)) ]; then
            echo -ne "\r🎯 SEND COMMANDS NOW! Time: ${i}s  "
        elif [ $i -gt 5 ]; then
            echo -ne "\r📡 Keep sending... Time: ${i}s     "
        else
            echo -ne "\r⏱️  Finishing... ${i}s            "
        fi
        sleep 1
    done
    echo ""
    
    wait $TCPDUMP_PID
    
    if [ -f "$PROXY_FILE" ]; then
        SIZE=$(ls -lh $PROXY_FILE | awk '{print $5}')
        PACKETS=$(tcpdump -r $PROXY_FILE 2>/dev/null | wc -l)
        echo "✅ Proxy traffic captured: $PROXY_FILE"
        echo "   Size: $SIZE, Packets: $PACKETS"
        
        # Quick analysis
        if [ $PACKETS -gt 0 ]; then
            echo ""
            echo "📊 Quick Analysis:"
            echo "Unique IPs in capture:"
            tcpdump -r $PROXY_FILE -n 2>/dev/null | awk '{print $3,$5}' | tr '.' ' ' | awk '{print $1"."$2"."$3"."$4}' | sort | uniq -c
        else
            echo "⚠️  No packets captured - ERSPAN might not be configured or proxy not sending traffic"
        fi
        
        echo "$PROXY_FILE" > $CAPTURE_DIR/last_proxy.txt
    else
        echo "❌ Proxy capture failed"
        return 1
    fi
}

# Function to capture baseline ERSPAN traffic
capture_baseline_erspan() {
    echo "📈 CAPTURING BASELINE ERSPAN TRAFFIC"
    echo "==================================="
    echo "This captures all ERSPAN traffic without specific filtering"
    echo ""
    
    BASELINE_FILE="$CAPTURE_DIR/erspan_baseline_$(date +%Y%m%d_%H%M%S).pcap"
    DURATION=15
    
    echo "Capturing all ERSPAN (GRE) traffic for ${DURATION} seconds..."
    echo "File: $BASELINE_FILE"
    echo ""
    
    # Capture all GRE traffic
    timeout $DURATION tcpdump -i any -w $BASELINE_FILE "proto 47" 2>/dev/null &
    TCPDUMP_PID=$!
    
    echo "🔴 Baseline capture running..."
    for i in $(seq $DURATION -1 1); do
        echo -ne "\r⏱️  Time remaining: ${i}s  "
        sleep 1
    done
    echo ""
    
    wait $TCPDUMP_PID
    
    if [ -f "$BASELINE_FILE" ]; then
        SIZE=$(ls -lh $BASELINE_FILE | awk '{print $5}')
        PACKETS=$(tcpdump -r $BASELINE_FILE 2>/dev/null | wc -l)
        echo "✅ Baseline captured: $BASELINE_FILE ($SIZE, $PACKETS packets)"
        echo "$BASELINE_FILE" > $CAPTURE_DIR/last_baseline.txt
        
        if [ $PACKETS -gt 0 ]; then
            echo ""
            echo "📊 ERSPAN Sources Found:"
            tcpdump -r $BASELINE_FILE -n 2>/dev/null | awk '{print $3}' | cut -d. -f1-4 | sort | uniq -c
        fi
    else
        echo "❌ Baseline capture failed"
        return 1
    fi
}

# Function to analyze proxy vs original traffic
compare_with_original() {
    echo ""
    echo "🔍 COMPARE WITH ORIGINAL TRAFFIC"
    echo "==============================="
    
    echo "Available capture files:"
    ls -la $CAPTURE_DIR/*.pcap 2>/dev/null | while read -r line; do
        FILE=$(echo $line | awk '{print $9}')
        PACKETS=$(tcpdump -r "$FILE" 2>/dev/null | wc -l)
        echo "  $(basename $FILE): $PACKETS packets"
    done
    echo ""
    
    echo "Do you have original working PCAP files to compare? (y/n)"
    read -r HAS_ORIGINAL
    
    if [ "$HAS_ORIGINAL" = "y" ]; then
        echo "Enter path to original working PCAP file:"
        read -r ORIGINAL_FILE
        
        if [ -f "$ORIGINAL_FILE" ]; then
            if [ -f "$CAPTURE_DIR/last_proxy.txt" ]; then
                PROXY_FILE=$(cat $CAPTURE_DIR/last_proxy.txt)
                echo ""
                echo "Comparing original vs proxy traffic..."
                python erspan_analyzer.py compare "$ORIGINAL_FILE" "$PROXY_FILE"
            else
                echo "No recent proxy capture found. Please capture proxy traffic first."
            fi
        else
            echo "Original file not found: $ORIGINAL_FILE"
        fi
    else
        echo "To get original PCAPs, please provide the path where they are stored."
    fi
}

# Function to test ERSPAN monitoring setup
test_erspan_setup() {
    echo ""
    echo "🔧 TESTING ERSPAN SETUP"
    echo "======================"
    echo ""
    
    echo "1. Testing if ERSPAN traffic is reaching this server..."
    echo "   Looking for GRE (protocol 47) traffic for 10 seconds..."
    
    SAMPLE_COUNT=$(timeout 10 tcpdump -i any -c 50 "proto 47" 2>/dev/null | wc -l)
    
    if [ $SAMPLE_COUNT -gt 0 ]; then
        echo "✅ ERSPAN traffic detected: $SAMPLE_COUNT packets in 10 seconds"
        echo ""
        echo "📊 ERSPAN Source IPs:"
        timeout 5 tcpdump -i any -n "proto 47" 2>/dev/null | awk '{print $3}' | cut -d. -f1-4 | sort | uniq -c
    else
        echo "❌ No ERSPAN traffic detected"
        echo ""
        echo "Possible issues:"
        echo "- ERSPAN mirror session not configured"
        echo "- Wrong ERSPAN destination IP"
        echo "- Firewall blocking GRE traffic"
        echo "- RedRat proxy not generating traffic"
    fi
    
    echo ""
    echo "2. Testing RedRat device connectivity..."
    if ping -c 3 -W 2 $REDRAT_DEVICE_IP >/dev/null 2>&1; then
        echo "✅ RedRat device ($REDRAT_DEVICE_IP) is reachable"
    else
        echo "❌ RedRat device ($REDRAT_DEVICE_IP) is not reachable"
    fi
    
    echo ""
    echo "3. Testing RedRat proxy connectivity..."
    if curl -s --connect-timeout 5 "http://$REDRAT_PROXY_IP:5000" >/dev/null; then
        echo "✅ RedRat proxy web interface is accessible"
    else
        echo "❌ RedRat proxy web interface is not accessible"
    fi
}

# Function to monitor live ERSPAN traffic
monitor_live_erspan() {
    echo ""
    echo "👁️  LIVE ERSPAN MONITORING"
    echo "========================="
    echo "Monitoring live ERSPAN traffic. Press Ctrl+C to stop."
    echo ""
    
    # Show live traffic with detailed info
    tcpdump -i any -n -l "proto 47" | while read line; do
        TIMESTAMP=$(date '+%H:%M:%S')
        echo "[$TIMESTAMP] $line"
    done
}

# Main menu
show_menu() {
    echo ""
    echo "🛠️  ERSPAN REDRAT PROXY DEBUG MENU"
    echo "=================================="
    echo "1) Show network status"
    echo "2) Capture RedRat proxy traffic (30s)"
    echo "3) Capture baseline ERSPAN traffic (15s)"
    echo "4) Compare with original PCAP files"
    echo "5) Test ERSPAN setup"
    echo "6) Monitor live ERSPAN traffic"
    echo "7) Quick proxy test (capture + basic analysis)"
    echo "8) List capture files"
    echo "9) Exit"
    echo ""
    echo -n "Select option (1-9): "
}

# Quick test function
quick_proxy_test() {
    echo ""
    echo "🚀 QUICK REDRAT PROXY TEST"
    echo "========================="
    echo "This will capture proxy traffic and do basic analysis"
    echo ""
    
    # First check if ERSPAN is working
    echo "Testing ERSPAN connectivity first..."
    ERSPAN_TEST=$(timeout 5 tcpdump -i any -c 5 "proto 47" 2>/dev/null | wc -l)
    
    if [ $ERSPAN_TEST -eq 0 ]; then
        echo "⚠️  No ERSPAN traffic detected in 5 second test"
        echo "   ERSPAN mirror session might not be configured properly"
        echo ""
        echo "Continue anyway? (y/n)"
        read -r CONTINUE
        [ "$CONTINUE" != "y" ] && return 1
    else
        echo "✅ ERSPAN traffic detected - proceeding with capture"
    fi
    
    echo ""
    echo "Press Enter to start 30-second proxy traffic capture..."
    read -r
    
    capture_proxy_traffic 30
}

# List capture files
list_captures() {
    echo ""
    echo "📋 CAPTURE FILES"
    echo "==============="
    
    if [ -d "$CAPTURE_DIR" ] && [ "$(ls -A $CAPTURE_DIR/*.pcap 2>/dev/null)" ]; then
        echo "Files in $CAPTURE_DIR:"
        ls -la $CAPTURE_DIR/*.pcap | while read -r line; do
            FILE=$(echo $line | awk '{print $9}')
            SIZE=$(echo $line | awk '{print $5}')
            DATE=$(echo $line | awk '{print $6, $7, $8}')
            PACKETS=$(tcpdump -r "$FILE" 2>/dev/null | wc -l)
            echo "  $(basename $FILE): $SIZE, $PACKETS packets ($DATE)"
        done
    else
        echo "No capture files found in $CAPTURE_DIR"
    fi
}

# Main loop
main() {
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1) show_network_status ;;
            2) capture_proxy_traffic 30 ;;
            3) capture_baseline_erspan ;;
            4) compare_with_original ;;
            5) test_erspan_setup ;;
            6) monitor_live_erspan ;;
            7) quick_proxy_test ;;
            8) list_captures ;;
            9) echo "👋 Goodbye!"; exit 0 ;;
            *) echo "❌ Invalid option. Please select 1-9." ;;
        esac
        
        echo ""
        echo "Press Enter to continue..."
        read -r
    done
}

# Initial checks
echo "🔍 Initial System Check:"
echo "========================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Running as non-root. tcpdump might need sudo privileges."
    echo "   If captures fail, run with: sudo $0"
else
    echo "✅ Running as root - tcpdump access OK"
fi

# Check if server IP is configured
if ip addr | grep -q "$SERVER_IP"; then
    echo "✅ Server IP $SERVER_IP is configured"
else
    echo "⚠️  Server IP $SERVER_IP not found in network config"
fi

# Quick ERSPAN test
echo "📡 Testing for ERSPAN traffic (3 second sample)..."
ERSPAN_COUNT=$(timeout 3 tcpdump -i any -c 10 "proto 47" 2>/dev/null | wc -l)
if [ $ERSPAN_COUNT -gt 0 ]; then
    echo "✅ ERSPAN traffic detected ($ERSPAN_COUNT packets)"
else
    echo "⚠️  No ERSPAN traffic in 3-second test"
fi

echo ""

# Run main menu
main