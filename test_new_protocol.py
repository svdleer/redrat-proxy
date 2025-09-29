#!/usr/bin/env python3

"""Test script for the new proper RedRat protocol sequence."""

import sys
import os
sys.path.append('/home/svdleer/redrat-proxy')

# Import our fixed redrat library
from app.services.redratlib_with_mk3_fix import IRNetBox

def test_new_protocol():
    """Test the new proper RedRat protocol sequence with HUMAX POWER on port 9."""
    
    # Test data - using the exact working IR signal from PCAP
    working_ir_data = bytes.fromhex("000000000000000032000000000000000001ff63ff6300000018000000820245554c236e04400d6504ef0b1400ec00df00e70095028c0006010c00a500210012000a00e7006000710095009700db11ff000102020202020202020202020202020202020202020202020202030202020202020202020202020202020202020204020202030203020302030203020302030203027f0506070802090a0b0c0d040e020f0210111213140a15161616160a16161616160a161616161616160c1616160a160c161616161616160c1616161617027f")
    
    redrat_host = "172.16.6.62"  # RedRat device IP from database
    ir_port = 9                  # HUMAX on port 9 as requested
    power = 50
    
    print(f"🎯 Testing HUMAX POWER signal on port 9")
    print(f"Target: {redrat_host}, Port: {ir_port} (HUMAX), Power: {power}")
    print(f"IR Data: {len(working_ir_data)} bytes")
    print(f"Signal starts with: {working_ir_data[:16].hex()}")
    
    try:
        with IRNetBox(redrat_host, 10001) as ir:
            print(f"✅ Connected to RedRat device")
            print(f"Device model: {ir.irnetbox_model}")
            print(f"Available ports: {ir.ports}")
            
            # Test our new protocol sequence
            ir.irsend_raw(ir_port, power, working_ir_data)
            
            print(f"🎉 Protocol test completed!")
            
    except Exception as e:
        print(f"❌ Protocol test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_protocol()