#!/usr/bin/env python3
"""
Signal Library Sync Checker
Compares database signal templates with captured traffic to find discrepancies
"""

import sys
import os
import json
import binascii

# Add app to path
sys.path.insert(0, '/home/svdleer/redrat-proxy')

def get_database_signal():
    """Get the POWER signal from database"""
    import mysql.connector
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            database='redrat_proxy',
            user='redrat',
            password='Clad6DytmucAr'
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT template_data FROM command_templates WHERE name = 'POWER_signal1'")
        result = cursor.fetchone()
        
        if result:
            template_json = json.loads(result[0])
            signal_hex = template_json['signal_data']
            signal_bytes = binascii.unhexlify(signal_hex)
            return signal_bytes, template_json
        
        return None, None
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None, None
    finally:
        if 'connection' in locals():
            connection.close()

def analyze_captured_signals():
    """Read and analyze the captured signal files"""
    try:
        with open('original_ir_signals.bin', 'rb') as f:
            original_data = f.read()
            
        with open('proxy_ir_signals.bin', 'rb') as f:
            proxy_data = f.read()
            
        # Remove the comment headers that were added
        original_clean = original_data.split(b'\n\n')[0]
        if original_clean.startswith(b'# IR Signal'):
            original_clean = original_data.split(b'\n', 1)[1].split(b'\n\n')[0]
            
        proxy_clean = proxy_data.split(b'\n\n')[0]
        if proxy_clean.startswith(b'# IR Signal'):
            proxy_clean = proxy_data.split(b'\n', 1)[1].split(b'\n\n')[0]
            
        return original_clean, proxy_clean
        
    except Exception as e:
        print(f"❌ Error reading signal files: {e}")
        return None, None

def compare_signals(db_signal, db_template, original_signal, proxy_signal):
    """Compare all three signal sources"""
    
    print("🔍 SIGNAL LIBRARY SYNC ANALYSIS")
    print("="*60)
    print()
    
    print("📊 SIGNAL LENGTHS:")
    print(f"  Database Template: {len(db_signal)} bytes")
    print(f"  Original Capture:  {len(original_signal)} bytes")
    print(f"  Proxy Capture:     {len(proxy_signal)} bytes")
    print()
    
    print("🔍 SIGNAL HEADERS (first 32 bytes):")
    print(f"  Database: {db_signal[:32].hex()}")
    print(f"  Original: {original_signal[:32].hex()}")
    print(f"  Proxy:    {proxy_signal[:32].hex()}")
    print()
    
    print("🔍 SIGNAL TAILS (last 32 bytes):")
    print(f"  Database: {db_signal[-32:].hex()}")
    print(f"  Original: {original_signal[-32:].hex()}")
    print(f"  Proxy:    {proxy_signal[-32:].hex()}")
    print()
    
    # Compare database vs original
    db_vs_orig_match = sum(1 for i in range(min(len(db_signal), len(original_signal))) 
                          if db_signal[i] == original_signal[i])
    db_vs_orig_pct = (db_vs_orig_match / min(len(db_signal), len(original_signal))) * 100
    
    # Compare database vs proxy
    db_vs_proxy_match = sum(1 for i in range(min(len(db_signal), len(proxy_signal))) 
                           if db_signal[i] == proxy_signal[i])
    db_vs_proxy_pct = (db_vs_proxy_match / min(len(db_signal), len(proxy_signal))) * 100
    
    # Compare original vs proxy
    orig_vs_proxy_match = sum(1 for i in range(min(len(original_signal), len(proxy_signal))) 
                             if original_signal[i] == proxy_signal[i])
    orig_vs_proxy_pct = (orig_vs_proxy_match / min(len(original_signal), len(proxy_signal))) * 100
    
    print("📈 SIMILARITY ANALYSIS:")
    print(f"  Database ↔ Original: {db_vs_orig_pct:.1f}% ({db_vs_orig_match}/{min(len(db_signal), len(original_signal))} bytes)")
    print(f"  Database ↔ Proxy:    {db_vs_proxy_pct:.1f}% ({db_vs_proxy_match}/{min(len(db_signal), len(proxy_signal))} bytes)")
    print(f"  Original ↔ Proxy:    {orig_vs_proxy_pct:.1f}% ({orig_vs_proxy_match}/{min(len(original_signal), len(proxy_signal))} bytes)")
    print()
    
    print("🔬 DATABASE TEMPLATE INFO:")
    print(f"  UID: {db_template.get('uid', 'N/A')}")
    print(f"  Command: {db_template.get('command', 'N/A')}")
    print(f"  Remote ID: {db_template.get('remote_id', 'N/A')}")
    print(f"  Modulation Freq: {db_template.get('modulation_freq', 'N/A')} Hz")
    print(f"  No Repeats: {db_template.get('no_repeats', 'N/A')}")
    print(f"  Max Lengths: {db_template.get('max_lengths', 'N/A')}")
    print()
    
    # Diagnosis
    print("🎯 DIAGNOSIS:")
    print("="*40)
    
    if abs(len(db_signal) - len(original_signal)) > 50:
        print("❌ Database and original signals have very different lengths")
        print("   → Signal templates may be from different source")
        
    if db_vs_orig_pct > 90:
        print("✅ Database and original signals match well")
        print("   → Original system uses database correctly")
    elif db_vs_orig_pct > 50:
        print("⚠️  Database and original signals partially match")
        print("   → Some signal processing differences")
    else:
        print("❌ Database and original signals don't match")
        print("   → Different signal sources or major processing differences")
        
    if db_vs_proxy_pct > 90:
        print("✅ Database and proxy signals match well")
        print("   → Proxy uses database correctly")
    elif db_vs_proxy_pct > 50:
        print("⚠️  Database and proxy signals partially match")
        print("   → Proxy has some signal processing issues")
    else:
        print("❌ Database and proxy signals don't match")
        print("   → Proxy has major signal processing problems")
        
    if orig_vs_proxy_pct < 50:
        print("❌ Original and proxy signals are very different")
        if db_vs_orig_pct > db_vs_proxy_pct:
            print("   → Proxy signal processing is broken")
        elif db_vs_proxy_pct > db_vs_orig_pct:
            print("   → Original capture may not be from same command")
        else:
            print("   → Both systems may have different signal sources")

def main():
    print("🔧 Signal Library Sync Checker")
    print("="*50)
    print("Comparing database templates with captured traffic")
    print()
    
    # Get database signal
    print("📚 Reading database signal template...")
    db_signal, db_template = get_database_signal()
    if not db_signal:
        print("❌ Failed to get database signal")
        return
    
    print(f"✅ Database signal loaded: {len(db_signal)} bytes")
    
    # Get captured signals
    print("📡 Reading captured signal files...")
    original_signal, proxy_signal = analyze_captured_signals()
    if not original_signal or not proxy_signal:
        print("❌ Failed to read captured signals")
        return
        
    print(f"✅ Original signal loaded: {len(original_signal)} bytes")
    print(f"✅ Proxy signal loaded: {len(proxy_signal)} bytes")
    print()
    
    # Compare all signals
    compare_signals(db_signal, db_template, original_signal, proxy_signal)
    
    print()
    print("💡 RECOMMENDATIONS:")
    print("="*50)
    print("1. If database ↔ original match is low: Check if original uses same DB")
    print("2. If database ↔ proxy match is low: Fix proxy signal conversion")
    print("3. If all matches are low: Verify we're comparing same commands")
    print("4. Check modulation frequency and signal formatting differences")

if __name__ == "__main__":
    main()