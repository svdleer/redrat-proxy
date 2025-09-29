#!/usr/bin/env python3
"""
Proxy vs Hub ERSPAN Comparison Test
Generates traffic using our working ASYNC protocol with sequence numbers
"""
import sys
import os
sys.path.append('/home/svdleer/redrat-proxy')

from app.services.irnetbox_lib_new import IRNetBox, IRSignal, OutputConfig, PowerLevel

def test_proxy_humax_power():
    """Send HUMAX POWER via our proxy using the exact working protocol"""
    print("🎯 Testing HUMAX POWER via PROXY (port 9, power 50)")
    print("   Using ASYNC protocol (0x30) with sequence numbers")
    
    # The exact working HUMAX POWER signal data (193 bytes)
    signal_data_hex = """00017343ff6300000018000000820245
5c236e04400d6504ef0b1400ec00df00e70095028c0006010c00a500210012000a00e7006000710095009700db11ff00
0102020202020202020202020202020202020202020202020202030202020202020202020202020202020202020202
0402020203020302030203020302030203027f0506070802090a0b0c0d040e020f0210111213140a1516161616
0a16161616160a161616161616160c1616160a160c161616161616160c1616161617027f"""
    
    # Clean and convert hex to bytes
    signal_data_hex = signal_data_hex.replace(' ', '').replace('\n', '')
    ir_data = bytes.fromhex(signal_data_hex)
    
    print(f"📡 Signal: {len(ir_data)} bytes")
    print(f"   Starts with: {ir_data[:16].hex()}")
    print(f"   Frequency: 38000Hz (0xff63)")
    
    try:
        with IRNetBox('172.16.6.62', 10001) as ir:
            print(f"✅ Connected to RedRat device")
            print(f"📤 Sending via ASYNC protocol (0x30):")
            print(f"   - Port: 9")
            print(f"   - Power: 50")
            print(f"   - Protocol: MK3/4 ASYNC with sequence numbers")
            
            # This will use our fixed protocol with:
            # 1. Device version query (seq=1)
            # 2. ASYNC IR data (0x30) with sequence number (seq=2)
            # 3. IR output trigger (0x08) with sequence number (seq=3)
            ir.irsend_raw(9, 50, ir_data)
            
            print("✅ HUMAX POWER sent successfully via proxy!")
            print("📊 Traffic captured for ERSPAN comparison")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 PROXY vs HUB ERSPAN COMPARISON")
    print("="*50)
    print("This will generate proxy traffic for comparison with hub PCAP")
    print("")
    
    # Generate the proxy traffic
    success = test_proxy_humax_power()
    
    if success:
        print("")
        print("🎉 SUCCESS! Proxy traffic generated")
        print("📈 Next steps:")
        print("1. Stop tcpdump capture")
        print("2. Compare proxy_vs_hub_comparison.pcap with original hub PCAP")
        print("3. Verify protocol sequences match exactly")
        print("")
        print("Key differences to look for:")
        print("- Message sequence numbers (we now include them)")
        print("- ASYNC protocol payload structure")
        print("- Port configuration (port 9 vs original)")
        print("- Signal data format (should be identical)")
    else:
        print("")
        print("❌ Failed to generate proxy traffic")
        print("Check RedRat device connectivity and try again")