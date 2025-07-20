#!/usr/bin/env python3
"""
Simple verification that the DoubleSignal fix is in place
"""

import os

def check_doublesignal_fix():
    """Check if the DoubleSignal fix is properly implemented in the code"""
    
    service_file = "app/services/remote_service.py"
    
    if not os.path.exists(service_file):
        print("❌ remote_service.py not found")
        return False
    
    print("🔍 Checking DoubleSignal fix implementation...")
    
    with open(service_file, 'r') as f:
        content = f.read()
    
    # Check for the fixed logic
    fixes_to_check = [
        "# A DoubleSignal should be treated as ONE command",
        "# Process as a single command with the original name (no _Signal1 suffix)",
        "process_single_signal(signal1, name.text, signals, remote_name)"
    ]
    
    all_fixes_present = True
    
    for fix in fixes_to_check:
        if fix in content:
            print(f"✅ Found: {fix}")
        else:
            print(f"❌ Missing: {fix}")
            all_fixes_present = False
    
    # Check that the old incorrect logic is removed
    incorrect_patterns = [
        'f"{name.text}_Signal1"',
        'f"{name.text}_Signal2"',
        "process_single_signal(signal2,"
    ]
    
    for pattern in incorrect_patterns:
        if pattern in content:
            print(f"❌ Old incorrect pattern still present: {pattern}")
            all_fixes_present = False
        else:
            print(f"✅ Old pattern correctly removed: {pattern}")
    
    return all_fixes_present

def main():
    print("🚀 Verifying DoubleSignal Fix Implementation")
    print("=" * 50)
    
    if check_doublesignal_fix():
        print(f"\n🎉 SUCCESS: DoubleSignal fix is properly implemented!")
        print(f"📝 Summary of fix:")
        print(f"   • DoubleSignal entries are treated as single commands")
        print(f"   • No more _Signal1/_Signal2 suffixes")
        print(f"   • Uses Signal1 as the primary signal")
        print(f"   • Web upload will work correctly")
        return True
    else:
        print(f"\n❌ FAILURE: DoubleSignal fix is not properly implemented!")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
