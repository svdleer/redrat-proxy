#!/usr/bin/env python3
"""
Test RedRat device on remote host at 172.16.6.62
This tests the merged stb-tester library with the remote RedRat device
"""

import sys
import os
import logging
import binascii

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_remote_redrat():
    """Test the remote RedRat device at 172.16.6.62"""
    redrat_ip = "172.16.6.62"
    redrat_port = 10001
    
    logger.info(f"Testing RedRat device at {redrat_ip}:{redrat_port}")
    
    try:
        # Import the merged library
        from services.redratlib import IRNetBox
        
        # Test connection and basic functionality
        logger.info("Attempting to connect to RedRat device...")
        
        with IRNetBox(redrat_ip, redrat_port) as ir:
            logger.info("✓ Successfully connected to RedRat device")
            
            # Get device information
            device_info = ir.get_device_info()
            logger.info(f"Device info: {device_info}")
            
            # Test basic commands
            logger.info("Testing power on command...")
            ir.power_on()
            logger.info("✓ Power on successful")
            
            logger.info("Testing indicators on...")
            ir.indicators_on()
            logger.info("✓ Indicators on successful")
            
            # Test IR transmission with a simple pattern
            logger.info("Testing IR transmission...")
            
            # Simple NEC-style IR pattern for testing
            test_pattern = [
                9000, -4500,     # Lead-in
                560, -560,       # Bit 0
                560, -1690,      # Bit 1
                560, -1690,      # Bit 1
                560, -560,       # Bit 0
                560, -39000      # End gap
            ]
            
            # Convert pattern to bytes (this is a simplified conversion)
            # In a real scenario, this would come from the database
            ir_data = bytearray()
            for value in test_pattern:
                if value > 0:
                    ir_data.extend(value.to_bytes(2, 'big'))
                else:
                    ir_data.extend((-value | 0x8000).to_bytes(2, 'big'))
            
            logger.info(f"Sending IR pattern with {len(test_pattern)} elements")
            logger.info(f"IR data length: {len(ir_data)} bytes")
            
            # Send IR signal to port 1 with 50% power
            ir.irsend_raw(port=1, power=50, data=bytes(ir_data))
            logger.info("✓ IR transmission completed successfully!")
            
            logger.info("Testing indicators off...")
            ir.indicators_off()
            logger.info("✓ Indicators off successful")
            
        logger.info("✓ All tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        logger.exception("Full error details:")
        return False

def main():
    print("RedRat Remote Device Test")
    print("=" * 50)
    print("Testing device at 172.16.6.62:10001")
    print()
    
    success = test_remote_redrat()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ SUCCESS: RedRat device is working correctly!")
        print("The merged stb-tester library is functioning properly.")
    else:
        print("✗ FAILURE: RedRat device test failed")
        print("Check the logs above for error details.")
    
    print("\nNext steps:")
    if success:
        print("- Deploy the updated library to production")
        print("- Test with actual remote control commands from database")
    else:
        print("- Check network connectivity to 172.16.6.62")
        print("- Verify RedRat device is powered on and responding")
        print("- Compare with official RedRat tool behavior")

if __name__ == "__main__":
    main()
