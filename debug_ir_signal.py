#!/usr/bin/env python3
"""
Debug IR signal data to understand why device doesn't power on
"""

import sys
import os
import time
import base64

# Add the app directory to the Python path
sys.path.insert(0, '/home/svdleer/redrat-proxy')

def analyze_signal_data():
    """Analyze the IR signal data we're using"""
    
    print("🔍 IR SIGNAL DATA ANALYSIS")
    print("=" * 50)
    
    # Test signal data from XML
    test_signal_b64 = "AQICAgICAgICAgICAgICAgICAgICAgICAgICAgICAwICAgICAgICAgICAgICAgICAgICAgICAgICAgIEAgICAgMCAwIDAgMCAwIDAgMCAwIDAgMCB/"
    
    # Fix padding
    missing_padding = len(test_signal_b64) % 4
    if missing_padding:
        test_signal_b64 += '=' * (4 - missing_padding)
        
    signal_data = base64.b64decode(test_signal_b64)
    
    print(f"📊 Signal Data Analysis:")
    print(f"   Length: {len(signal_data)} bytes")
    print(f"   Hex: {signal_data.hex()}")
    print()
    
    print("📈 Signal Pattern Analysis:")
    # Count different values in signal data
    value_counts = {}
    for byte in signal_data:
        value_counts[byte] = value_counts.get(byte, 0) + 1
    
    print("   Value distribution:")
    for value, count in sorted(value_counts.items()):
        print(f"     0x{value:02x} ({value:3d}): {count:3d} times ({count/len(signal_data)*100:.1f}%)")
    
    print()
    print("🎯 Signal Characteristics:")
    print(f"   Modulation: 38238 Hz (standard consumer IR)")
    print(f"   Lengths: [0.56, 0.56, 0.56, 1.68] ms")
    print(f"   Repeats: 1")
    print(f"   Pause: 0.0 ms")
    
    # Analyze if this looks like a valid IR signal
    unique_values = len(value_counts)
    print()
    print("🔬 Signal Validity Check:")
    print(f"   Unique values: {unique_values}")
    
    if unique_values <= 4:
        print("   ✅ Low complexity - typical for simple IR signals")
    elif unique_values <= 8:
        print("   ⚠️  Medium complexity - might be valid")
    else:
        print("   ❌ High complexity - suspicious for IR timing data")
    
    # Check for common IR patterns
    if 1 in value_counts and 2 in value_counts:
        print("   ✅ Contains timing indices 1 and 2 - typical IR pattern")
    
    if 3 in value_counts:
        print("   ✅ Contains timing index 3 - extended pattern")
    
    if 4 in value_counts:
        print("   ✅ Contains timing index 4 - complex pattern")
        
    if 7 in value_counts:
        print("   ✅ Contains end marker (7) - properly terminated")
    
    return signal_data

