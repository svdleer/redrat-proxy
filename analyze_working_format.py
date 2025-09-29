#!/usr/bin/env python3

"""
Analyze the working hub signal format to determine correct frequency encoding position.
"""

def analyze_working_signal():
    # Working hub signal from the comparison
    hub_signal_hex = "020000000000000000000000210000000000000000017340ff63000000050000"
    
    # Our proxy signal
    proxy_signal_hex = "0000000000000000320000000000000000017343ff6300000018000000820245"
    
    hub_bytes = bytes.fromhex(hub_signal_hex)
    proxy_bytes = bytes.fromhex(proxy_signal_hex)
    
    print("WORKING HUB vs PROXY SIGNAL ANALYSIS")
    print("=" * 60)
    
    print("HUB    (working):", hub_signal_hex)
    print("PROXY  (failing):", proxy_signal_hex)
    print()
    
    # Look for frequency patterns
    print("FREQUENCY ANALYSIS:")
    print("-" * 30)
    
    # Expected frequency is ~38kHz
    expected_freq = 38238
    expected_timer = 65536 - (6000000 // expected_freq)
    print(f"Expected frequency: {expected_freq} Hz")
    print(f"Expected timer value: {expected_timer} (0x{expected_timer:04x})")
    print()
    
    print("HUB signal potential frequency locations:")
    for i in range(0, len(hub_bytes)-1, 2):
        val_be = int.from_bytes(hub_bytes[i:i+2], 'big')
        val_le = int.from_bytes(hub_bytes[i:i+2], 'little')
        
        if val_be > 0 and val_be < 65536:
            freq_be = 6000000 / (65536 - val_be) if (65536 - val_be) > 0 else 0
        else:
            freq_be = 0
            
        if val_le > 0 and val_le < 65536:
            freq_le = 6000000 / (65536 - val_le) if (65536 - val_le) > 0 else 0
        else:
            freq_le = 0
            
        print(f"  Bytes {i:2d}-{i+1:2d}: {hub_bytes[i:i+2].hex()} = BE:{val_be:5d} ({freq_be:6.0f}Hz) | LE:{val_le:5d} ({freq_le:6.0f}Hz)")
    
    print()
    print("Key differences in the header structure:")
    print("-" * 40)
    for i in range(min(len(hub_bytes), len(proxy_bytes))):
        if hub_bytes[i] != proxy_bytes[i]:
            print(f"  Byte {i:2d}: HUB=0x{hub_bytes[i]:02x}, PROXY=0x{proxy_bytes[i]:02x}")
    
    print()
    print("ANALYSIS:")
    print("-" * 10)
    print("1. HUB has 0x7340 at bytes 20-21 (big-endian)")
    print("2. HUB has 0xff63 at bytes 22-23")  
    print("3. PROXY has 0x7343 at bytes 18-19")
    print("4. PROXY has 0xff63 at bytes 20-21")
    print()
    print("The frequency encoding appears to be at DIFFERENT POSITIONS!")
    print("HUB format may use a different header structure than what we're generating.")

if __name__ == "__main__":
    analyze_working_signal()