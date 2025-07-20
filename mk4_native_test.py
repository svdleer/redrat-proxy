#!/usr/bin/env python3
"""
Test MK4 with native MK4 protocol (not forced MK3)
"""

import sys
import os
sys.path.append('/tmp')

from redratlib_mk4_native import IRNetBox
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('mk4_native_test')

def test_mk4_native_protocol():
    """Test MK4 with its native protocol"""
    
    # Simple IR pattern for testing
    simple_ir_pattern = bytearray([
        0x28, 0x23,  # 9000us 
        0x94, 0x11,  # 4500us  
        0x30, 0x02,  # 560us
        0x30, 0x02,  # 560us
    ])
    
    print("Testing MK4 with NATIVE MK4 protocol...")
    print(f"IR pattern: {simple_ir_pattern.hex()}")
    print(f"Pattern length: {len(simple_ir_pattern)} bytes")
    
    try:
        with IRNetBox('172.16.6.62', 10001) as ir:
            print(f"✓ Connected successfully!")
            print(f"✓ Device model: {ir.irnetbox_model} (MK4 = 12)")
            
            if ir.irnetbox_model == 12:  # MK4
                print("✓ MK4 device detected - using NATIVE MK4 protocol")
            
            # Test different power levels
            power_levels = [15, 25, 50, 75, 100]
            
            for power in power_levels:
                print(f"\nTesting power level: {power}")
                try:
                    ir.irsend_raw(port=1, power=power, data=bytes(simple_ir_pattern))
                    print(f"✅ SUCCESS with power {power}! Native MK4 protocol works!")
                    break
                except Exception as e:
                    if "error code: 51" in str(e):
                        print(f"❌ Power {power}: NACK error 51")
                    elif "timed out" in str(e):
                        print(f"⏱️  Power {power}: Timeout")
                    else:
                        print(f"❓ Power {power}: {e}")
            else:
                print("💸 All power levels failed with native MK4 protocol")
                
    except Exception as e:
        print(f"✗ Test failed: {e}")
        logger.exception("Full error details:")

if __name__ == "__main__":
    test_mk4_native_protocol()
