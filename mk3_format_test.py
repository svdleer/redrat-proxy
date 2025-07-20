#!/usr/bin/env python3
"""
Test different IR data formats for MK3 protocol to resolve error 51
"""

import sys
import os
sys.path.append('/tmp')

from redratlib_mk3_corrected import IRNetBox
import struct
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('mk3_format_test')

def test_different_ir_formats():
    """Test various IR data formats to find what works"""
    
    # Different IR data format attempts
    test_formats = [
        {
            'name': 'Simple timing pairs (microseconds)',
            'description': 'Raw timing values as 16-bit little-endian',
            'data': struct.pack('<HHHHHHHH',
                9000, 4500,  # Header: 9ms burst, 4.5ms space
                560, 560,    # Bit timing
                560, 1690,   # Different bit timing  
                560, 40000   # Final burst + long gap
            )
        },
        {
            'name': 'NEC protocol format',
            'description': 'Standard NEC IR protocol timing',
            'data': struct.pack('<HHHH',
                9000, 4500,  # NEC header
                560, 1690    # Sample bit pattern
            )
        },
        {
            'name': 'Minimal test pattern',
            'description': 'Simplest possible IR pattern',
            'data': struct.pack('<HH', 1000, 1000)  # 1ms on, 1ms off
        },
        {
            'name': 'RedRat XML format simulation',
            'description': 'Simulate RedRat XML IR data format',
            # Try to match the RedRat XML format more closely
            'data': bytes([
                0x00, 0x01,  # Header or format indicator
                0x23, 0x28,  # 9000us (little-endian)
                0x94, 0x11,  # 4500us  
                0x30, 0x02,  # 560us
                0x30, 0x02,  # 560us
                0x9a, 0x06,  # 1690us
                0x30, 0x02,  # 560us
                0x10, 0x27   # End pattern
            ])
        }
    ]
    
    print("Testing different IR data formats for MK3 protocol...")
    
    try:
        with IRNetBox('172.16.6.62', 10001) as ir:
            print(f"✓ Connected to MK4 device (model: {ir.irnetbox_model})")
            
            for i, test_format in enumerate(test_formats, 1):
                print(f"\n=== Test {i}: {test_format['name']} ===")
                print(f"Description: {test_format['description']}")
                print(f"Data length: {len(test_format['data'])} bytes")
                print(f"Data hex: {test_format['data'].hex()}")
                
                try:
                    ir.irsend_raw(port=1, power=20, data=test_format['data'])
                    print("✅ SUCCESS! This format works!")
                    print(f"🎉 Found working format: {test_format['name']}")
                    break
                    
                except Exception as e:
                    if "error code: 51" in str(e):
                        print(f"❌ NACK error 51 - format rejected")
                    elif "timed out" in str(e):
                        print(f"⏱️  Timeout - might be processing")
                    else:
                        print(f"❓ Other error: {e}")
                        
        if i == len(test_formats):
            print(f"\n💸 All {len(test_formats)} formats failed - need more investigation")
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")

if __name__ == "__main__":
    test_different_ir_formats()
