#!/usr/bin/env python3
"""
Test the new RedRat service by directly calling it to generate protocol traffic.
"""

import sys
import os
import time
sys.path.append('/home/svdleer/redrat-proxy')

# Set environment variables for the service
os.environ['REDRAT_HOST'] = '172.16.6.62'
os.environ['DATABASE_URL'] = 'mysql://redrat:password@172.16.6.107:3306/redrat_hub'

try:
    from app.services.redrat_service import create_redrat_service
    
    def test_new_service():
        """Test the new RedRat service"""
        print("🎯 Testing New RedRat Service")
        print("=" * 40)
        
        # Create service instance
        service = create_redrat_service('172.16.6.62')
        
        # Test connection
        print("📡 Testing connection...")
        conn_result = service.test_connection()
        if conn_result['success']:
            print(f"✅ Connection successful: {conn_result['message']}")
            print(f"Device info: {conn_result['device_info']}")
        else:
            print(f"❌ Connection failed: {conn_result['message']}")
            return False
        
        # Send a test command
        print("\n📤 Sending test command (POWER)...")
        cmd_result = service.send_command(
            command_id=999,
            remote_id=12,
            command_name='POWER',
            ir_port=9,
            power=75
        )
        
        if cmd_result['success']:
            print(f"✅ Command successful: {cmd_result['message']}")
            print(f"Executed at: {cmd_result['executed_at']}")
        else:
            print(f"❌ Command failed: {cmd_result['message']}")
            print(f"Error details: {cmd_result.get('error_details', 'None')}")
        
        return cmd_result['success']
    
    if __name__ == "__main__":
        success = test_new_service()
        print(f"\n{'🎉 SUCCESS!' if success else '❌ FAILED'}")
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the correct directory")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)