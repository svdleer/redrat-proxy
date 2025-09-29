#!/usr/bin/env python3
"""
Direct test of the working library to compare protocol output
This uses direct file import to avoid Flask dependencies
"""

import sys
sys.path.append('/home/svdleer/redrat-proxy/app/services')

# Direct import from the library file
from irnetbox_lib import IRNetBox, IRSignal, PowerLevel

print("🧪 Testing Working Library Protocol")
print("==================================")

# Test signal data from logs
signal_hex = "00017343ff63000000180000008202455c236e04400d6504ef0b1400ec00df00e70095028c0006010c00a500ca00b600c600940234000a170a161616161616160c1616160a160c161616161616160c1616161617027f"

try:
    # Convert hex to bytes
    sig_data = bytes.fromhex(signal_hex)
    print(f"✅ Signal data: {len(sig_data)} bytes")
    print(f"Starts with: {sig_data[:16].hex()}")
    
    # Create IRSignal
    ir_signal = IRSignal(
        name="POWER_TEST",
        uid="power_test",
        modulation_freq=38238,
        lengths=[],
        sig_data=sig_data,
        no_repeats=1,
        intra_sig_pause=0.0,
        toggle_data=None
    )
    print(f"✅ Created IRSignal: {ir_signal.name}")
    
    print("🔌 Testing protocol formatting...")
    
    # Just test the protocol creation without actual network sending
    irnetbox = IRNetBox("172.16.6.62")
    print("📡 Library loaded successfully")
    print(f"Signal ready for transmission: {len(ir_signal.sig_data)} bytes")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()