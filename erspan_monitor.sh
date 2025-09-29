#!/bin/bash
# ERSPAN Monitor Setup Script for RedRat Signal Debugging
# This script helps configure ERSPAN monitoring on the remote server

set -e

REMOTE_HOST="access-engineering.nl"
REMOTE_PORT="65001" 
REMOTE_USER="svdleer"
ERSPAN_SESSION_ID="100"
MONITOR_INTERFACE="any"
CAPTURE_TIME="30"

echo "🌐 ERSPAN Monitor Setup for RedRat Signal Debugging"
echo "=================================================="
echo "Remote server: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PORT"
echo "ERSPAN Session ID: $ERSPAN_SESSION_ID"
echo "Monitor duration: $CAPTURE_TIME seconds"
echo ""

# Function to run commands on remote server
run_remote() {
    ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "$1"
}

# Copy analyzer script to remote server
echo "📋 Copying ERSPAN analyzer to remote server..."
scp -P $REMOTE_PORT erspan_analyzer.py $REMOTE_USER@$REMOTE_HOST:/tmp/

# Install dependencies on remote server if needed
echo "📦 Installing dependencies on remote server..."
run_remote "pip3 install --user scapy 2>/dev/null || echo 'scapy already installed or install failed'"

# Create capture script on remote server
echo "📝 Creating capture script on remote server..."
cat > /tmp/erspan_capture.sh << 'EOF'
#!/bin/bash
# ERSPAN Capture Script

CAPTURE_FILE="$1"
DURATION="$2"
INTERFACE="${3:-any}"
FILTER="${4:-proto 47}"

echo "🔴 Starting ERSPAN capture..."
echo "  File: $CAPTURE_FILE"
echo "  Duration: $DURATION seconds"
echo "  Interface: $INTERFACE"
echo "  Filter: $FILTER"

# Start tcpdump capture in background
timeout $DURATION tcpdump -i $INTERFACE -w $CAPTURE_FILE "$FILTER" &
TCPDUMP_PID=$!

echo "📡 Capture started (PID: $TCPDUMP_PID)"
echo "   Capturing for $DURATION seconds..."

# Wait for capture to complete
wait $TCPDUMP_PID
RESULT=$?

if [ $RESULT -eq 0 ] || [ $RESULT -eq 124 ]; then
    echo "✅ Capture completed successfully"
    echo "📁 File: $CAPTURE_FILE ($(ls -lh $CAPTURE_FILE | awk '{print $5}'))"
    
    # Quick analysis
    PACKET_COUNT=$(tcpdump -r $CAPTURE_FILE 2>/dev/null | wc -l)
    echo "📦 Captured $PACKET_COUNT packets"
else
    echo "❌ Capture failed with exit code $RESULT"
    exit 1
fi
EOF

scp -P $REMOTE_PORT /tmp/erspan_capture.sh $REMOTE_USER@$REMOTE_HOST:/tmp/
run_remote "chmod +x /tmp/erspan_capture.sh"

# Function to capture baseline traffic
capture_baseline() {
    echo ""
    echo "📈 STEP 1: Capturing baseline ERSPAN traffic"
    echo "============================================"
    echo "This captures normal network activity without RedRat signals"
    
    BASELINE_FILE="/tmp/erspan_baseline_$(date +%Y%m%d_%H%M%S).pcap"
    
    echo "Press Enter to start baseline capture, or Ctrl+C to skip..."
    read -r
    
    run_remote "/tmp/erspan_capture.sh $BASELINE_FILE $CAPTURE_TIME"
    
    echo "✅ Baseline capture saved as: $BASELINE_FILE"
    echo ""
}

# Function to capture signal traffic
capture_signal_traffic() {
    echo ""
    echo "📡 STEP 2: Capturing RedRat signal traffic" 
    echo "=========================================="
    echo "Now we'll capture traffic while RedRat sends signals"
    
    SIGNAL_FILE="/tmp/erspan_signal_$(date +%Y%m%d_%H%M%S).pcap"
    
    echo "Instructions:"
    echo "1. Press Enter to start signal capture"
    echo "2. Immediately trigger RedRat signals from the web interface"
    echo "3. Send multiple test commands during the ${CAPTURE_TIME}s window"
    echo ""
    echo "Press Enter when ready to start signal capture..."
    read -r
    
    echo "🚨 CAPTURE STARTING IN 3 SECONDS - GET READY TO SEND SIGNALS!"
    sleep 1 && echo "2..." 
    sleep 1 && echo "1..."
    sleep 1 && echo "🔴 CAPTURING NOW - SEND REDRAT SIGNALS!"
    
    run_remote "/tmp/erspan_capture.sh $SIGNAL_FILE $CAPTURE_TIME"
    
    echo "✅ Signal capture saved as: $SIGNAL_FILE"
    echo ""
    
    return 0
}

