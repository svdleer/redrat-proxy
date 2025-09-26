#!/usr/bin/env python3
"""
Test script for the new IRNetBox import functionality
Replaces the old XML import system with IRNetBox txt format import

Usage: python3 test_irnetbox_import.py [irnetbox_file.txt]
"""

import sys
import os
import tempfile

def test_irnetbox_detection():
    """Test IRNetBox format detection"""
    print("🔍 Testing IRNetBox format detection...")
    
    # Import the detection function
    from app.services.remote_service import parse_irnetbox_file
    def detect_irnetbox_format(filepath):
        try:
            parse_irnetbox_file(filepath)
            return True
        except:
            return False
    
    # Create a temporary test file with IRNetBox format
    test_content = """Device Humax HDR-FOX T2

Signal data as IRNetBox data blocks

POWER   DMOD_SIG   signal1 16 0000BE8C0117D900060C050C050C050C050C050C050C050C050C050C050C
GUIDE   MOD_SIG    8 050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        result = detect_irnetbox_format(test_file)
        print(f"   ✅ IRNetBox format detection: {result}")
        return result
    finally:
        os.unlink(test_file)

def test_irnetbox_parsing():
    """Test IRNetBox file parsing"""
    print("🔍 Testing IRNetBox parsing...")
    
    from remoteservice_txt import parse_irnetbox_file
    
    # Create a temporary test file with IRNetBox format
    test_content = """Device Humax HDR-FOX T2

Signal data as IRNetBox data blocks

POWER   DMOD_SIG   signal1 16 0000BE8C0117D900060C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C
POWER   DMOD_SIG   signal2 16 0000BE8C0117D900060C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C
GUIDE   MOD_SIG    8 050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C
UP      MOD_SIG    8 050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        device_name, signals = parse_irnetbox_file(test_file)
        print(f"   ✅ Device Name: {device_name}")
        print(f"   ✅ Signals Found: {len(signals)}")
        for signal_name, signal_data in signals.items():
            print(f"      - {signal_name}: {signal_data['sig_type']} (freq: {signal_data['frequency']}Hz)")
        return device_name, signals
    finally:
        os.unlink(test_file)

def test_template_data_creation():
    """Test creating template data from signal info"""
    from app.services.remote_service import parse_irnetbox_file
    # Note: create_template_data is now internal to the service - test via full import
    
    # Create a temporary test file
    test_content = """Device Test Remote

Signal data as IRNetBox data blocks

POWER   DMOD_SIG   signal1 16 0000BE8C0117D900060C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C
GUIDE   MOD_SIG    8 050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C050C
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        device_name, signals = parse_irnetbox_file(test_file)
        
        # Test template data creation
        for signal_name, signal_info in signals.items():
            template_data = create_template_data(signal_name, signal_info)
            print(f"   ✅ Template created for {signal_name}: {len(template_data)} chars")
        
        return True
    except Exception as e:
        print(f"   ❌ Import test failed: {e}")
        return False
    finally:
        os.unlink(test_file)

def test_service_import():
    """Test the service layer import"""
    print("🔍 Testing service layer import...")
    
    try:
        from app.services.remote_service import import_remotes_from_irnetbox
        print("   ✅ IRNetBox import function available")
        return True
    except ImportError as e:
        print(f"   ❌ Could not import IRNetBox function: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Service import test failed: {e}")
        return False

def test_xml_deprecation():
    """Test that XML functions are properly deprecated"""
    print("🔍 Testing XML deprecation...")
    
    try:
        from app.services.remote_service import import_remotes_from_xml
        try:
            import_remotes_from_xml('test.xml', 1)
            print("   ❌ XML function should have raised deprecation error")
            return False
        except Exception as e:
            if "deprecated" in str(e).lower():
                print("   ✅ XML function properly deprecated")
                return True
            else:
                print(f"   ❌ Unexpected error: {e}")
                return False
    except ImportError as e:
        print(f"   ❌ Could not import deprecated XML function: {e}")
        return False

def main():
    print("🚀 Testing IRNetBox Import Migration")
    print("=" * 50)
    
    tests = [
        ("IRNetBox Detection", test_irnetbox_detection),
        ("IRNetBox Parsing", test_irnetbox_parsing),
        ("Import Functionality", test_import_functionality),
        ("Service Layer", test_service_import),
        ("XML Deprecation", test_xml_deprecation)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n" + "=" * 50)
    print("🏁 Test Results:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! IRNetBox import migration is successful.")
        print("\n📝 Next steps:")
        print("   1. Test with a real IRNetBox .txt file")
        print("   2. Verify the web interface accepts .txt files")
        print("   3. Check database entries after import")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    # If a file is provided as argument, test with that file
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if os.path.exists(test_file):
            print(f"🔍 Testing with provided file: {test_file}")
            try:
                from app.services.remote_service import import_remotes_from_irnetbox
                # Note: This would require a user_id, so we'll just test parsing
                from app.services.remote_service import parse_irnetbox_file
                
                device_name, signals = parse_irnetbox_file(test_file)
                print(f"✅ File parsed successfully:")
                print(f"   Device: {device_name}")
                print(f"   Signals: {len(signals)}")
                for signal_name in signals.keys():
                    print(f"      - {signal_name}")
            except Exception as e:
                print(f"❌ Error parsing file: {e}")
        else:
            print(f"❌ File not found: {test_file}")
    
    # Run standard tests
    sys.exit(main())