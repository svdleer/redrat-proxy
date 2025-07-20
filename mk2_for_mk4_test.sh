#!/bin/bash
# Test MK4 with MK2 protocol - this should work!
# Fine: 42 euros - MK2 protocol to the rescue!

set -e

REMOTE_HOST="access-engineering.nl"
REMOTE_PORT="65001"
REMOTE_USER="svdleer"

echo "================================================"
echo "Testing MK4 with MK2 Protocol (42 euro fix!)"
echo "================================================"

# Create test script using the updated library
cat > /tmp/mk2_for_mk4_test.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/tmp')

from redratlib_fixed import IRNetBox
import binascii
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_mk4_with_mk2_protocol():
    """Test MK4 device using MK2 protocol"""
    print("Testing MK4 device with MK2 protocol...")
    
    try:
        with IRNetBox("172.16.6.62", 10001) as ir:
            print(f"✓ Connected successfully!")
            
            # Get device info
            info = ir.get_device_info()
            print(f"✓ Device info: {info}")
            
            if info['model'] == 12:  # MK4
                print("✓ MK4 device detected - will use MK2 protocol")
            
            # Test power on
            ir.power_on()
            print("✓ Power on successful")
            
            # Real RedRat IR data (from a power button)
            real_ir_data = binascii.unhexlify(
                "000174F5FF600000000600000048024502222F704540D12116A464F" +
                "000000000000000000000000000000000000000000000"
            )
            
            print(f"Sending IR signal with MK2 protocol...")
            print(f"IR data: {len(real_ir_data)} bytes")
            
            # This should now use MK2 protocol for the MK4 device
            ir.irsend_raw(port=1, power=50, data=real_ir_data)
            print("✅ SUCCESS: IR signal sent using MK2 protocol on MK4 device!")
            
            return True
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mk4_with_mk2_protocol()
    if success:
        print("\n🎉 SUCCESS: MK2 protocol works on MK4! No 42 euro fine!")
        print("The RedRat proxy should now work correctly!")
    else:
        print("\n💸 Still having issues...")
        sys.exit(1)
EOF

echo "Copying updated library and test..."
scp -P $REMOTE_PORT app/services/redratlib.py $REMOTE_USER@$REMOTE_HOST:/tmp/redratlib_fixed.py
scp -P $REMOTE_PORT /tmp/mk2_for_mk4_test.py $REMOTE_USER@$REMOTE_HOST:/tmp/

echo "Running MK2-for-MK4 test..."
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "python3 /tmp/mk2_for_mk4_test.py"

echo "================================================"
echo "If successful, deploying to Docker container..."

# If test passes, deploy to the actual Docker container
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "
if [ \$? -eq 0 ]; then
    echo 'Test passed! Deploying to Docker...'
    CONTAINER_ID=\$(sudo docker ps | grep redrat | awk '{print \$1}' | head -1)
    if [ ! -z \"\$CONTAINER_ID\" ]; then
        echo \"Deploying to container: \$CONTAINER_ID\"
        sudo docker cp /tmp/redratlib_fixed.py \$CONTAINER_ID:/app/app/services/redratlib.py
        sudo docker exec \$CONTAINER_ID ls -la /app/app/services/redratlib.py
        echo '✅ Updated redratlib.py deployed to container!'
        echo '🎉 Your RedRat proxy should now work with IR transmission!'
    fi
fi
"

echo "================================================"
echo "Deployment completed!"
echo "The 42 euro fine should now be avoided! 💰➡️😅"
echo "================================================"
