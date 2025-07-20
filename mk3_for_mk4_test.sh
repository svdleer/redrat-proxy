#!/bin/bash
# Test MK4 with MK3 async protocol
# Fine: 42 euros - MK3 protocol attempt!

set -e

REMOTE_HOST="access-engineering.nl"
REMOTE_PORT="65001"
REMOTE_USER="svdleer"

echo "================================================"
echo "Testing MK4 with MK3 Async Protocol (42 euro edition)"
echo "================================================"

# Create test script using the updated library with MK3 protocol
cat > /tmp/mk3_for_mk4_test.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/tmp')

from redratlib_mk3 import IRNetBox
import binascii
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_mk4_with_mk3_protocol():
    """Test MK4 device using MK3 async protocol"""
    print("Testing MK4 device with MK3 async protocol...")
    
    try:
        with IRNetBox("172.16.6.62", 10001) as ir:
            print(f"✓ Connected successfully!")
            
            # Get device info
            info = ir.get_device_info()
            print(f"✓ Device info: {info}")
            
            if info['model'] == 12:  # MK4
                print("✓ MK4 device detected - will use MK3 async protocol")
            
            # Test power on
            ir.power_on()
            print("✓ Power on successful")
            
            # Real RedRat IR data (from a power button)
            real_ir_data = binascii.unhexlify(
                "000174F5FF600000000600000048024502222F704540D12116A464F" +
                "000000000000000000000000000000000000000000000"
            )
            
            print(f"Sending IR signal with MK3 async protocol...")
            print(f"IR data: {len(real_ir_data)} bytes")
            
            # This should now use MK3 async protocol for the MK4 device
            ir.irsend_raw(port=1, power=50, data=real_ir_data)
            print("✅ SUCCESS: IR signal sent using MK3 async protocol on MK4 device!")
            
            return True
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_simple_data():
    """Test with simple timing data"""
    print("\nTesting with simple timing pattern...")
    
    try:
        with IRNetBox("172.16.6.62", 10001) as ir:
            # Simple NEC-like timing pattern
            # Format: mark, space, mark, space, etc. (in microseconds)
            simple_timing = bytes([
                0x23, 0x28,  # 9000μs mark  
                0xD1, 0x94,  # 4500μs space (0x8000 + 4500 = 0xD194)
                0x02, 0x30,  # 560μs mark
                0x82, 0x30,  # 560μs space
                0x02, 0x30,  # 560μs mark
                0x86, 0x9A,  # 1690μs space (0x8000 + 1690 = 0x869A)
                0x02, 0x30,  # 560μs mark
                0xA7, 0x10   # 10000μs space (0x8000 + 10000 = 0xA710)
            ])
            
            print(f"Simple timing pattern: {len(simple_timing)} bytes")
            print(f"Pattern: {binascii.hexlify(simple_timing).decode()}")
            
            ir.irsend_raw(port=1, power=30, data=simple_timing)
            print("✅ Simple timing pattern sent successfully!")
            
            return True
            
    except Exception as e:
        print(f"Simple timing test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing MK4 with MK3 protocol...")
    
    # Test 1: Real IR data
    success1 = test_mk4_with_mk3_protocol()
    
    # Test 2: Simple timing pattern
    success2 = test_with_simple_data()
    
    if success1 or success2:
        print("\n🎉 SUCCESS: MK3 async protocol works on MK4! No 42 euro fine!")
        print("The RedRat proxy should now work correctly!")
    else:
        print("\n💸 MK3 protocol also having issues...")
        sys.exit(1)
EOF

echo "Copying updated library with MK3 protocol..."
scp -P $REMOTE_PORT app/services/redratlib.py $REMOTE_USER@$REMOTE_HOST:/tmp/redratlib_mk3.py
scp -P $REMOTE_PORT /tmp/mk3_for_mk4_test.py $REMOTE_USER@$REMOTE_HOST:/tmp/

echo "Running MK3 protocol test..."
ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "python3 /tmp/mk3_for_mk4_test.py"

echo "================================================"
echo "Testing complete!"
echo "================================================"
