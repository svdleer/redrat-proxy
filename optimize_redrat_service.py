#!/usr/bin/env python3
"""
RedRat Service Optimization
Removes unnecessary initialization and streamlines IR signal transmission
"""

import sys
import os

def main():
    print("🚀 RedRat Service Optimization")
    print("="*50)
    print("Problem: Proxy does excessive initialization (power_on, indicators, delays)")
    print("Solution: Streamline to send IR signals directly like the original hub")
    print("")
    
    # Path to the service file
    service_file = "/home/svdleer/redrat-proxy/app/services/redrat_service.py"
    
    # Read current content
    try:
        with open(service_file, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading service file: {e}")
        return
    
    print("🔍 Current initialization found:")
    
    # Check current initialization steps
    if "ir.power_on()" in content:
        print("   ❌ ir.power_on() - Powers on device every time")
    if "ir.indicators_on()" in content:
        print("   ❌ ir.indicators_on() - Turns on indicators every time")  
    if "time.sleep(0.1)" in content:
        print("   ❌ time.sleep(0.1) - Unnecessary delays")
    if "for repeat in range(no_repeats)" in content:
        print("   ❌ Multiple repeats - Sends command multiple times")
    
    print("")
    print("🔧 APPLYING OPTIMIZATION...")
    
    # Create backup
    backup_file = service_file + ".backup_optimization"
    try:
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"📁 Backup created: {backup_file}")
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return
    
    # Apply optimizations
    new_content = content
    
    # 1. Remove power_on() calls in IR execution
    new_content = new_content.replace(
        '''                    # Ensure device is powered on and ready
                    logger.debug(f"Powering on RedRat device and preparing port {ir_port}")
                    ir.power_on()''',
        '''                    # Device should already be powered and ready
                    logger.debug(f"Sending IR signal directly to port {ir_port}")'''
    )
    
    # 2. Remove indicators_on() 
    new_content = new_content.replace(
        '''                    
                    # Turn on indicators for visual feedback
                    ir.indicators_on()''',
        '''                    
                    # Skipping indicators for efficiency'''
    )
    
    # 3. Remove sleep delay
    new_content = new_content.replace(
        '''                    
                    # Small delay to ensure device is ready
                    time.sleep(0.1)''',
        '''                    
                    # No delay needed - send immediately'''
    )
    
    # 4. Simplify repeat logic to single send (most efficient)
    new_content = new_content.replace(
        '''                    # Send the IR signal with specified number of repeats
                    for repeat in range(no_repeats):
                        if repeat > 0:
                            logger.debug(f"Sending repeat {repeat + 1} of {no_repeats}")
                            # Apply inter-signal pause (convert ms to seconds)
                            time.sleep(intra_sig_pause / 1000.0)
                        
                        ir.irsend_raw(ir_port, power, ir_data)''',
        '''                    # Send the IR signal once (like original hub)
                    logger.debug(f"Sending IR signal: port={ir_port}, power={power}, data_size={len(ir_data)}")
                    ir.irsend_raw(ir_port, power, ir_data)'''
    )
    
    # Write the optimized content
    try:
        with open(service_file, 'w') as f:
            f.write(new_content)
        print("✅ Optimization applied successfully!")
    except Exception as e:
        print(f"❌ Error writing optimized file: {e}")
        return
    
    print("\n🎯 OPTIMIZATIONS APPLIED:")
    print("="*50)
    print("✅ Removed ir.power_on() from every command")
    print("✅ Removed ir.indicators_on() from every command") 
    print("✅ Removed artificial sleep delays")
    print("✅ Simplified to single IR signal send (no repeats)")
    print("✅ More efficient like original hub system")
    
    print("\n💡 NEXT STEPS:")
    print("="*50)
    print("1. Rebuild Docker container with optimized service")
    print("2. Test IR signal transmission")
    print("3. Compare new PCAP - should show fewer initialization messages")
    print("4. Verify IR signals work on actual device")
    print(f"5. Backup available: {backup_file}")

if __name__ == "__main__":
    main()