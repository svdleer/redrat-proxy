#!/usr/bin/env python3
"""
Test actual database commands on remote RedRat device
Tests the complete flow from database to IR transmission
"""

import sys
import os
import logging

# Add the app directory to Python path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_ir_command():
    """Test sending an actual command from the database to the remote RedRat"""
    logger.info("Testing database IR command transmission")
    
    try:
        # Import required modules
        from mysql_db import db
        from services.redrat_service import RedRatService
        
        # Connect to database and get a test command
        with db.get_connection() as conn:
            if not conn:
                logger.error("Failed to connect to database")
                return False
                
            cursor = conn.cursor(dictionary=True)
            
            # Get the first available command with IR data
            cursor.execute("""
                SELECT ct.*, r.name as remote_name 
                FROM command_templates ct
                JOIN remotes r ON ct.remote_id = r.id
                WHERE ct.ir_data IS NOT NULL 
                AND ct.ir_data != ''
                AND ct.command_name LIKE '%POWER%'
                LIMIT 1
            """)
            
            command = cursor.fetchone()
            
            if not command:
                logger.warning("No POWER command found, trying any command...")
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
                logger.error("No commands with IR data found in database")
                return False
                
            logger.info(f"Testing command: '{command['command_name']}' from remote: '{command['remote_name']}'")
            
            # Create RedRat service pointing to remote device
            service = RedRatService("172.16.6.62", 10001)
            
            # Send the command
            result = service.send_command(
                command_id=command['id'],
                remote_id=command['remote_id'], 
                command_name=command['command_name'],
                device_id=1,  # Assume device ID 1
                ir_port=command.get('ir_port', 1),
                power=command.get('power', 50)
            )
            
            logger.info(f"Command result: {result}")
            
            if result.get('success'):
                logger.info("✓ Database command sent successfully!")
                return True
            else:
                logger.error(f"✗ Command failed: {result.get('message', 'Unknown error')}")
                return False
                
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        logger.exception("Full error details:")
        return False

def test_specific_power_command():
    """Test a specific POWER command if available"""
    logger.info("Testing specific POWER command")
    
    try:
        from mysql_db import db
        from services.redrat_service import RedRatService
        
        with db.get_connection() as conn:
            if not conn:
                logger.error("Failed to connect to database")
                return False
                
            cursor = conn.cursor(dictionary=True)
            
            # Look for POWER command specifically
            cursor.execute("""
                SELECT ct.*, r.name as remote_name 
                FROM command_templates ct
                JOIN remotes r ON ct.remote_id = r.id
                WHERE ct.ir_data IS NOT NULL 
                AND ct.ir_data != ''
                AND (ct.command_name = 'POWER' OR ct.command_name LIKE 'Power%')
                LIMIT 1
            """)
            
            command = cursor.fetchone()
            
            if not command:
                logger.warning("No POWER command found in database")
                return False
                
            logger.info(f"Found POWER command: '{command['command_name']}' from remote: '{command['remote_name']}'")
            logger.info(f"IR data length: {len(command['ir_data']) if command['ir_data'] else 0} bytes")
            
            # Create service for remote RedRat
            service = RedRatService("172.16.6.62", 10001)
            
            # Send the POWER command
            result = service.send_command(
                command_id=command['id'],
                remote_id=command['remote_id'],
                command_name=command['command_name'], 
                device_id=1,
                ir_port=command.get('ir_port', 1),
                power=command.get('power', 50)
            )
            
            logger.info(f"POWER command result: {result}")
            return result.get('success', False)
            
    except Exception as e:
        logger.error(f"POWER command test failed: {e}")
        return False

def main():
    print("RedRat Database Command Test")
    print("=" * 50)
    print("Testing actual database commands on remote RedRat (172.16.6.62)")
    print()
    
    # Test results
    results = {}
    
    # Test 1: Any available command
    print("Test 1: Database IR Command...")
    results['database_command'] = test_database_ir_command()
    
    # Test 2: Specific POWER command
    print("\nTest 2: Specific POWER Command...")
    results['power_command'] = test_specific_power_command()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    
    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    if any(results.values()):
        print("\n✓ SUCCESS: At least one database command worked!")
        print("The IR transmission functionality is working.")
        print("\nYour RedRat proxy should now be functional.")
    else:
        print("\n✗ FAILURE: No database commands worked")
        print("Check database connectivity and RedRat device status.")
    
    print(f"\nRemote RedRat device: 172.16.6.62:10001")
    print("Remember: 35 euro fine for issues - let's make sure this works! 😅")

if __name__ == "__main__":
    main()
