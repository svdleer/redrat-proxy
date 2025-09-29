#!/usr/bin/env bash
"""
Test the fixed RedRat protocol
1. Start ERSPAN capture
2. Send a test signal via the proxy API  
3. Stop capture and analyze the results
"""

echo "🧪 Testing Fixed RedRat Protocol"
echo "================================="
echo "The fix changed from SYNC format (0x08) to ASYNC format (0x30)"
echo ""

# Create capture directory
mkdir -p ./captures

# Generate timestamp for unique filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CAPTURE_FILE="./captures/redrat_proxy_fixed_${TIMESTAMP}.pcap"

echo "📡 Starting ERSPAN capture..."
echo "Capture file: $CAPTURE_FILE"

# Start tcpdump in background to capture ERSPAN traffic
sudo tcpdump -i any host 172.16.6.101 and proto 47 -w "$CAPTURE_FILE" &
TCPDUMP_PID=$!

echo "Process ID: $TCPDUMP_PID"
echo "⏳ Waiting 3 seconds for tcpdump to start..."
sleep 3

echo ""
echo "🎯 Sending test IR signal via proxy API..."

# Send a test power command via the proxy API  
curl -X POST http://172.16.6.101:5000/api/irnetbox/command \
  -H "Content-Type: application/json" \
  -d '{
    "remote_name": "Humax", 
    "command": "POWER"
  }' \
  2>/dev/null | python3 -m json.tool

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
    echo "🔬 Now running detailed signal comparison..."
    
    # Update signal comparator with new file
    sed -i "s|proxy_pcap = \".*\"|proxy_pcap = \"$CAPTURE_FILE\"|" signal_comparator.py
    
    # Run the comparison
    source /home/svdleer/scripts/python/venv/bin/activate && python3 signal_comparator.py
    
else
    echo "❌ Capture file not created!"
fi

echo ""
echo "🎯 EXPECTED RESULTS:"
echo "================================="
echo "✅ Proxy should now use message type 0x30 (MK3/4 ASYNC)"  
echo "✅ Signal header should start with 'ae540000' (like original)"
echo "✅ IR signals should work on the actual device"