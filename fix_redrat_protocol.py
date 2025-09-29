#!/usr/bin/env python3
"""
RedRat Protocol Fix
Updates the RedRat library to use MK3/4 ASYNC format (0x30) instead of SYNC format (0x08)
Based on PCAP analysis showing original system uses 0x30 format with header ae540000
"""

import sys
import os

# Add app to path
sys.path.insert(0, '/home/svdleer/redrat-proxy')

def main():
    print("🔧 RedRat Protocol Fix")
    print("="*50)
    print("Problem: Proxy uses SYNC format (0x08), but original uses ASYNC format (0x30)")
    print("Solution: Update redratlib_with_mk3_fix.py to use MK3/4 ASYNC format")
    print("")
    
    # Path to the library file
    lib_file = "/home/svdleer/redrat-proxy/app/services/redratlib_with_mk3_fix.py"
    
    # Read current content
    try:
        with open(lib_file, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading library file: {e}")
        return
    
    print("🔍 Current irsend_raw method analysis:")
    
    # Check what protocol is currently being used
    if "OUTPUT_IR_SYNC" in content and "self._send(MessageTypes.OUTPUT_IR_SYNC" in content:
        print("   Currently using: OUTPUT_IR_SYNC (0x08) - WRONG!")
        needs_fix = True
    elif "OUTPUT_IR_ASYNC" in content and "self._send(MessageTypes.OUTPUT_IR_ASYNC" in content:
        print("   Currently using: OUTPUT_IR_ASYNC (0x30) - CORRECT!")
        needs_fix = False
    else:
        print("   Cannot determine current protocol")
        needs_fix = True
    
    if not needs_fix:
        print("✅ Library already uses correct ASYNC format!")
        return
    
    print("\n🔧 APPLYING FIX...")
    print("   Replacing OUTPUT_IR_SYNC with OUTPUT_IR_ASYNC")
    
    # Create backup
    backup_file = lib_file + ".backup"
    try:
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"📁 Backup created: {backup_file}")
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return
    
    # Apply the fix
    new_content = content.replace(
        "self._send(MessageTypes.OUTPUT_IR_SYNC, payload)",
        "self._send(MessageTypes.OUTPUT_IR_ASYNC, payload)"
    )
    
    # Also update any comments that reference SYNC
    new_content = new_content.replace(
        "# For MK3+ devices, use SYNC mode with proper data format",
        "# For MK3+ devices, use ASYNC mode with proper data format"
    )
    new_content = new_content.replace(
        "# Based on working packet analysis: use message type 0x08 (OUTPUT_IR_SYNC)",
        "# Based on working packet analysis: use message type 0x30 (OUTPUT_IR_ASYNC)"
    )
    new_content = new_content.replace(
        "logger.info(\"Forced MK3+ SYNC IR signal sent successfully\")",
        "logger.info(\"Forced MK3+ ASYNC IR signal sent successfully\")"
    )
    new_content = new_content.replace(
        "logger.info(\"SYNC IR signal sent successfully\")",
        "logger.info(\"ASYNC IR signal sent successfully\")"
    )
    new_content = new_content.replace(
        "# Format the data payload for SYNC mode",
        "# Format the data payload for ASYNC mode"
    )
    new_content = new_content.replace(
        "# Format the data payload for SYNC mode (matching working packets)",
        "# Format the data payload for ASYNC mode (matching working packets)"
    )
    
    # Write the fixed content
    try:
        with open(lib_file, 'w') as f:
            f.write(new_content)
        print("✅ Fix applied successfully!")
    except Exception as e:
        print(f"❌ Error writing fixed file: {e}")
        return
    
    print("\n🎯 VERIFICATION:")
    # Verify the fix
    try:
        with open(lib_file, 'r') as f:
            fixed_content = f.read()
        
        if "self._send(MessageTypes.OUTPUT_IR_ASYNC, payload)" in fixed_content:
            print("✅ OUTPUT_IR_ASYNC is now being used")
        else:
            print("❌ Fix verification failed")
            
        sync_count = fixed_content.count("OUTPUT_IR_SYNC")
        async_count = fixed_content.count("OUTPUT_IR_ASYNC") 
        print(f"   OUTPUT_IR_SYNC references: {sync_count}")
        print(f"   OUTPUT_IR_ASYNC references: {async_count}")
        
    except Exception as e:
        print(f"❌ Error verifying fix: {e}")
    
    print("\n💡 NEXT STEPS:")
    print("="*50)
    print("1. Restart the RedRat proxy Docker container")
    print("2. Test IR signal transmission")
    print("3. Compare new PCAP with original to verify 0x30 format")
    print("4. If still not working, check the data payload format")
    print(f"5. Backup is available: {backup_file}")

if __name__ == "__main__":
    main()