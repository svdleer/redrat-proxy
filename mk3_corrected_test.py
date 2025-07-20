#!/usr/bin/env python3
"""
Test MK3 protocol with corrected endianness and IR format
"""

import sys
import os
sys.path.append('/tmp')

from redratlib_mk3 import IRNetBox
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('mk3_corrected_test')

def test_corrected_mk3():
    """Test MK3 with corrected format"""
    
    # Simple IR pattern - basic NEC protocol start
    # NEC format: 9000us burst, 4500us space, then data bits
    simple_ir_pattern = bytearray([
        # This should be interpreted as timing values in microseconds
        0x28, 0x23,  # 9000us (0x2328 = 9000)
        0x94, 0xd1,  # 4500us (0xd194 = ~4500 in some encoding)
        0x02, 0x30,  # 560us burst
        0x82, 0x30,  # 560us space
        0x02, 0x30,  # 560us burst  
        0x86, 0x9a,  # 1690us space (logical 1)
        0x02, 0x30,  # 560us burst
        0xa7, 0x10   # End gap
    ])
    
    print("Testing MK3 protocol with corrected endianness...")
    print(f"IR pattern: {simple_ir_pattern.hex()}")
    print(f"Pattern length: {len(simple_ir_pattern)} bytes")
    
    try:
        with IRNetBox('172.16.6.62', 10001) as ir:
            print(f"✓ Connected successfully!")
            print(f"✓ Device info: {{'model': {ir.irnetbox_model}, 'ports': {ir.ports}}}")
            
            if ir.irnetbox_model == 12:  # MK4
                print("✓ MK4 device detected - will use corrected MK3 async protocol")
            
            print("Sending IR signal with corrected MK3 format...")
            ir.irsend_raw(port=1, power=25, data=bytes(simple_ir_pattern))
            print("✓ IR signal sent successfully!")
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        logger.exception("Full error details:")

if __name__ == "__main__":
    test_corrected_mk3()
