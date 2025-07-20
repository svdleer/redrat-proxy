#!/usr/bin/env python3
"""
IR Transmission Diagnostic Script
Tests basic IR transmission functionality to diagnose why IR is not working
"""

import sys
import os
import logging
import json
import binascii
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from services.redratlib import IRNetBox
    from services.redrat_service import RedRatService
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

def test_direct_redratlib(host, port=10001):
    """Test IR transmission using redratlib directly"""
    logger.info("=== Testing Direct RedRat Library ===")
    
    try:
        # Connect to RedRat device
        ir = IRNetBox(host, port)
        logger.info(f"Connected to RedRat at {host}:{port}")
        
        # Get device info
        try:
            info = ir.get_device_info()
            logger.info(f"Device info: {info}")
        except Exception as e:
            logger.warning(f"Could not get device info: {e}")
        
        # Test simple IR transmission
        # Using a basic power signal pattern (simplified)
        test_pattern = [
            9000, -4500,  # Lead-in
            560, -560, 560, -1690, 560, -1690, 560, -560,  # Some data bits
            560, -1690, 560, -1690, 560, -560, 560, -560,
            560, -560, 560, -560, 560, -560, 560, -560,
            560, -560, 560, -1690, 560, -1690, 560, -1690,
            560, -39000  # End gap
        ]
        
        logger.info("Testing IR transmission...")
        logger.info(f"Pattern length: {len(test_pattern)} elements")
        
        # Test on IR port 1 with medium power (50)
        ir_port = 1
        power = 50
        
        logger.info(f"Sending IR signal to port {ir_port} with power {power}")
        
        # Send the signal
        result = ir.irsend_raw(ir_port, power, test_pattern)
        logger.info(f"IR send result: {result}")
        
        # Close connection
        ir.close()
        return True
        
    except Exception as e:
        logger.error(f"Direct redratlib test failed: {e}")
        return False

def test_redrat_service(host, port=10001):
    """Test IR transmission using RedRatService"""
    logger.info("=== Testing RedRat Service ===")
    
    try:
        service = RedRatService(host, port)
        
        # Test a simple command execution
        test_ir_data = [
            9000, -4500,
            560, -560, 560, -1690, 560, -1690, 560, -560,
            560, -1690, 560, -1690, 560, -560, 560, -560,
            560, -560, 560, -560, 560, -560, 560, -560,
            560, -560, 560, -1690, 560, -1690, 560, -1690,
            560, -39000
        ]
        
        logger.info("Testing service IR execution...")
        result = service._execute_ir_command(
            ir_data=test_ir_data,
            ir_port=1,
            power=50,
            no_repeats=1,
            intra_sig_pause=100
        )
        
        logger.info(f"Service execution result: {result}")
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"RedRat service test failed: {e}")
        return False

def test_database_command():
    """Test sending a command from the database"""
    logger.info("=== Testing Database Command ===")
    
    try:
        # Import database modules
        from mysql_db import db
        from services.redrat_service import RedRatService
        
        # Get the first available command from database
        with db.get_connection() as conn:
            if not conn:
                logger.error("No database connection")
                return False
                
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT ct.*, r.name as remote_name 
                FROM command_templates ct
                JOIN remotes r ON ct.remote_id = r.id
                WHERE ct.ir_data IS NOT NULL 
                AND ct.ir_data != ''
                LIMIT 1
            """)
            
            command = cursor.fetchone()
            
            if not command:
                logger.error("No commands found in database")
                return False
                
            logger.info(f"Testing command: {command['command_name']} from remote: {command['remote_name']}")
            
            # Get RedRat device info
            cursor.execute("SELECT * FROM redrat_devices WHERE is_active = 1 LIMIT 1")
            device = cursor.fetchone()
            
            if not device:
                logger.error("No active RedRat devices found")
                return False
                
            logger.info(f"Using device: {device['name']} at {device['ip_address']}")
            
            # Create service and send command
            service = RedRatService(device['ip_address'], device.get('port', 10001))
            
            result = service.send_command(
                command_id=command['id'],
                remote_id=command['remote_id'],
                command_name=command['command_name'],
                device_id=device['id'],
                ir_port=command.get('ir_port', 1),
                power=command.get('power', 50)
            )
            
            logger.info(f"Database command result: {result}")
            return result.get('success', False)
            
    except Exception as e:
        logger.error(f"Database command test failed: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("RedRat IR Transmission Diagnostic")
    print("=" * 50)
    
    # Check if host provided
    if len(sys.argv) < 2:
        print("Usage: python test_ir_transmission.py <redrat_host> [port]")
        print("Example: python test_ir_transmission.py 192.168.1.100")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 10001
    
    logger.info(f"Starting diagnostic for {host}:{port}")
    
    # Test results
    results = {}
    
    # Test 1: Direct redratlib
    results['direct_redratlib'] = test_direct_redratlib(host, port)
    
    # Test 2: RedRat service
    results['redrat_service'] = test_redrat_service(host, port)
    
    # Test 3: Database command (if available)
    results['database_command'] = test_database_command()
    
    # Summary
    print("\n" + "=" * 50)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    if any(results.values()):
        print("\n✓ At least one test passed - IR hardware seems functional")
    else:
        print("\n✗ All tests failed - check hardware connection and setup")
    
    print("\nNext steps:")
    if not results['direct_redratlib']:
        print("- Check RedRat device IP address and network connectivity")
        print("- Verify RedRat device is powered on and accessible")
        print("- Test with official RedRat tool to confirm device works")
    elif not results['redrat_service']:
        print("- Issue with RedRatService wrapper - check service implementation")
    elif not results['database_command']:
        print("- Issue with database integration or command data")
    else:
        print("- All tests passed! IR transmission should be working")

if __name__ == "__main__":
    main()
