#!/usr/bin/env python3
"""
RedRat ASYNC Output Fix
Adds the missing OUTPUT_IR_SYNC (0x08) trigger after ASYNC IR commands
"""

import sys
import os

def main():
    print("🔧 RedRat ASYNC Output Fix")
    print("="*50)
    print("Problem: ASYNC IR (0x30) sent but missing OUTPUT_IR_SYNC (0x08) trigger")
    print("Solution: Add 0x08 output trigger after 0x30 ASYNC command")
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
    
    print("🔍 Current ASYNC implementation:")
    if "self._send(MessageTypes.OUTPUT_IR_ASYNC, payload)" in content:
        print("   ✅ Found OUTPUT_IR_ASYNC (0x30) command")
    else:
        print("   ❌ OUTPUT_IR_ASYNC command not found")
        
    if "self._send(MessageTypes.OUTPUT_IR_SYNC)" in content and "after.*ASYNC" in content:
        print("   ✅ Found OUTPUT_IR_SYNC trigger after ASYNC")
        print("   ✅ Fix already applied!")
        return
    else:
        print("   ❌ Missing OUTPUT_IR_SYNC (0x08) trigger after ASYNC")
    
    print("")
    print("🔧 APPLYING FIX...")
    
    # Create backup
    backup_file = lib_file + ".backup_async_fix"
    try:
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"📁 Backup created: {backup_file}")
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return
    
    # Apply the fix - add OUTPUT_IR_SYNC trigger after ASYNC command
    new_content = content.replace(
        '''            self._send(MessageTypes.OUTPUT_IR_ASYNC, payload)
            logger.info("ASYNC IR signal sent successfully")''',
        '''            self._send(MessageTypes.OUTPUT_IR_ASYNC, payload)
            logger.info("ASYNC IR signal data uploaded")
            
            # Trigger the physical IR output (like hub baseline shows)
            logger.debug("Sending OUTPUT_IR_SYNC trigger to activate IR transmission")
            self._send(MessageTypes.OUTPUT_IR_SYNC)
            logger.info("ASYNC IR output triggered successfully")'''
    )
    
    # Also update the other ASYNC path
    new_content = new_content.replace(
        '''            self._send(MessageTypes.OUTPUT_IR_ASYNC, payload)
            logger.info("Forced MK3+ ASYNC IR signal sent successfully")''',
        '''            self._send(MessageTypes.OUTPUT_IR_ASYNC, payload)
            logger.info("Forced MK3+ ASYNC IR signal data uploaded")
            
            # Trigger the physical IR output (like hub baseline shows)
            logger.debug("Sending OUTPUT_IR_SYNC trigger to activate IR transmission")
            self._send(MessageTypes.OUTPUT_IR_SYNC)  
            logger.info("Forced MK3+ ASYNC IR output triggered successfully")'''
    )
    
    # Write the fixed content
    try:
        with open(lib_file, 'w') as f:
            f.write(new_content)
        print("✅ Fix applied successfully!")
    except Exception as e:
        print(f"❌ Error writing fixed file: {e}")
        return
    
    print("\n🎯 ASYNC OUTPUT FIX APPLIED:")
    print("="*50)
    print("✅ Added OUTPUT_IR_SYNC (0x08) trigger after ASYNC IR (0x30)")
    print("✅ Matches hub baseline behavior: 0x30 → 0x08")
    print("✅ Should now actually trigger physical IR output")
    
    print("\n💡 EXPECTED BEHAVIOR:")
    print("="*50)
    print("1. Send 0x30 (ASYNC IR) - Upload signal data to device")
    print("2. Send 0x08 (OUTPUT_IR_SYNC) - Trigger actual IR transmission")
    print("3. Device should now physically output the IR signal")
    print("4. PCAP should show both 0x30 and 0x08 messages")
    
    print("\n💡 NEXT STEPS:")
    print("="*50)
    print("1. Rebuild Docker container with the ASYNC fix")
    print("2. Test IR signal transmission")
    print("3. Capture PCAP - should show 0x30 followed by 0x08")
    print("4. Verify physical IR output actually works")
    print(f"5. Backup available: {backup_file}")

if __name__ == "__main__":
    main()