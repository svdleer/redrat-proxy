#!/usr/bin/env python3
"""
Direct test of the working library to send a POWER signal
This bypasses the web service completely to test the library directly
"""

import sys
import os
sys.path.append('/home/svdleer/redrat-proxy')

from app.services.irnetbox_lib import IRNetBox, IRSignal, PowerLevel

# Signal data from the database/logs (starting with 00017343ff63...)
signal_hex = "00017343ff63000000180000008202455c236e04400d6504ef0b1400ec00df00e70095028c0006010c00a500ca00b600c600940234000a170a161616161616160c1616160a160c161616161616160c1616161617027f"

print("🧪 Testing Working Library Directly")
print("==================================")
print(f"Signal hex length: {len(signal_hex)} chars ({len(signal_hex)//2} bytes)")
print(f"Signal starts with: {signal_hex[:32]}")

try:
    # Convert hex to bytes
    sig_data = bytes.fromhex(signal_hex)
    print(f"✅ Converted hex to bytes: {len(sig_data)} bytes")
    print(f"Signal bytes start with: {sig_data[:16].hex()}")
    
    # Create IRSignal
    ir_signal = IRSignal(
        name="POWER_DIRECT_TEST",
        uid="power_direct_test",
        modulation_freq=38238,
        lengths=[],
        sig_data=sig_data,
        no_repeats=1,
        intra_sig_pause=0.0,
        toggle_data=None
    )
    print(f"✅ Created IRSignal: {ir_signal.name}")
    
    # Connect to RedRat device
    irnetbox = IRNetBox("172.16.6.62")
    print("🔌 Connecting to RedRat device...")
    
    if irnetbox.connect("172.16.6.62"):
        print("✅ Connected successfully")
        
        # Send signal
        print("📡 Sending IR signal...")
        result = irnetbox.send_signal_robust(
            signal=ir_signal,
            port=1,
            power_level=PowerLevel.MEDIUM,
            max_retries=1
        )
        
        print(f"📊 Send result: {result}")
        
        if result['success']:
            print("✅ Signal sent successfully!")
        else:
            print(f"❌ Signal failed: {result.get('error', 'Unknown error')}")
        
        irnetbox.disconnect()
        print("🔌 Disconnected")
        
    else:
        print("❌ Failed to connect to RedRat device")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()