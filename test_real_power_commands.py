#!/usr/bin/env python3
"""
Test real power commands from database
"""

import sys
import os
import time
import base64
import json

# Add the app directory to the Python path
sys.path.insert(0, '/home/svdleer/redrat-proxy')

def test_real_power_commands():
    """Test the real power commands from the database"""
    
    print("🎯 TESTING REAL POWER COMMANDS FROM DATABASE")
    print("=" * 60)
    
    # Real power command data from your database
    power_commands = [
        {
            'id': 184,
            'name': 'Power',
            'device_type': 'SET_TOP_BOX', 
            'template_data': {
                "uid": "NsW62qXkCUCfUrQ73KMs8Q==",
                "command": "Power",
                "lengths": [0.4025, 0.29675, 0.15, 0.631, 0.79725, 0.46425],
                "remote_id": 15,
                "no_repeats": 1,
                "signal_data": "AAECAQIDAgECAQIEAgECAQIBAgECAwIFAgMCAQIBAgQCAQJ/AAECAQIDAgECAQIEAgECAQIBAgECAwIFAgMCAQIBAgQCAQJ/",
                "toggle_data": [{"len1": 1, "len2": 3, "bitNo": 19}, {"len1": 1, "len2": 3, "bitNo": 55}],
                "intra_sig_pause": 90.56775,
                "modulation_freq": "36000"
            }
        },
        {
            'id': 223,
            'name': 'POWER',
            'device_type': 'PVR',
            'template_data': {
                "uid": "RgTVkXKDn0C7hK9giKnH9Q==",
                "command": "POWER", 
                "lengths": [8.878, 4.535, 0.544, 1.7145, 0.6315, 1.418, 0.118, 0.1115, 0.1155, 0.0745, 0.326, 0.003, 0.134, 0.0825, 0.0165, 0.009, 0.005, 0.1155, 0.048, 0.0565, 0.0745, 0.0755, 0.1095, 2.3035],
                "remote_id": 16,
                "no_repeats": 2,
                "signal_data": "AAECAgICAgICAgICAgICAgICAgICAgICAgICAwICAgICAgICAgICAgICAgICAgIEAgICAwIDAgMCAwIDAgMCAwIDAn8FBgcIAgkKCwwNBA4CDwIQERITFAoVFhYWFgoWFhYWFgoWFhYWFhYWDBYWFgoWDBYWFhYWFhYMFhYWFhcCfw==",
                "toggle_data": [],
                "intra_sig_pause": 47.5215,
                "modulation_freq": "38350"
            }
        }
    ]
    
    try:
        from app.services.irnetbox_lib_new import IRNetBox, IRSignal, OutputConfig, PowerLevel
        
        # Connect to RedRat
        redrat = IRNetBox()
        if not redrat.connect("172.16.6.62"):
            print("❌ Could not connect to RedRat device")
            return
        
        print("✅ Connected to RedRat device")
        print(f"   Device Type: {redrat.device_type.value}")
        print()
        
        # Test each power command
        for i, cmd in enumerate(power_commands):
            template = cmd['template_data']
            
            print(f"🔋 Testing Command {i+1}: {cmd['name']} ({cmd['device_type']})")
            print(f"   Frequency: {template['modulation_freq']} Hz")
            print(f"   Repeats: {template['no_repeats']}")
            print(f"   Lengths: {len(template['lengths'])} timing values")
            print(f"   Signal Data: {len(template['signal_data'])} chars (base64)")
            
            # Decode signal data
            try:
                sig_data = base64.b64decode(template['signal_data'])
                print(f"   Decoded Signal: {len(sig_data)} bytes")
                print(f"   Signal Hex: {sig_data.hex()}")
            except Exception as e:
                print(f"   ❌ Failed to decode signal data: {e}")
                continue
            
            # Create IRSignal
            try:
                power_signal = IRSignal(
                    name=template['command'],
                    uid=template['uid'],
                    modulation_freq=int(template['modulation_freq']),
                    lengths=template['lengths'],
                    sig_data=sig_data,
                    no_repeats=template['no_repeats'],
                    intra_sig_pause=template['intra_sig_pause']
                )
                
                # Test with HIGH power on port 9
                print(f"   🚀 Sending with HIGH power on Port 9...")
                
                output_config = OutputConfig(port=9, power_level=PowerLevel.HIGH)
                seq_num = redrat.send_signal_async(power_signal, [output_config], 
                                                  post_delay_ms=1500)
                
                print(f"   ✅ Command sent! (seq: {seq_num})")
                print(f"   💡 **CHECK YOUR DEVICE NOW!**")
                print()
                
                # Wait for user to check device
                input("   Press Enter after checking if your device responded...")
                print()
                
                # Try with more repeats if original was single repeat
                if template['no_repeats'] <= 1:
                    print(f"   🔁 Trying with 3 repeats...")
                    
                    repeat_signal = IRSignal(
                        name=f"{template['command']}_REPEAT",
                        uid=f"{template['uid']}_repeat",
                        modulation_freq=int(template['modulation_freq']),
                        lengths=template['lengths'],
                        sig_data=sig_data,
                        no_repeats=3,
                        intra_sig_pause=max(100.0, template['intra_sig_pause'])
                    )
                    
                    seq_num2 = redrat.send_signal_async(repeat_signal, [output_config], 
                                                       post_delay_ms=2000)
                    
                    print(f"   ✅ Repeat command sent! (seq: {seq_num2})")
                    print(f"   💡 **CHECK YOUR DEVICE AGAIN!**")
                    print()
                    
                    input("   Press Enter after checking if your device responded...")
                    print()
                
            except Exception as e:
                print(f"   ❌ Failed to send command: {e}")
                print()
            
            print("-" * 50)
        
        redrat.disconnect()
        print("🔌 Disconnected from RedRat device")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🎯 REAL DATABASE POWER COMMAND TEST")
    print("=" * 60)
    print("This script will test the actual power commands from your database.")
    print("Watch your device carefully after each transmission!")
    print()
    
    test_real_power_commands()
    
    print()
    print("🎯 TEST SUMMARY:")
    print("- If one of the commands powered your device, note which one worked")
    print("- The working command contains the correct IR signal and timing")
    print("- Use that command's data for your RedRat proxy configuration")