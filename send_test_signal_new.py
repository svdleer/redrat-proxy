#!/usr/bin/env python3
"""
Send a single IR signal for traffic analysis comparison.
"""

import sys
import time
sys.path.append('/home/svdleer/redrat-proxy')
from irnetbox_lib_new import IRNetBox, IRSignalParser, PowerLevel

def send_test_signal(device_name: str, signal_name: str):
    """Send a test signal for traffic analysis."""
    print(f"🎯 Sending Test Signal: {device_name} - {signal_name}")
    print("=" * 50)
    
    try:
        # Load signal
        devices = IRSignalParser.parse_xml_file("remotes.xml")
        device = None
        for d in devices:
            if device_name.lower() in d.name.lower():
                device = d
                break
        
        if not device:
            print(f"❌ Device '{device_name}' not found")
            return False
        
        signal = None
        for s in device.signals:
            if s.name.lower() == signal_name.lower():
                signal = s
                break
        
        if not signal:
            print(f"❌ Signal '{signal_name}' not found")
            return False
        
        print(f"✅ Found signal: {signal.name} ({signal.modulation_freq}Hz)")
        
        # Connect and send
        irnetbox = IRNetBox()
        print("🔌 Connecting to IRNetBox at 172.16.6.62...")
        
        if not irnetbox.connect("172.16.6.62"):
            print("❌ Connection failed")
            return False
        
        print("✅ Connected!")
        
        # Send signal
        print(f"📡 Sending '{signal.name}' signal...")
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

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 send_test_signal.py <device> <signal>")
        print("Example: python3 send_test_signal.py humax power")
        return 1
    
    device_name = sys.argv[1]
    signal_name = sys.argv[2]
    
    success = send_test_signal(device_name, signal_name)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
