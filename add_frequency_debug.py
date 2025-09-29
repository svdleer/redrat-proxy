#!/usr/bin/env python3
"""
Enhanced Frequency Fix with Debug Logging

Add comprehensive debug logging to track frequency extraction and encoding.
"""

import os
import sys
import shutil

def add_debug_logging():
    print("🔧 Adding Debug Logging for Frequency Issue")
    print("==========================================")
    
    service_file = "/home/svdleer/redrat-proxy/app/services/redrat_service.py"
    
    # Read current file
    with open(service_file, 'r') as f:
        content = f.read()
    
    # Add debug logging right before the frequency encoding fix
    old_debug_pattern = '''                    # FREQUENCY ENCODING FIX: Ensure frequency is properly encoded in IR data
                    modulation_freq = ir_params.get('modulation_freq')'''
    
    new_debug_pattern = '''                    # FREQUENCY ENCODING FIX: Ensure frequency is properly encoded in IR data
                    logger.debug(f"DEBUG: ir_params keys = {list(ir_params.keys())}")
                    logger.debug(f"DEBUG: ir_params = {ir_params}")
                    modulation_freq = ir_params.get('modulation_freq')
                    logger.debug(f"DEBUG: extracted modulation_freq = {modulation_freq}")'''
    
    if old_debug_pattern in content:
        new_content = content.replace(old_debug_pattern, new_debug_pattern)
        
        with open(service_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Debug logging added!")
        return True
    else:
        print("❌ Could not find frequency encoding fix to debug")
        return False

if __name__ == "__main__":
    add_debug_logging()