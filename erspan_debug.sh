#!/bin/bash
# ERSPAN Debug Script using remote venv
# Simplified version for direct SSH session debugging

VENV_PATH="/home/svdleer/scripts/python/venv"
CAPTURE_DIR="./captures"

# Activate virtual environment
source $VENV_PATH/bin/activate

# Create captures directory
mkdir -p $CAPTURE_DIR

echo "🌐 ERSPAN Debugging for RedRat Signals"
echo "======================================"
echo "Virtual env: $VENV_PATH"
echo "Capture dir: $CAPTURE_DIR"
echo ""

# Function to capture baseline traffic
capture_baseline() {
    echo "📈 CAPTURING BASELINE TRAFFIC"
    echo "============================="
    echo "This captures normal network activity without RedRat signals"
    echo ""
    
    BASELINE_FILE="$CAPTURE_DIR/baseline_$(date +%Y%m%d_%H%M%S).pcap"
    DURATION=15
    
    echo "Starting baseline capture for $DURATION seconds..."
    echo "Capturing ERSPAN traffic (GRE protocol 47)..."
    echo ""
    
    # Capture ERSPAN traffic (GRE protocol 47)
    timeout $DURATION tcpdump -i any -w $BASELINE_FILE "proto 47" 2>/dev/null &
    TCPDUMP_PID=$!
    
    echo "🔴 Capture running (PID: $TCPDUMP_PID)..."
    
    # Show countdown
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
    else
        echo "❌ Baseline capture failed"
        return 1
    fi
}

# Function to capture signal traffic
capture_signals() {
    echo ""
    echo "📡 CAPTURING REDRAT SIGNAL TRAFFIC"
    echo "=================================="
    echo "Now we'll capture traffic while RedRat sends signals"
    echo ""
    
    SIGNAL_FILE="$CAPTURE_DIR/signals_$(date +%Y%m%d_%H%M%S).pcap"
    DURATION=20
    
    echo "Instructions:"
    echo "1. This capture will run for $DURATION seconds"
    echo "2. Open RedRat web interface in browser"
    echo "3. Send multiple test commands during the capture window"
    echo "4. Try different remotes/commands to generate traffic"
    echo ""
    echo "Press Enter when ready to start signal capture..."
    read -r
    
    echo "🚨 STARTING SIGNAL CAPTURE IN 3 SECONDS..."
    echo "   GET READY TO SEND REDRAT SIGNALS!"
    sleep 1 && echo "2..."
    sleep 1 && echo "1..."
    sleep 1 && echo ""
    echo "🔴 CAPTURING NOW - SEND REDRAT SIGNALS VIA WEB INTERFACE!"
    echo ""
    
    # Start capture
    timeout $DURATION tcpdump -i any -w $SIGNAL_FILE "proto 47" 2>/dev/null &
    TCPDUMP_PID=$!
    
    # Show countdown with instructions
    for i in $(seq $DURATION -1 1); do
        if [ $i -gt 15 ]; then
            echo -ne "\r🎯 SEND SIGNALS NOW! Time remaining: ${i}s  "
        elif [ $i -gt 5 ]; then
            echo -ne "\r📡 Keep sending signals... Time remaining: ${i}s  "
        else
            echo -ne "\r⏱️  Finishing capture... ${i}s  "
        fi
        sleep 1
    done
    echo ""
    
    wait $TCPDUMP_PID
    
    if [ -f "$SIGNAL_FILE" ]; then
        SIZE=$(ls -lh $SIGNAL_FILE | awk '{print $5}')
        PACKETS=$(tcpdump -r $SIGNAL_FILE 2>/dev/null | wc -l)
        echo "✅ Signals captured: $SIGNAL_FILE ($SIZE, $PACKETS packets)"
        echo "$SIGNAL_FILE" > $CAPTURE_DIR/last_signal.txt
    else
        echo "❌ Signal capture failed"
        return 1
    fi
}

