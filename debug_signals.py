#!/usr/bin/env python3
"""
Quick Signal Debug Tool for RedRat Proxy Docker Container

This script helps debug signal transmission issues by:
1. Testing RedRat device connectivity
2. Testing command execution from the database
3. Showing detailed error messages
4. Testing the entire signal pipeline

Usage: docker exec -it redrat-proxy_web_1 python debug_signals.py
"""

import sys
import os
import json
import logging
import traceback
from datetime import datetime

# Set up Python path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

# Configure logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_header(title):
    """Print a nice header"""
    print("\n" + "="*60)
    print(f"🔧 {title}")
    print("="*60)

def test_imports():
    """Test if all required imports work"""
    print_header("TESTING IMPORTS")
    
    try:
        from app.mysql_db import db
        print("✅ Database import successful")
    except Exception as e:
        print(f"❌ Database import failed: {e}")
        return False
    
    try:
        from app.services.redrat_service import RedRatService, create_redrat_service
        print("✅ RedRat service import successful")
    except Exception as e:
        print(f"❌ RedRat service import failed: {e}")
        return False
    
    try:
        from app.services.redratlib import IRNetBox
        print("✅ RedRat library import successful")
    except Exception as e:
        print(f"❌ RedRat library import failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connectivity"""
    print_header("TESTING DATABASE CONNECTION")
    
    try:
        from app.mysql_db import db
        
        with db.get_connection() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM remotes")
                remote_count = cursor.fetchone()[0]
                print(f"✅ Database connected - {remote_count} remotes found")
                
                cursor.execute("SELECT COUNT(*) FROM command_templates")
                template_count = cursor.fetchone()[0]
                print(f"✅ Database connected - {template_count} command templates found")
                
                return True
            else:
                print("❌ Database connection failed")
                return False
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        traceback.print_exc()
        return False

def test_redrat_devices():
    """Test RedRat device connectivity"""
    print_header("TESTING REDRAT DEVICES")
    
    try:
        from app.services.redrat_device_service import RedRatDeviceService
        
        devices = RedRatDeviceService.get_all_devices()
        
        if not devices:
            print("❌ No RedRat devices found in database")
            return False
        
        print(f"📋 Found {len(devices)} RedRat devices:")
        
        for device in devices:
            print(f"\n🔌 Device: {device['name']}")
            print(f"   IP: {device['ip_address']}:{device['port']}")
            print(f"   Active: {device['is_active']}")
            print(f"   Status: {device.get('last_status', 'unknown')}")
            
            if device['is_active']:
                # Test connectivity
                try:
                    result = RedRatDeviceService.test_device_connection(device['id'])
                    if result['success']:
                        print(f"   ✅ Connection test: SUCCESS")
                        print(f"   📊 Response time: {result.get('response_time', 'N/A')}s")
                        device_info = result.get('device_info', {})
                        if device_info:
                            print(f"   🏷️  Model: {device_info.get('model', 'Unknown')}")
                            print(f"   🔌 Ports: {device_info.get('ports', 'Unknown')}")
                    else:
                        print(f"   ❌ Connection test: FAILED - {result['message']}")
                        
                except Exception as e:
                    print(f"   ❌ Connection test: ERROR - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ RedRat device test error: {e}")
        traceback.print_exc()
        return False

def test_command_templates():
    """Test command template retrieval"""
    print_header("TESTING COMMAND TEMPLATES")
    
    try:
        from app.mysql_db import db
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get a sample command template
            cursor.execute("""
                SELECT ct.id, ct.name, ct.template_data, r.name as remote_name
                FROM command_templates ct
                JOIN remotes r ON JSON_EXTRACT(ct.template_data, '$.remote_id') = r.id
                WHERE ct.template_data IS NOT NULL
                LIMIT 5
            """)
            
            templates = cursor.fetchall()
            
            if not templates:
                print("❌ No command templates found")
                return False
            
            print(f"📋 Found {len(templates)} sample command templates:")
            
            for template in templates:
                template_id, command_name, template_data, remote_name = template
                print(f"\n📱 Template: {command_name}")
                print(f"   Remote: {remote_name}")
                print(f"   ID: {template_id}")
                
                # Try to parse template data
                try:
                    if isinstance(template_data, bytes):
                        template_data = template_data.decode('utf-8')
                    
                    if isinstance(template_data, str):
                        parsed_data = json.loads(template_data)
                    else:
                        parsed_data = template_data
                    
                    print(f"   ✅ Template data parsed successfully")
                    
                    # Check for signal data
                    has_signal_data = False
                    signal_size = 0
                    
                    if 'SigData' in parsed_data:
                        has_signal_data = True
                        signal_size = len(str(parsed_data['SigData']))
                    elif 'signal_data' in parsed_data:
                        has_signal_data = True
                        signal_size = len(str(parsed_data['signal_data']))
                    elif 'IRPacket' in parsed_data and 'SigData' in parsed_data['IRPacket']:
                        has_signal_data = True
                        signal_size = len(str(parsed_data['IRPacket']['SigData']))
                    
                    if has_signal_data:
                        print(f"   ✅ Signal data found ({signal_size} chars)")
                    else:
                        print(f"   ❌ No signal data found")
                        print(f"   📋 Available keys: {list(parsed_data.keys())}")
                    
                except Exception as e:
                    print(f"   ❌ Template parsing failed: {e}")
            
            return True
            
    except Exception as e:
        print(f"❌ Command template test error: {e}")
        traceback.print_exc()
        return False

def test_signal_execution():
    """Test actual signal execution"""
    print_header("TESTING SIGNAL EXECUTION")
    
    try:
        from app.mysql_db import db
        from app.services.redrat_service import RedRatService
        from app.services.redrat_device_service import RedRatDeviceService
        
        # Get first active RedRat device
        devices = RedRatDeviceService.get_all_devices()
        active_devices = [d for d in devices if d.get('is_active', False)]
        
        if not active_devices:
            print("❌ No active RedRat devices found")
            return False
        
        device = active_devices[0]
        print(f"🔌 Using RedRat device: {device['name']} ({device['ip_address']}:{device['port']})")
        
        # Get a sample command
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ct.name, r.id as remote_id, r.name as remote_name
                FROM command_templates ct
                JOIN remotes r ON JSON_EXTRACT(ct.template_data, '$.remote_id') = r.id
                WHERE ct.template_data IS NOT NULL
                LIMIT 1
            """)
            
            command_info = cursor.fetchone()
            
        if not command_info:
            print("❌ No test command available")
            return False
        
        command_name, remote_id, remote_name = command_info
        print(f"📱 Testing command: {command_name} on {remote_name}")
        
        # Create RedRat service
        redrat_service = RedRatService(device['ip_address'], device['port'])
        
        # Test device validation first
        print("🔍 Testing device validation...")
        validation_result = redrat_service.validate_device_and_port(1)
        
        if validation_result['success']:
            print("✅ Device validation successful")
        else:
            print(f"❌ Device validation failed: {validation_result['error']}")
            return False
        
        # Test command execution
        print("📡 Testing command execution...")
        result = redrat_service.send_command(
            command_id=999999,  # Fake ID for testing
            remote_id=remote_id,
            command_name=command_name,
            ir_port=1,
            power=50
        )
        
        if result['success']:
            print("✅ Signal execution successful!")
            print(f"   📊 Executed at: {result.get('executed_at', 'N/A')}")
        else:
            print(f"❌ Signal execution failed: {result['message']}")
            if result.get('error_details'):
                print(f"   🔍 Details: {result['error_details']}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Signal execution test error: {e}")
        traceback.print_exc()
        return False

def main():
    """Main debugging function"""
    print("🐳 RedRat Proxy Signal Debug Tool")
    print(f"⏰ Started at: {datetime.now()}")
    
    results = {
        'imports': False,
        'database': False,
        'devices': False,
        'templates': False,
        'execution': False
    }
    
    # Run all tests
    results['imports'] = test_imports()
    if results['imports']:
        results['database'] = test_database_connection()
        if results['database']:
            results['devices'] = test_redrat_devices()
            results['templates'] = test_command_templates()
            if results['devices'] and results['templates']:
                results['execution'] = test_signal_execution()
    
    # Summary
    print_header("SUMMARY")
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test.upper()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED - Signal system is working!")
    else:
        print("\n⚠️  SOME TESTS FAILED - Check the errors above")
        
        # Provide troubleshooting tips
        print("\n🔧 TROUBLESHOOTING TIPS:")
        
        if not results['imports']:
            print("- Check if all Python dependencies are installed")
            print("- Verify PYTHONPATH is set correctly")
        
        if not results['database']:
            print("- Check database connection settings in .env file")
            print("- Verify MySQL is running and accessible")
            print("- Check database credentials")
        
        if not results['devices']:
            print("- Add RedRat devices via the admin interface")
            print("- Check RedRat device IP addresses and ports")
            print("- Verify network connectivity to RedRat devices")
        
        if not results['templates']:
            print("- Import command templates via the interface")
            print("- Check if templates have valid signal data")
        
        if not results['execution']:
            print("- Check RedRat device network connectivity")
            print("- Verify IR signal data format")
            print("- Check for protocol compatibility issues")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Debugging interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)