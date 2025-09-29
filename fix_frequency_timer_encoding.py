#!/usr/bin/env python3

"""
Fix frequency encoding in redrat_service.py according to RedRat specs.

According to the RedRat IRNetBox documentation (section 5.2.8.2):
The timer producing the modulation/carrier frequency switching runs at 6MHz, so converting 
a required frequency value in Hz (e.g. 38000Hz), the following equation is used:

timer_value = 65536 - (6MHz / carrier_freq_in_Hz)

As the timer_value is an up-counting re-load value, we subtract it from 65536 to give 
the correct timer count to overflow.

The current code incorrectly encodes the raw frequency value instead of the timer value.
"""

import re
import os

def fix_frequency_encoding():
    file_path = "/home/svdleer/redrat-proxy/app/services/redrat_service.py"
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the frequency encoding section and replace it
    old_pattern = r'''(\s+)# Encode frequency as 16-bit little endian at offset 2
(\s+)freq_bytes = modulation_freq\.to_bytes\(2, byteorder='little'\)
(\s+)ir_data_list\[2\] = freq_bytes\[0\] 
(\s+)ir_data_list\[3\] = freq_bytes\[1\]'''
    
    new_replacement = r'''\1# Calculate RedRat timer value for frequency (per section 5.2.8.2 of spec)
\1# timer_value = 65536 - (6MHz / carrier_freq_in_Hz)
\1timer_value = int(65536 - (6000000 / modulation_freq))
\1# Ensure timer value is within valid range
\1timer_value = max(0, min(65535, timer_value))
\1logger.debug(f"Calculated timer value {timer_value} for frequency {modulation_freq}Hz")
\1# Encode timer value as 16-bit big-endian at offset 2 (per RedRat spec)  
\1timer_bytes = timer_value.to_bytes(2, byteorder='big')
\1ir_data_list[2] = timer_bytes[0] 
\1ir_data_list[3] = timer_bytes[1]'''
    
    if re.search(old_pattern, content, re.MULTILINE):
        content = re.sub(old_pattern, new_replacement, content, flags=re.MULTILINE)
        
        # Write the modified content back
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("✓ Fixed frequency encoding to use RedRat timer calculation")
        print("  - Now calculates: timer_value = 65536 - (6MHz / frequency)")
        print("  - Encodes as big-endian (per RedRat spec)")
        print("  - Added bounds checking for timer value")
        return True
    else:
        print("❌ Could not find frequency encoding pattern in redrat_service.py")
        print("The file may have already been updated or the pattern has changed.")
        return False

if __name__ == "__main__":
    print("Fixing frequency encoding in redrat_service.py...")
    if fix_frequency_encoding():
        print("\n🔧 Frequency encoding fix applied successfully!")
        print("Next steps:")
        print("1. Rebuild the Docker container")
        print("2. Test IR signal transmission")
        print("3. Check logs for proper timer value calculation")
    else:
        print("\n❌ Fix failed - manual intervention may be required")