def test_different_power_levels():
    """Test signal transmission with different power levels and ports"""
    
    print("\n🚀 POWER LEVEL TESTING")
    print("=" * 50)
    
    try:
        from app.services.irnetbox_lib_new import IRNetBox, IRSignal, OutputConfig, PowerLevel
        
        # Test signal
        test_signal_b64 = "AQICAgICAgICAgICAgICAgICAgICAgICAgICAgICAwICAgICAgICAgICAgICAgICAgICAgICAgICAgIEAgICAgMCAwIDAgMCAwIDAgMCAwIDAgMCB/"
        missing_padding = len(test_signal_b64) % 4
        if missing_padding:
            test_signal_b64 += '=' * (4 - missing_padding)
        signal_data = base64.b64decode(test_signal_b64)
        
        test_signal = IRSignal(
            name="POWER_TEST",
            uid="power_test",
            modulation_freq=38238,  # Standard consumer IR
            lengths=[0.56, 0.56, 0.56, 1.68],
            sig_data=signal_data,
            no_repeats=1,
            intra_sig_pause=0.0
        )
        
        # Connect to RedRat
        redrat = IRNetBox()
        if not redrat.connect("172.16.6.62"):
            print("❌ Could not connect to RedRat device")
            return
        
        print("✅ Connected to RedRat device")
        print(f"   Device Type: {redrat.device_type.value}")
        print(f"   Firmware: {redrat.firmware_version}")
        
        # Test different power levels on port 9
        power_levels = [
            (PowerLevel.HIGH, "HIGH (100%)"),
            (PowerLevel.MEDIUM, "MEDIUM (50%)"), 
            (PowerLevel.LOW, "LOW (25%)")
        ]
        
        for power_level, power_name in power_levels:
            print(f"\n🔋 Testing {power_name} on Port 9...")
            
            try:
                output_config = OutputConfig(port=9, power_level=power_level)
                seq_num = redrat.send_signal_async(test_signal, [output_config], 
                                                  post_delay_ms=1000)  # Longer delay
                
                print(f"   ✅ Signal sent (seq: {seq_num})")
                print(f"   💡 Check if your device responded to {power_name}")
                time.sleep(3)  # Wait before next test
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
        
        # Test on different ports with HIGH power
        print(f"\n🔌 Testing HIGH power on different ports...")
        test_ports = [1, 2, 9, 10]
        
        for port in test_ports:
            print(f"\n   Testing Port {port}...")
            try:
                output_config = OutputConfig(port=port, power_level=PowerLevel.HIGH)
                seq_num = redrat.send_signal_async(test_signal, [output_config], 
                                                  post_delay_ms=1000)
                
                print(f"     ✅ Signal sent on port {port} (seq: {seq_num})")
                print(f"     💡 Check if your device responded")
                time.sleep(2)
                
            except Exception as e:
                print(f"     ❌ Failed: {e}")
        
        redrat.disconnect()
        print("\n🔌 Disconnected from RedRat device")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def test_signal_variations():
    """Test different signal variations to find what works"""
    
    print("\n🎛️  SIGNAL VARIATION TESTING")
    print("=" * 50)
    
    try:
        from app.services.irnetbox_lib_new import IRNetBox, IRSignal, OutputConfig, PowerLevel
        
        # Original signal data
        test_signal_b64 = "AQICAgICAgICAgICAgICAgICAgICAgICAgICAgICAwICAgICAgICAgICAgICAgICAgICAgICAgICAgIEAgICAgMCAwIDAgMCAwIDAgMCAwIDAgMCB/"
        missing_padding = len(test_signal_b64) % 4
        if missing_padding:
            test_signal_b64 += '=' * (4 - missing_padding)
        signal_data = base64.b64decode(test_signal_b64)
        
        # Connect to RedRat
        redrat = IRNetBox()
        if not redrat.connect("172.16.6.62"):
            print("❌ Could not connect to RedRat device")
            return
        
        print("✅ Connected to RedRat device")
        
        # Test variations
        variations = [
            {
                'name': 'Original Signal',
                'freq': 38238,
                'lengths': [0.56, 0.56, 0.56, 1.68],
                'repeats': 1,
                'pause': 0.0
            },
            {
                'name': 'More Repeats',
                'freq': 38238,
                'lengths': [0.56, 0.56, 0.56, 1.68],
                'repeats': 3,  # Try multiple repeats
                'pause': 100.0  # With pause between repeats
            },
            {
                'name': 'Standard 38KHz',
                'freq': 38000,  # Round frequency
                'lengths': [0.56, 0.56, 0.56, 1.68],
                'repeats': 1,
                'pause': 0.0
            },
            {
                'name': 'Alternative Frequency',
                'freq': 36000,  # Different frequency
                'lengths': [0.56, 0.56, 0.56, 1.68],
                'repeats': 1,
                'pause': 0.0
            },
            {
                'name': 'Longer Timing',
                'freq': 38238,
                'lengths': [1.0, 1.0, 1.0, 2.0],  # Longer timing
                'repeats': 1,
                'pause': 0.0
            }
        ]
        
        for i, var in enumerate(variations):
            print(f"\n🧪 Test {i+1}: {var['name']}")
            print(f"   Freq: {var['freq']} Hz")
            print(f"   Lengths: {var['lengths']}")
            print(f"   Repeats: {var['repeats']}")
            print(f"   Pause: {var['pause']} ms")
            
            try:
                test_signal = IRSignal(
                    name=f"POWER_{i+1}",
                    uid=f"power_test_{i+1}",
                    modulation_freq=var['freq'],
                    lengths=var['lengths'],
                    sig_data=signal_data,
                    no_repeats=var['repeats'],
                    intra_sig_pause=var['pause']
                )
                
                output_config = OutputConfig(port=9, power_level=PowerLevel.HIGH)
                seq_num = redrat.send_signal_async(test_signal, [output_config], 
                                                  post_delay_ms=1500)
                
                print(f"   ✅ Signal sent (seq: {seq_num})")
                print(f"   💡 Check if your device responded")
                time.sleep(4)  # Wait between tests
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
        
        redrat.disconnect()
        print("\n🔌 Disconnected from RedRat device")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run all analyses
    analyze_signal_data()
    test_different_power_levels()
    test_signal_variations()
    
    print("\n" + "=" * 50)
    print("🎯 NEXT STEPS:")
    print("1. Check if any of the above tests powered on your device")
    print("2. If none worked, we may need the actual IR signal from your XML file")
    print("3. Consider testing with a different device/remote")
    print("4. Verify the IR LED output is working (use phone camera to see IR)")