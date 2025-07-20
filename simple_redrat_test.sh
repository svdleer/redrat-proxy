#!/bin/bash
# Simple RedRat test without Flask dependencies
# Fine: 42 euros - Keep it simple!

set -e

REMOTE_HOST="access-engineering.nl"
REMOTE_PORT="65001"
REMOTE_USER="svdleer"

echo "================================================"
echo "Simple RedRat Library Test (42 euro fine edition)"
echo "================================================"

# Create a minimal test script
cat > /tmp/simple_redrat_test.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/tmp')

from redratlib_merged import IRNetBox
import binascii
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_redrat():
    print("Testing RedRat device at 172.16.6.62...")
    
    try:
        with IRNetBox("172.16.6.62", 10001) as ir:
            print(f"✓ Connected successfully!")
            
            # Get device info
            info = ir.get_device_info()
            print(f"✓ Device info: {info}")
            
            # Test power on
            ir.power_on()
            print("✓ Power on successful")
            
            # Test indicators
            ir.indicators_on()
            print("✓ Indicators on successful")
            
            # Simple IR test with proper RedRat signal format
            # This is a basic NEC protocol pattern
            test_signal = bytes([
                0x00, 0x01, 0x74, 0xF5,  # Header
                0xFF, 0x60, 0x00, 0x00,  # More header
                0x00, 0x06, 0x00, 0x00,  # Length info
                0x00, 0x48, 0x02, 0x45,  # Timing data starts
                0x02, 0x22, 0xF7, 0x04,
                0x54, 0x0D, 0x12, 0x11,
                0x6A, 0x46, 0x4F
            ])
            
            print(f"Sending test IR signal ({len(test_signal)} bytes)...")
            ir.irsend_raw(port=1, power=50, data=test_signal)
            print("✓ IR signal sent successfully!")
            
            ir.indicators_off()
            print("✓ Test completed successfully!")
            return True
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_redrat()
    if success:
        print("\n🎉 SUCCESS: RedRat is working! No 42 euro fine!")
    else:
        print("\n💸 FAILURE: 42 euro fine incoming...")
        sys.exit(1)
EOF

# Copy files and run test
echo "Copying test files to remote server..."
scp -P $REMOTE_PORT /tmp/simple_redrat_test.py $REMOTE_USER@$REMOTE_HOST:/tmp/
scp -P $REMOTE_PORT app/services/redratlib.py $REMOTE_USER@$REMOTE_HOST:/tmp/redratlib_merged.py

echo "Running simple RedRat test..."
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "python3 /tmp/simple_redrat_test.py"

echo "================================================"
echo "Test completed!"
echo "================================================"
