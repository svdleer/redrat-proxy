#!/usr/bin/env python3
"""
Fix RedRat MK2/MK3 protocol detection issue
This script patches the protocol to use MK3+ SYNC mode for better compatibility
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.redratlib import IRNetBox, NetBoxTypes

def test_current_protocol():
    """Test what protocol the current device uses"""
    print("=== Testing Current Protocol Detection ===")
    
    # Try to connect and detect device
    try:
        redrat_ip = input("Enter RedRat device IP (or press Enter for 192.168.1.100): ").strip()
        if not redrat_ip:
            redrat_ip = "192.168.1.100"
        
        print(f"Connecting to RedRat at {redrat_ip}...")
        
        with IRNetBox(redrat_ip) as ir:
            print(f"Device Model: {ir.irnetbox_model} ({NetBoxTypes.get_name(ir.irnetbox_model)})")
            print(f"Port Count: {ir.ports}")
            
            # Check which protocol path it will take
            if ir.irnetbox_model == NetBoxTypes.MK2:
                print("❌ PROBLEM: Using MK2 protocol (chatty, many packets)")
                print("   This causes the 4.8x packet difference you observed")
                return "MK2"
            else:
                print("✅ Using MK3+ protocol (efficient, fewer packets)")
                return "MK3+"
                
    except Exception as e:
        print(f"Error: {e}")
        return None

def suggest_fix():
    """Suggest the fix for MK2/MK3 protocol issue"""
    print("\n=== PROTOCOL FIX RECOMMENDATIONS ===")
    print()
    print("PROBLEM IDENTIFIED:")
    print("  Your RedRat device is detected as MK2, causing excessive packet chatter")
    print("  Official tool likely forces MK3+ protocol for efficiency")
    print()
    print("SOLUTIONS:")
    print()
    print("1. FORCE MK3+ PROTOCOL (Recommended):")
    print("   - Modify redratlib.py to always use MK3+ SYNC protocol")
    print("   - This will reduce packets by ~80% and match official tool behavior")
    print()
    print("2. UPDATE DEVICE DETECTION:")
    print("   - Your device may actually be MK3+ but detected as MK2")
    print("   - Fix the device version detection logic")
    print()
    print("3. PROTOCOL VERSION OVERRIDE:")
    print("   - Add configuration option to force protocol version")
    print("   - Allow manual override regardless of device detection")

def create_mk3_fix():
    """Create a patched version that forces MK3+ protocol"""
    print("\n=== Creating MK3+ Protocol Fix ===")
    
    backup_file = "app/services/redratlib_backup.py"
    original_file = "app/services/redratlib.py"
    
    # Create backup
    try:
        import shutil
        shutil.copy2(original_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return False
    
    # Read the current file
    try:
        with open(original_file, 'r') as f:
            content = f.read()
        
        # Find and replace the protocol selection logic
        old_logic = '''        elif self.irnetbox_model == NetBoxTypes.MK2:
            logger.debug("Using MK2 protocol")'''
            
        new_logic = '''        elif self.irnetbox_model == NetBoxTypes.MK2:
            # FORCE MK3+ PROTOCOL: Use efficient SYNC mode instead of chatty MK2 protocol
            logger.debug("Device detected as MK2, but forcing MK3+ SYNC protocol for efficiency")
            logger.info("Protocol override: Using MK3+ SYNC mode to match official RedRat tool behavior")
            
            # MK3+ protocol - Use SYNC mode for better compatibility
            logger.debug(f"Using forced MK3+ protocol for device model: {self.irnetbox_model}")
            
            # For MK3+ devices, use SYNC mode with proper data format
            ports = [0] * self.ports
            ports[port - 1] = power
            
            logger.debug(f"Port configuration: {ports}")
            
            # Format the data payload for SYNC mode
            packet_format = "{0}s{1}s".format(self.ports, len(data))
            logger.debug(f"Packet format: {packet_format}")
            
            payload = struct.pack(
                packet_format,
                struct.pack("{}B".format(self.ports), *ports),
                data)
            
            self._send(MessageTypes.OUTPUT_IR_SYNC, payload)
            logger.info("Forced MK3+ SYNC IR signal sent successfully")
            return  # Skip the original MK2 logic'''
        
        if old_logic in content:
            new_content = content.replace(old_logic, new_logic)
            
            # Write the patched file
            with open(original_file, 'w') as f:
                f.write(new_content)
            
            print("✅ Protocol fix applied successfully!")
            print("   - MK2 devices will now use efficient MK3+ SYNC protocol")
            print("   - This should reduce packet count by ~80%")
            print("   - Behavior should now match official RedRat tool")
            print()
            print("To revert: cp app/services/redratlib_backup.py app/services/redratlib.py")
            return True
        else:
            print("❌ Could not find expected code pattern to patch")
            return False
            
    except Exception as e:
        print(f"❌ Error applying fix: {e}")
        return False

if __name__ == "__main__":
    print("RedRat MK2/MK3 Protocol Fix Tool")
    print("=" * 40)
    
    # Test current protocol
    current_protocol = test_current_protocol()
    
    # Show recommendations
    suggest_fix()
    
    if current_protocol == "MK2":
        print()
        apply_fix = input("Apply MK3+ protocol fix? (y/N): ").strip().lower()
        
        if apply_fix == 'y':
            if create_mk3_fix():
                print()
                print("🎉 Fix applied! Restart your Flask app to test the changes.")
                print("   The proxy should now send ~80% fewer packets and match official tool behavior.")
            else:
                print("❌ Fix failed. Check the file manually.")
        else:
            print("Fix not applied. You can run this script again anytime.")
    else:
        print("\nDevice already uses MK3+ protocol. Protocol differences may be due to other factors.")
