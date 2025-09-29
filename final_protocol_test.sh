vi #!/usr/bin/env bash
"""
Final test of the fixed RedRat protocol with proper API endpoint
"""

echo "🧪 Final Protocol Test - MK3/4 ASYNC Format (0x30)"
echo "=================================================="
echo ""

# Create capture directory
mkdir -p ./captures

# Generate timestamp for unique filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CAPTURE_FILE="./captures/redrat_proxy_final_${TIMESTAMP}.pcap"

echo "📡 Starting ERSPAN capture..."
echo "Capture file: $CAPTURE_FILE"

# Start tcpdump in background to capture ERSPAN traffic
sudo tcpdump -i any host 172.16.6.101 and proto 47 -w "$CAPTURE_FILE" &
TCPDUMP_PID=$!

echo "Process ID: $TCPDUMP_PID"
echo "⏳ Waiting 3 seconds for tcpdump to start..."
sleep 3

echo ""
echo "🎯 Sending POWER command to Humax remote (ID: 12) via correct API endpoint..."

# Send a POWER command using the correct API endpoint
curl -X POST http://127.0.0.1:5000/api/remotes/12/commands/POWER/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: rr_X_Tk5fZC3h8_oUln1IZeGQT07-5QxqJrKLeLdy5uTwE" \
  -d '{}' | python3 -m json.tool

echo ""
echo "⏳ Waiting 5 seconds for IR transmission..."
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
    
    echo ""
    echo "🔬 Running detailed signal comparison..."
    
    # Update signal comparator with new file
    sed -i "s|proxy_pcap = \".*\"|proxy_pcap = \"$CAPTURE_FILE\"|" signal_comparator.py
    
    # Run the comparison
    source /home/svdleer/scripts/python/venv/bin/activate && python3 signal_comparator.py
    
else
    echo "❌ Capture file not created!"
fi

echo ""
echo "🎯 EXPECTED RESULTS AFTER FIX:"
echo "==============================="
echo "✅ Proxy should now use message type 0x30 (MK3/4 ASYNC) instead of 0x12"  
echo "✅ Signal header should start with 'ae540000' (matching original)"
echo "✅ Signal data should be similar to original working capture"
echo "✅ IR signals should work on the actual Humax device"