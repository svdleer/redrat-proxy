#!/usr/bin/env python3
"""
RedRat Frequency Encoding Fix

Problem: The modulation frequency from the database template (38238 Hz) is not being
         encoded properly in the IR signal data, causing RedRat to return NACK error 51
         ("IR signal modulation frequency is too low").

Solution: Properly encode the frequency in the RedRat signal data format.
"""

import os
import sys
import shutil
from datetime import datetime

def fix_frequency_encoding():
    print("🔧 RedRat Frequency Encoding Fix")
    print("==================================================")
    print("Problem: Modulation frequency not properly encoded in IR data")
    print("Solution: Add frequency encoding to RedRat signal preparation")
    print()
    
    # File to modify
    service_file = "/home/svdleer/redrat-proxy/app/services/redrat_service.py"
    
    # Create backup
    backup_file = f"{service_file}.backup_freq_fix"
    shutil.copy2(service_file, backup_file)
    print(f"📁 Backup created: {backup_file}")
    
    # Read current file
    with open(service_file, 'r') as f:
        content = f.read()
    
    # Check if already fixed
    if "# FREQUENCY ENCODING FIX" in content:
        print("✅ Frequency encoding fix already applied!")
        return True
    
    # Find the place where ir_data is prepared and irsend_raw is called
    old_pattern = '''                    logger.debug(f"Device ready, sending IR signal to port {ir_port}")
                    
                    # Send the IR signal once (like original hub)
                    logger.debug(f"Sending IR signal: port={ir_port}, power={power}, data_size={len(ir_data)}")
                    ir.irsend_raw(ir_port, power, ir_data)'''
    
    new_pattern = '''                    logger.debug(f"Device ready, sending IR signal to port {ir_port}")
                    
                    # FREQUENCY ENCODING FIX: Ensure frequency is properly encoded in IR data
                    modulation_freq = ir_params.get('modulation_freq')
                    if modulation_freq and modulation_freq > 0:
                        logger.debug(f"Encoding frequency {modulation_freq}Hz into IR signal data")
                        # RedRat signal format: frequency should be encoded in bytes 2-3 (little endian)  
                        if len(ir_data) >= 4:
                            ir_data_list = list(ir_data)
                            # Encode frequency as 16-bit little endian at offset 2
                            freq_bytes = modulation_freq.to_bytes(2, byteorder='little')
                            ir_data_list[2] = freq_bytes[0] 
                            ir_data_list[3] = freq_bytes[1]
                            ir_data = bytes(ir_data_list)
                            logger.info(f"Frequency {modulation_freq}Hz encoded in IR data at bytes 2-3")
                        else:
                            logger.warning(f"IR data too short ({len(ir_data)} bytes) to encode frequency")
                    else:
                        logger.warning("No modulation frequency specified - using data as-is")
                    
                    # Send the IR signal once (like original hub)
                    logger.debug(f"Sending IR signal: port={ir_port}, power={power}, data_size={len(ir_data)}")
                    ir.irsend_raw(ir_port, power, ir_data)'''
    
    if old_pattern in content:
        new_content = content.replace(old_pattern, new_pattern)
        
        # Write the modified content
        with open(service_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Fix applied successfully!")
        print()
        print("🎯 FREQUENCY ENCODING FIX APPLIED:")
        print("==================================================")
        print("✅ Added frequency encoding to IR signal preparation")
        print("✅ Frequency from template will be encoded at bytes 2-3")
        print("✅ Should fix NACK error 51 (frequency too low)")
        print()
        print("💡 EXPECTED BEHAVIOR:")
        print("==================================================")
        print("1. Extract modulation_freq from template (38238 Hz)")
        print("2. Encode frequency into IR data at bytes 2-3 (little endian)")
        print("3. Send properly formatted IR data to RedRat")
        print("4. RedRat should accept the signal (no NACK error 51)")
        print()
        print("💡 NEXT STEPS:")
        print("==================================================")
        print("1. Rebuild Docker container with frequency fix")
        print("2. Test IR signal transmission")
        print("3. Check logs - should see frequency encoding messages")
        print("4. Verify no NACK error 51 occurs")
        print(f"5. Backup available: {backup_file}")
        
        return True
    else:
        print("❌ Could not find target pattern in redrat_service.py")
        print("💡 The file structure may have changed. Manual fix required.")
        return False

if __name__ == "__main__":
    fix_frequency_encoding()