# Function to analyze captures
analyze_captures() {
    echo ""
    echo "🔍 ANALYZING CAPTURES"
    echo "===================="
    
    # Get last captured files
    if [ -f "$CAPTURE_DIR/last_baseline.txt" ] && [ -f "$CAPTURE_DIR/last_signal.txt" ]; then
        BASELINE=$(cat $CAPTURE_DIR/last_baseline.txt)
        SIGNAL=$(cat $CAPTURE_DIR/last_signal.txt)
        
        echo "Comparing:"
        echo "  Baseline: $(basename $BASELINE)"
        echo "  Signal:   $(basename $SIGNAL)"
        echo ""
        
        python erspan_analyzer.py compare "$BASELINE" "$SIGNAL"
    else
        echo "❌ No recent captures found. Please capture baseline and signals first."
        return 1
    fi
}

# Function to show capture files
list_captures() {
    echo ""
    echo "📋 AVAILABLE CAPTURES"
    echo "===================="
    
    if [ -d "$CAPTURE_DIR" ] && [ "$(ls -A $CAPTURE_DIR/*.pcap 2>/dev/null)" ]; then
        echo "Capture files in $CAPTURE_DIR:"
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

# Function to test RedRat connectivity
test_redrat_connectivity() {
    echo ""
    echo "🔌 TESTING REDRAT CONNECTIVITY"
    echo "=============================="
    
    # Get RedRat IP from Docker container or environment
    echo "Checking RedRat device connectivity..."
    
    # Try to get RedRat IP from Docker container logs or config
    REDRAT_IP=$(docker exec redrat-proxy_web_1 printenv | grep -i redrat | head -1 | cut -d'=' -f2 2>/dev/null || echo "")
    
    if [ -z "$REDRAT_IP" ]; then
        echo "Enter RedRat device IP address (e.g., 172.16.6.62):"
        read -r REDRAT_IP
    fi
    
    if [ -n "$REDRAT_IP" ]; then
        echo "Testing connectivity to RedRat at $REDRAT_IP..."
        
        # Test ping
        if ping -c 3 -W 2 "$REDRAT_IP" >/dev/null 2>&1; then
            echo "✅ Ping successful to $REDRAT_IP"
        else
            echo "❌ Ping failed to $REDRAT_IP"
        fi
        
        # Test port 10001
        if nc -zv "$REDRAT_IP" 10001 2>/dev/null; then
            echo "✅ Port 10001 is open on $REDRAT_IP"
        else
            echo "❌ Port 10001 is not accessible on $REDRAT_IP"
        fi
        
        # Test from Docker container
        if docker exec redrat-proxy_web_1 nc -zv "$REDRAT_IP" 10001 2>/dev/null; then
            echo "✅ Docker container can reach RedRat device"
        else
            echo "❌ Docker container cannot reach RedRat device"
        fi
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "🛠️  ERSPAN DEBUG MENU"
    echo "===================="
    echo "1) Capture baseline traffic (no signals)"
    echo "2) Capture RedRat signal traffic"
    echo "3) Compare baseline vs signals"
    echo "4) List capture files"
    echo "5) Test RedRat connectivity"
    echo "6) Quick test (baseline + signals + analysis)"
    echo "7) Exit"
    echo ""
    echo -n "Select option (1-7): "
}

# Quick test function
quick_test() {
    echo ""
    echo "🚀 QUICK ERSPAN TEST"
    echo "==================="
    echo "This will do a complete baseline + signal + analysis cycle"
    echo ""
    echo "Press Enter to continue or Ctrl+C to cancel..."
    read -r
    
    capture_baseline
    if [ $? -eq 0 ]; then
        echo ""
        echo "Press Enter to start signal capture..."
        read -r
        capture_signals
        if [ $? -eq 0 ]; then
            analyze_captures
        fi
    fi
}

# Main loop
main() {
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1) capture_baseline ;;
            2) capture_signals ;;
            3) analyze_captures ;;
            4) list_captures ;;
            5) test_redrat_connectivity ;;
            6) quick_test ;;
            7) echo "👋 Goodbye!"; exit 0 ;;
            *) echo "❌ Invalid option. Please select 1-7." ;;
        esac
        
        echo ""
        echo "Press Enter to continue..."
        read -r
    done
}

# Check if running as root for tcpdump
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Note: Running as non-root user. tcpdump might need sudo privileges."
    echo "   If captures fail, run with: sudo $0"
    echo ""
fi

# Check if Docker container is running
if ! docker ps | grep -q redrat-proxy_web_1; then
    echo "⚠️  Warning: RedRat Docker container doesn't appear to be running"
    echo "   Please start it with: docker-compose up -d"
    echo ""
fi

# Run main menu
main