#!/usr/bin/env python3

"""
Analyze the frequency encoding in RedRat IR data to determine correct format.
Based on the logs, we can see the IR data format and reverse engineer the encoding.
"""

import binascii

def analyze_ir_data():
    # From the recent logs - this is the IR data being sent
    ir_data_hex = "0001ff63ff63000000180000008202455c236e04400d6504ef0b1400ec00df00e70095028c0006010c00a500210012000a00e7006000710095009700db11ff000102020202020202020202020202020202020202020202020202030202020202020202020202020202020202020204020202030203020302030203020302030203027f0506070802090a0b0c0d040e020f0210111213140a15161616160a16161616160a161616161616160c1616160a160c161616161616160c1616161617027f"
    
    # Convert to bytes
    ir_data = binascii.unhexlify(ir_data_hex)
    
    print("IR Data Analysis")
    print("=" * 50)
    print(f"Total length: {len(ir_data)} bytes")
    print(f"First 20 bytes: {ir_data[:20].hex()}")
    print()
    
    # Analyze potential frequency positions
    print("Potential frequency encoding positions:")
    print("-" * 40)
    
    # Check bytes 0-1 
    freq_01 = int.from_bytes(ir_data[0:2], 'big')
    freq_01_le = int.from_bytes(ir_data[0:2], 'little')
    print(f"Bytes 0-1: {ir_data[0:2].hex()} = {freq_01} (BE) / {freq_01_le} (LE)")
    
    # Check bytes 2-3 (where we're currently encoding)
    freq_23 = int.from_bytes(ir_data[2:4], 'big')
    freq_23_le = int.from_bytes(ir_data[2:4], 'little')  
    print(f"Bytes 2-3: {ir_data[2:4].hex()} = {freq_23} (BE) / {freq_23_le} (LE)")
    
    # Check bytes 4-5
    freq_45 = int.from_bytes(ir_data[4:6], 'big')
    freq_45_le = int.from_bytes(ir_data[4:6], 'little')
    print(f"Bytes 4-5: {ir_data[4:6].hex()} = {freq_45} (BE) / {freq_45_le} (LE)")
    
    # The expected frequency should be around 38kHz (38000 Hz)
    expected_freq = 38000
    expected_timer_be = 65536 - (6000000 // expected_freq)  # Big endian calculation
    expected_timer_le = expected_timer_be
    
    print()
    print("Expected values for 38kHz:")
    print(f"Timer value (65536 - 6M/38k): {expected_timer_be}")
    print(f"Timer hex (BE): {expected_timer_be.to_bytes(2, 'big').hex()}")
    print(f"Timer hex (LE): {expected_timer_be.to_bytes(2, 'little').hex()}")
    
    # Check if any of the actual values match expected
    print()
    print("Frequency reverse calculations (assuming 6MHz/timer formula):")
    print("-" * 60)
    
    for pos, val_be, val_le in [(0, freq_01, freq_01_le), (2, freq_23, freq_23_le), (4, freq_45, freq_45_le)]:
        if val_be > 0 and val_be < 65536:
            calc_freq_be = 6000000 / (65536 - val_be) if (65536 - val_be) > 0 else 0
            print(f"Bytes {pos}-{pos+1} BE ({val_be:04x}): {calc_freq_be:.0f} Hz")
        
        if val_le > 0 and val_le < 65536:
            calc_freq_le = 6000000 / (65536 - val_le) if (65536 - val_le) > 0 else 0
            print(f"Bytes {pos}-{pos+1} LE ({val_le:04x}): {calc_freq_le:.0f} Hz")
    
    print()
    print("Raw data structure analysis:")
    print("-" * 30)
    for i in range(0, min(32, len(ir_data)), 2):
        val = int.from_bytes(ir_data[i:i+2], 'big')
        print(f"Bytes {i:2d}-{i+1:2d}: {ir_data[i:i+2].hex()} = {val:5d}")

if __name__ == "__main__":
    analyze_ir_data()