# Function to analyze captures
analyze_captures() {
    echo ""
    echo "🔍 STEP 3: Analyzing captured traffic"
    echo "====================================="
    
    # Get list of capture files
    echo "📋 Available capture files on remote server:"
    run_remote "ls -la /tmp/erspan_*.pcap 2>/dev/null || echo 'No capture files found'"
    
    echo ""
    echo "Enter baseline file path (or press Enter to skip analysis):"
    read -r BASELINE_PATH
    
    if [ -n "$BASELINE_PATH" ]; then
        echo "Enter signal file path:"
        read -r SIGNAL_PATH
        
        if [ -n "$SIGNAL_PATH" ]; then
            echo "🔬 Analyzing captures..."
            run_remote "cd /tmp && python3 erspan_analyzer.py compare $BASELINE_PATH $SIGNAL_PATH"
        else
            echo "🔬 Analyzing single file..."
            run_remote "cd /tmp && python3 erspan_analyzer.py analyze $BASELINE_PATH"
        fi
    else
        echo "⏭️  Analysis skipped"
    fi
}

# Function to download captures for local analysis
download_captures() {
    echo ""
    echo "💾 STEP 4: Download captures for local analysis"
    echo "=============================================="
    
    # Create local captures directory
    mkdir -p ./captures
    
    echo "📥 Downloading capture files..."
    scp -P $REMOTE_PORT "$REMOTE_USER@$REMOTE_HOST:/tmp/erspan_*.pcap" ./captures/ 2>/dev/null || {
        echo "⚠️  No capture files to download or download failed"
        return 1
    }
    
    echo "✅ Captures downloaded to ./captures/"
    ls -la ./captures/
    
    echo ""
    echo "🔬 You can now analyze locally with:"
    echo "  python3 erspan_analyzer.py compare ./captures/baseline.pcap ./captures/signal.pcap"
}

# Function for live monitoring
live_monitor() {
    echo ""
    echo "👁️  LIVE ERSPAN MONITORING"
    echo "========================"
    echo "This will show live ERSPAN traffic. Useful for real-time debugging."
    echo ""
    echo "Press Enter to start live monitoring (Ctrl+C to stop)..."
    read -r
    
    echo "🔴 Starting live monitor on remote server..."
    run_remote "cd /tmp && sudo python3 erspan_analyzer.py monitor --interface any --filter 'proto 47'"
}

# Main menu
show_menu() {
    echo ""
    echo "🛠️  ERSPAN DEBUGGING MENU"
    echo "========================"
    echo "1) Capture baseline traffic"
    echo "2) Capture RedRat signal traffic" 
    echo "3) Analyze existing captures"
    echo "4) Download captures for local analysis"
    echo "5) Live ERSPAN monitoring"
    echo "6) Show debugging tips"
    echo "7) Exit"
    echo ""
    echo -n "Select option (1-7): "
}

# Debugging tips
show_tips() {
    echo ""
    echo "💡 ERSPAN DEBUGGING TIPS"
    echo "======================="
    echo ""
    echo "🔍 What to look for in comparisons:"
    echo "  • Packet count differences (should increase during signals)"
    echo "  • New IP addresses (RedRat device IP should appear)"
    echo "  • Protocol 47 (GRE) packets (ERSPAN uses GRE encapsulation)"
    echo "  • Timing differences (signals should create traffic bursts)"
    echo ""
    echo "🚨 Common issues:"
    echo "  • No ERSPAN packets = Monitor session not configured properly"
    echo "  • Same packet count = RedRat not sending or network path issue"
    echo "  • Wrong IPs = Check RedRat device network configuration"
    echo ""
    echo "🔧 Troubleshooting steps:"
    echo "  1. Verify RedRat device IP is reachable from Docker container"
    echo "  2. Check Docker network mode (should be 'host' for direct access)"
    echo "  3. Test basic RedRat connectivity from container"
    echo "  4. Verify ERSPAN mirror session captures RedRat traffic"
    echo ""
    echo "📝 Quick RedRat connectivity test:"
    echo "  docker exec -it redrat-proxy_web_1 ping -c 3 <REDRAT_IP>"
    echo "  docker exec -it redrat-proxy_web_1 nc -zv <REDRAT_IP> 10001"
    echo ""
}

# Main script execution
main() {
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1) capture_baseline ;;
            2) capture_signal_traffic ;;
            3) analyze_captures ;;
            4) download_captures ;;
            5) live_monitor ;;
            6) show_tips ;;
            7) echo "👋 Goodbye!"; exit 0 ;;
            *) echo "❌ Invalid option. Please select 1-7." ;;
        esac
        
        echo ""
        echo "Press Enter to continue..."
        read -r
    done
}

# Check if we have the analyzer script
if [ ! -f "erspan_analyzer.py" ]; then
    echo "❌ Error: erspan_analyzer.py not found in current directory"
    echo "   Please make sure you're running this from the redrat-proxy directory"
    exit 1
fi

# Check SSH connectivity
echo "🔌 Testing SSH connectivity to remote server..."
if ! ssh -p $REMOTE_PORT -o ConnectTimeout=5 $REMOTE_USER@$REMOTE_HOST "echo 'SSH OK'" >/dev/null 2>&1; then
    echo "❌ Error: Cannot connect to remote server"
    echo "   Please check SSH credentials and network connectivity"
    exit 1
fi

echo "✅ SSH connectivity verified"

# Run main menu
main