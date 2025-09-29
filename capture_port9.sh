#!/usr/bin/env bash
"""
Port 9 IR Signal Capture
Captures IR signal transmission to port 9 for analysis
"""

echo "🎯 Port 9 IR Signal Capture"
echo "=========================="
echo ""

# Create capture directory
mkdir -p ./captures

# Generate timestamp for unique filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CAPTURE_FILE="./captures/port9_power_${TIMESTAMP}.pcap"

echo "📡 Starting ERSPAN capture for port 9 transmission..."
echo "Capture file: $CAPTURE_FILE"

# Start tcpdump in background to capture ERSPAN traffic
sudo tcpdump -i any host 172.16.6.101 and proto 47 -w "$CAPTURE_FILE" &
TCPDUMP_PID=$!

echo "Process ID: $TCPDUMP_PID"
echo "⏳ Waiting 3 seconds for tcpdump to start..."
sleep 3

echo ""
echo "🎯 Sending POWER command to Humax remote on port 9..."

# Send POWER command to port 9
curl -X POST http://172.16.6.101:5000/api/remotes/12/commands/POWER/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: rr_X_Tk5fZC3h8_oUln1IZeGQT07-5QxqJrKLeLdy5uTwE" \
  -d '{"ir_port": 9}' | python3 -m json.tool

echo ""
echo "⏳ Waiting 5 seconds for IR transmission completion..."
sleep 5

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
        
        # Update signal comparator with new port 9 capture
        sed -i "s|proxy_pcap = \".*\"|proxy_pcap = \"$CAPTURE_FILE\"|" signal_comparator.py
        
        # Run the comparison
        source /home/svdleer/scripts/python/venv/bin/activate && python3 signal_comparator.py
        
    else
        echo "❌ No packets captured!"
    fi
    
else
    echo "❌ Capture file not created!"
fi

echo ""
echo "🎯 PORT 9 ANALYSIS COMPLETE"
echo "==========================="
echo "Port 9 IR signal captured and analyzed"
echo "Check results above for signal details"