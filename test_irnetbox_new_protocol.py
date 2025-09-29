#!/usr/bin/env python3
"""
Test irnetbox_lib_new protocol output vs working XML protocol
"""
import sys
import os
sys.path.append('/home/svdleer/redrat-proxy')

# Import the new library
from app.services.irnetbox_lib_new import IRNetBox, IRSignalParser, IRSignal, OutputConfig, PowerLevel
import base64

def test_irnetbox_new_protocol():
    """Test the new library protocol output"""
    print("🎯 TESTING IRNETBOX_LIB_NEW PROTOCOL")
    print("=====================================")
    
    # Create HUMAX POWER signal from XML data
    # This is the same signal data that was working before
    humax_power_signal = IRSignal(
        name="POWER",
        uid="HUMAX_POWER_001",
        modulation_freq=37343,  # From working signal
        lengths=[2.55, 1.125, 0.52, 0.255, 0.225, 0.255, 0.15, 0.255, 0.14, 0.255, 0.95, 0.14, 0.645, 0.1, 0.255, 0.6, 0.4, 0.255, 0.96, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.96, 0.255, 0.96, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.64, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.15, 0.255, 0.255],
        sig_data=bytes.fromhex("0102020202020202020202020202020202020202020202020202030202020202020202020202020202020202020204020202030203020302030203020302030203027f0506070802090a0b0c0d040e020f0210111213140a15161616160a16161616160a161616161616160c1616160a160c161616161616160c1616161617027f"),
        no_repeats=1,
        intra_sig_pause=100.0
    )
    
    print(f"Signal: {humax_power_signal.name}")
    print(f"Freq: {humax_power_signal.modulation_freq}Hz")
    print(f"Lengths: {len(humax_power_signal.lengths)}")
    print(f"Data: {len(humax_power_signal.sig_data)} bytes")
    print()
    
    # Create IRNetBox instance  
    ir = IRNetBox("172.16.6.62")
    
    try:
        # Connect to device
        print("🔌 Connecting to RedRat device...")
        if not ir.connect():
            print("❌ Failed to connect to RedRat device")
            return
        print("✅ Connected!")
        
        # Get device info
        device_info = ir.get_device_info()
        print(f"Device: {device_info['device_type']} at {device_info['ip_address']}")
        print()
        
        # Test signal conversion (this is what the new library will send)
        print("🧪 Testing signal conversion...")
        binary_signal = ir.download_signal(humax_power_signal)
        
        print(f"Binary signal length: {len(binary_signal)} bytes")
        print(f"Binary signal (hex): {binary_signal.hex()[:80]}...")
        print()
        
        # Compare with working protocol
        working_hex = "5af3f4010000000000000000640000000000000000017343ff63000010180200008202455c236e04400d6504ef0b1400ec00df00e70095028c0006010c00a500210012000a00e7006000710095009700db11ff000102020202020202020202020202020202020202020202020202030202020202020202020202020202020202020204020202030203020302030203020302030203027f0506070802090a0b0c0d040e020f0210111213140a15161616160a16161616160a161616161616160c1616160a160c161616161616160c1616161617027f"
        working_binary = bytes.fromhex(working_hex)
        
        print("📋 PROTOCOL COMPARISON:")
        print(f"New lib signal: {len(binary_signal)} bytes")
        print(f"Working signal: {len(working_binary)} bytes")
        print()
        
        print("First 40 bytes:")
        print(f"New lib: {binary_signal[:20].hex()}")
        print(f"Working: {working_binary[:20].hex()}")
        
        if binary_signal[:20] == working_binary[:20]:
            print("✅ Headers match!")
        else:
            print("❌ Headers differ!")
        print()
        
        # Test async output format
        output_configs = [OutputConfig(port=9, power_level=PowerLevel.HIGH)]
        
        print("🚀 Testing ASYNC protocol generation...")
        try:
            # This will test the async protocol format
            seq_num = ir.send_signal_async(humax_power_signal, output_configs, sequence_number=12345, post_delay_ms=500)
            print(f"✅ Generated ASYNC protocol with sequence {seq_num}")
        except Exception as e:
            print(f"⚠️  ASYNC test failed: {e}")
        
        print()
        print("🎉 Protocol test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ir.disconnect()

if __name__ == "__main__":
    test_irnetbox_new_protocol()