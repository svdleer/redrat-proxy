#!/bin/bash
# RedRat Signal Comparison Script
# Run this on the remote server (access-engineering.nl)
# Usage: ./signal_comparison.sh

set -e

SERVER="access-engineering.nl"
SSH_PORT="65001"
USER="svdleer"

echo "=== RedRat Signal Comparison Setup ==="
echo "Server: $SERVER:$SSH_PORT"
echo "Date: $(date)"
echo

# Check if we're running on the remote server
if [[ $(hostname) != *"engineering"* ]]; then
    echo "❌ This script should be run ON the remote server"
    echo "Please SSH to the server first:"
    echo "ssh -p $SSH_PORT $USER@$SERVER"
    exit 1
fi

echo "✅ Running on remote server"

# Create comparison directory
COMPARISON_DIR="/tmp/redrat_signal_comparison_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$COMPARISON_DIR"
echo "📁 Created comparison directory: $COMPARISON_DIR"

# Check Docker status
echo
echo "🐳 Checking Docker status..."
sudo docker ps | grep -E "(redrat|proxy)" || echo "No RedRat containers found"

echo
echo "📊 ERSPAN capture setup..."
echo "Please configure ERSPAN to capture traffic to/from RedRat device IP"
echo "Typical RedRat devices use port 10001"

# Function to capture signals
capture_signal() {
    local tool_name=$1
    local command_name=$2
    local capture_file="$COMPARISON_DIR/capture_${tool_name}_${command_name}_$(date +%H%M%S).pcap"
    
    echo "🎯 Capturing $tool_name signal for command: $command_name"
    
    # Start packet capture (adjust interface as needed)
    echo "Starting packet capture to: $capture_file"
    echo "Press ENTER when ready to start capture..."
    read
    
    # Start tcpdump in background
    sudo tcpdump -i any -w "$capture_file" host [REDRAT_IP] and port 10001 &
    TCPDUMP_PID=$!
    
    echo "🔴 Capture started (PID: $TCPDUMP_PID)"
    echo "Now execute the $tool_name command for: $command_name"
    echo "Press ENTER when command execution is complete..."
    read
    
    # Stop capture
    sudo kill $TCPDUMP_PID 2>/dev/null || true
    sleep 2
    
    echo "⏹️  Capture stopped. File: $capture_file"
    
    # Basic analysis
    if [[ -f "$capture_file" ]]; then
        echo "📈 Capture statistics:"
        echo "  File size: $(ls -lh "$capture_file" | awk '{print $5}')"
        echo "  Packet count: $(sudo tcpdump -r "$capture_file" 2>/dev/null | wc -l)"
    fi
    
    echo
}

# Function to analyze captured signals
analyze_signals() {
    echo "🔬 Analyzing captured signals..."
    
    for pcap_file in "$COMPARISON_DIR"/*.pcap; do
        if [[ -f "$pcap_file" ]]; then
            echo "📋 Analysis of $(basename "$pcap_file"):"
            
            # Extract timing information
            echo "  Timing analysis:"
            sudo tcpdump -r "$pcap_file" -tt 2>/dev/null | head -10
            
            # Extract packet sizes
            echo "  Packet size distribution:"
            sudo tcpdump -r "$pcap_file" -q 2>/dev/null | awk '{print $NF}' | grep -o '[0-9]*' | sort -n | uniq -c
            
            echo "  ---"
        fi
    done
    
    echo "📁 All captures stored in: $COMPARISON_DIR"
}

# Main comparison workflow
main() {
    echo "🚀 Starting RedRat Signal Comparison"
    echo
    echo "This script will help you capture and compare IR signals between:"
    echo "1. Your RedRat Proxy tool (Docker)"
    echo "2. Official RedRat tool"
    echo
    echo "Prerequisites:"
    echo "- ERSPAN configured to capture RedRat traffic"
    echo "- RedRat device accessible"
    echo "- Both tools available"
    echo
    
    read -p "Ready to proceed? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled"
        exit 1
    fi
    
    # Get RedRat device IP
    read -p "Enter RedRat device IP address: " REDRAT_IP
    if [[ -z "$REDRAT_IP" ]]; then
        echo "❌ RedRat IP required"
        exit 1
    fi
    
    # Update script with actual IP
    sed -i "s/\[REDRAT_IP\]/$REDRAT_IP/g" "$0"
    
    # Get command to test
    read -p "Enter command name to test (e.g., 'power_on'): " COMMAND_NAME
    if [[ -z "$COMMAND_NAME" ]]; then
        COMMAND_NAME="power_on"
    fi
    
    echo
    echo "📋 Test Configuration:"
    echo "  RedRat IP: $REDRAT_IP"
    echo "  Command: $COMMAND_NAME"
    echo "  Capture Dir: $COMPARISON_DIR"
    echo
    
    # Capture proxy tool signal
    echo "=== Step 1: Capture RedRat Proxy Tool Signal ==="
    capture_signal "proxy" "$COMMAND_NAME"
    
    # Capture official tool signal  
    echo "=== Step 2: Capture Official RedRat Tool Signal ==="
    capture_signal "official" "$COMMAND_NAME"
    
    # Analyze results
    echo "=== Step 3: Analysis ==="
    analyze_signals
    
    echo
    echo "✅ Signal comparison complete!"
    echo "📁 Results available in: $COMPARISON_DIR"
    echo
    echo "🔍 Next steps:"
    echo "1. Compare packet timing between captures"
    echo "2. Analyze signal power levels"
    echo "3. Compare IR data payloads"
    echo "4. Check for timing differences"
}

# Check if running as comparison
if [[ "$1" == "compare" ]]; then
    main
else
    echo "RedRat Signal Comparison Script"
    echo "Usage: $0 compare"
    echo
    echo "This script helps compare IR signals between your RedRat proxy and official tools"
fi
