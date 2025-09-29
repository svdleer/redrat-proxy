#!/usr/bin/env bash
"""
Fresh Hub Signal Capture
Captures a new baseline signal from the original working hub system
"""

echo "🎯 Fresh Hub Signal Capture"
echo "==========================="  
echo "This will capture a new baseline signal from the original working hub"
echo ""

# Create capture directory
mkdir -p ./captures

# Generate timestamp for unique filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CAPTURE_FILE="./captures/hub_baseline_${TIMESTAMP}.pcap"

echo "📡 Starting ERSPAN capture for hub baseline..."
echo "Capture file: $CAPTURE_FILE"
echo ""
echo "🎮 INSTRUCTIONS:"
echo "1. Start capture (will run for 30 seconds)"
echo "2. Send a POWER command from the original working hub/system"
echo "3. Wait for capture to complete"
echo "4. Analyze the results"
echo ""

read -p "Press Enter to start capture..."

# Start tcpdump in background to capture ERSPAN traffic
sudo tcpdump -i any host 172.16.6.101 and proto 47 -w "$CAPTURE_FILE" &
TCPDUMP_PID=$!

echo "📡 Capture started (PID: $TCPDUMP_PID)"
echo ""
echo "🚨 NOW: Send POWER command from the ORIGINAL WORKING HUB/SYSTEM"
echo "   (You have 30 seconds)"
echo ""

# Countdown timer
for i in {30..1}; do
    echo -ne "\r⏱️  Time remaining: ${i} seconds   "
    sleep 1
done

echo ""
echo ""
echo "🛑 Stopping capture..."
sudo kill $TCPDUMP_PID
sleep 2

echo ""
echo "📊 Analyzing captured traffic..."

if [ -f "$CAPTURE_FILE" ]; then
    echo "✅ Capture file created: $(ls -lh $CAPTURE_FILE | awk '{print $5}')"
    
    # Quick analysis
    echo ""
    echo "🔍 Quick packet analysis:"
    echo "Total packets: $(sudo tcpdump -r $CAPTURE_FILE 2>/dev/null | wc -l)"
    echo "ERSPAN packets: $(sudo tcpdump -r $CAPTURE_FILE proto 47 2>/dev/null | wc -l)"
    
    if [ $(sudo tcpdump -r $CAPTURE_FILE 2>/dev/null | wc -l) -gt 0 ]; then
        echo ""
        echo "🔬 Running detailed signal analysis..."
        
        # Update signal comparator with new hub baseline
        sed -i "s|original_pcap = \".*\"|original_pcap = \"$CAPTURE_FILE\"|" signal_comparator.py
        
        # Run the comparison
        source /home/svdleer/scripts/python/venv/bin/activate && python3 signal_comparator.py
        
        echo ""
        echo "🔄 Running sync checker with new baseline..."
        python3 signal_sync_checker.py
        
    else
        echo "❌ No packets captured. Possible issues:"
        echo "   - No POWER command was sent"
        echo "   - Original system not sending to 172.16.6.101"
        echo "   - Wrong capture interface"
    fi
    
else
    echo "❌ Capture file not created!"
fi

echo ""
echo "🎯 NEXT STEPS:"
echo "=============="
echo "1. Compare the new hub baseline with proxy signals"
echo "2. Check if new baseline matches database better"
echo "3. Verify we're capturing the right command"
echo "4. Update proxy to use correct signal templates if needed"