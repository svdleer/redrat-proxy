#!/usr/bin/env python3
"""
Direct test of ASYNC protocol transmission
"""

import sys
import os
import time
import base64

# Add the app directory to the Python path
sys.path.insert(0, '/home/svdleer/redrat-proxy')

def test_direct_async_transmission():
    """Test direct ASYNC transmission with working signal data"""
    
    print("🎯 DIRECT ASYNC PROTOCOL TEST")
    print("=" * 50)
    
    try:
        # Import required modules
        from app.services.irnetbox_lib_new import IRNetBox, IRSignal, OutputConfig, PowerLevel
        
        print("✅ IRNetBox library imported successfully")
        
        # Test signal data from our XML (base64 decoded)
        test_signal_b64 = "AQICAgICAgICAgICAgICAgICAgICAgICAgICAgICAwICAgICAgICAgICAgICAgICAgICAgICAgICAgIEAgICAgMCAwIDAgMCAwIDAgMCAwIDAgMCB/"
        
        # Fix base64 padding if needed
        missing_padding = len(test_signal_b64) % 4
        if missing_padding:
            test_signal_b64 += '=' * (4 - missing_padding)
            
        signal_data = base64.b64decode(test_signal_b64)
        
        print(f"📊 Signal data: {len(signal_data)} bytes")
        print(f"   Hex: {signal_data.hex()}")
        
        # Create IRSignal object
        test_signal = IRSignal(
            name="POWER",
            uid="test_power",
            modulation_freq=38238,
            lengths=[0.56, 0.56, 0.56, 1.68],  # from XML
            sig_data=signal_data,
            no_repeats=1,
            intra_sig_pause=0.0
        )
        
        print(f"✅ IRSignal created: {test_signal.name}")
        
        # Connect to RedRat device
        redrat = IRNetBox()
        print("🔌 Connecting to RedRat device...")
        
        if redrat.connect("172.16.6.62"):
            print("✅ Connected to RedRat device")
            
            print("🚀 Transmitting signal with ASYNC protocol...")
            
            # Create output configuration for port 9
            output_config = OutputConfig(
                port=9,
                power_level=PowerLevel.HIGH
            )
            
            # Transmit using ASYNC protocol  
            result = redrat.send_signal_async(test_signal, [output_config], sequence_number=12345)
            
            if result:
                print("✅ ASYNC transmission successful!")
                print("   Protocol: 0x30 (MK3/4 ASYNC)")
                print("   This should generate the correct ASYNC packet!")
                print(f"   Response: {result}")
            else:
                print("❌ ASYNC transmission failed")
                
            redrat.disconnect()
            print("🔌 Disconnected from RedRat device")
            
        else:
            print("❌ Connection to RedRat device failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_async_transmission()