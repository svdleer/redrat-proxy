#!/usr/bin/env python3
"""
Test with the old remotes.xml file
"""

import sys
import time
sys.path.append('/home/svdleer/redrat-proxy')
from irnetbox_lib_new import IRNetBox, IRSignalParser, PowerLevel

def send_test_signal_old_xml(device_name: str, signal_name: str):
    """Send a test signal using the old XML file."""
    print(f"🎯 Testing with OLD remotes.xml: {device_name} - {signal_name}")
    print("=" * 50)
    
    try:
        # Load signal from OLD XML file
        devices = IRSignalParser.parse_xml_file("/home/svdleer/redrat-lib/redrat-lib.old/remotes.xml")
        device = None
        for d in devices:
            if device_name.lower() in d.name.lower():
                device = d
                break
        
        if not device:
            print(f"❌ Device '{device_name}' not found in old XML")
            return False
        
        signal = None
        for s in device.signals:
            if s.name.lower() == signal_name.lower():
                signal = s
                break
        
        if not signal:
            print(f"❌ Signal '{signal_name}' not found in old XML")
            return False
        
        print(f"✅ Found signal: {signal.name} ({signal.modulation_freq}Hz)")
        print(f"📊 Signal data: {len(signal.sig_data)} bytes, starts with: {signal.sig_data[:16].hex()}")
        
        # Connect and send
        irnetbox = IRNetBox()
        print("🔌 Connecting to IRNetBox at 172.16.6.62...")
        
        if not irnetbox.connect("172.16.6.62"):
            print("❌ Connection failed")
            return False
        
        print("✅ Connected!")
        
        # Send signal
        print(f"📡 Sending '{signal.name}' signal from OLD XML...")
        result = irnetbox.send_signal_robust(
            signal=signal,
            port=9,
            power_level=PowerLevel.HIGH,
            max_retries=1
        )
        
        if result['success']:
            print(f"✅ Signal sent successfully in {result['total_time']:.2f}s")
        else:
            print(f"❌ Signal failed: {result['error']}")
        
        irnetbox.disconnect()
        print("🔌 Disconnected")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = send_test_signal_old_xml("humax", "power")
    print(f"\nResult: {'SUCCESS' if success else 'FAILURE'}")