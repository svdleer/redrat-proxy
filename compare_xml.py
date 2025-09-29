#!/usr/bin/env python3
"""
Compare POWER signals between current and old remotes.xml files
"""

import sys
sys.path.append('/home/svdleer/redrat-proxy')
from irnetbox_lib_new import IRSignalParser

def compare_xml_files():
    print("🔍 Comparing POWER signals between XML files")
    print("=" * 60)
    
    # Parse current XML
    print("📄 Loading current remotes.xml...")
    current_devices = IRSignalParser.parse_xml_file("remotes.xml")
    current_humax = None
    for d in current_devices:
        if 'humax' in d.name.lower():
            current_humax = d
            break
    
    # Parse old XML
    print("📄 Loading old remotes.xml...")
    old_devices = IRSignalParser.parse_xml_file("/home/svdleer/redrat-lib/redrat-lib.old/remotes.xml")
    old_humax = None
    for d in old_devices:
        if 'humax' in d.name.lower():
            old_humax = d
            break
    
    if not current_humax or not old_humax:
        print("❌ Could not find Humax device in one or both files")
        return
    
    # Find POWER signals
    current_power = None
    for s in current_humax.signals:
        if s.name.upper() == 'POWER':
            current_power = s
            break
    
    old_power = None
    for s in old_humax.signals:
        if s.name.upper() == 'POWER':
            old_power = s
            break
    
    if not current_power or not old_power:
        print("❌ Could not find POWER signal in one or both files")
        return
    
    print("\n📊 COMPARISON RESULTS:")
    print(f"Current XML POWER signal:")
    print(f"  Frequency: {current_power.modulation_freq}Hz")
    print(f"  Data size: {len(current_power.sig_data)} bytes")
    print(f"  Repeats: {current_power.no_repeats}")
    print(f"  Pause: {current_power.intra_sig_pause}ms")
    print(f"  Data start: {current_power.sig_data[:20].hex()}")
    print(f"  Data end: {current_power.sig_data[-20:].hex()}")
    print(f"  UID: {current_power.uid}")
    
    print(f"\nOld XML POWER signal:")
    print(f"  Frequency: {old_power.modulation_freq}Hz")
    print(f"  Data size: {len(old_power.sig_data)} bytes")
    print(f"  Repeats: {old_power.no_repeats}")
    print(f"  Pause: {old_power.intra_sig_pause}ms")
    print(f"  Data start: {old_power.sig_data[:20].hex()}")
    print(f"  Data end: {old_power.sig_data[-20:].hex()}")
    print(f"  UID: {old_power.uid}")
    
    # Compare data
    if current_power.sig_data == old_power.sig_data:
        print("\n✅ Signal data is IDENTICAL")
    else:
        print("\n❌ Signal data is DIFFERENT")
        print("🔍 Finding differences...")
        for i, (c, o) in enumerate(zip(current_power.sig_data, old_power.sig_data)):
            if c != o:
                print(f"  Byte {i}: current=0x{c:02x}, old=0x{o:02x}")
                if i > 10:  # Show first 10 differences only
                    print("  ... (more differences)")
                    break
    
    # Compare other attributes
    attrs_match = True
    if current_power.modulation_freq != old_power.modulation_freq:
        print(f"❌ Frequency differs: {current_power.modulation_freq} vs {old_power.modulation_freq}")
        attrs_match = False
    if current_power.no_repeats != old_power.no_repeats:
        print(f"❌ Repeats differ: {current_power.no_repeats} vs {old_power.no_repeats}")
        attrs_match = False
    if abs(current_power.intra_sig_pause - old_power.intra_sig_pause) > 0.1:
        print(f"❌ Pause differs: {current_power.intra_sig_pause} vs {old_power.intra_sig_pause}")
        attrs_match = False
    
    if attrs_match and current_power.sig_data == old_power.sig_data:
        print("\n🎉 Both POWER signals are IDENTICAL!")
    else:
        print("\n⚠️  POWER signals have differences")

if __name__ == "__main__":
    compare_xml_files()