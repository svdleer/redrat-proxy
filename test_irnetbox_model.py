#!/usr/bin/env python3
"""
Test the fixed IRNetBox class with irnetbox_model attribute
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, '/home/svdleer/redrat-proxy')

def test_irnetbox_model():
    """Test that the IRNetBox class now has the irnetbox_model attribute"""
    
    print("🔧 TESTING FIXED IRNETBOX CLASS")
    print("=" * 50)
    
    try:
        from app.services.irnetbox_lib_new import IRNetBox
        
        # Create IRNetBox instance
        ir = IRNetBox("172.16.6.62")
        
        print("✅ IRNetBox imported successfully")
        print(f"   Initial irnetbox_model: {ir.irnetbox_model}")
        print(f"   Initial device_type: {ir.device_type}")
        print(f"   Initial ports: {ir.ports}")
        
        # Test connection
        if ir.connect():
            print("✅ Connected successfully")
            print(f"   Device Type: {ir.device_type}")
            print(f"   Device Model (numeric): {ir.irnetbox_model}")
            print(f"   Firmware: {ir.firmware_version}")
            print(f"   Serial: {ir.serial_number}")
            print(f"   Ports: {ir.ports}")
            
            device_info = ir.get_device_info()
            print("\n📊 Device Info:")
            for key, value in device_info.items():
                print(f"   {key}: {value}")
            
            ir.disconnect()
            print("✅ Disconnected successfully")
        else:
            print("❌ Connection failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_irnetbox_model()