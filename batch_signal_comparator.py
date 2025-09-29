#!/usr/bin/env python3
"""
Batch Signal Comparator - Check multiple PCAP files for IR signals  
"""

import os
import sys
import glob

# Add app to path
sys.path.insert(0, '/home/svdleer/redrat-proxy')

# Import our signal comparator functions
from signal_comparator import extract_redrat_signals_from_pcap, analyze_redrat_signals

def find_best_original_pcap():
    """Find the original PCAP with the most IR signals"""
    print("🔍 Scanning all original PCAP files for IR signals...")
    
    pcap_files = glob.glob("/home/svdleer/redrat_proxy_old/*.pcap")
    pcap_files.sort(key=lambda x: os.path.getsize(x), reverse=True)  # Sort by size, largest first
    
    best_file = None
    best_ir_count = 0
    
    for pcap_file in pcap_files[:10]:  # Check top 10 largest files
        file_size = os.path.getsize(pcap_file)
        if file_size < 1000:  # Skip tiny files (likely empty)
            continue
            
        print(f"\n📁 {os.path.basename(pcap_file)} ({file_size:,} bytes)")
        
        try:
            signals = extract_redrat_signals_from_pcap(pcap_file, "TEST")
            analysis = analyze_redrat_signals(signals, "TEST")
            ir_count = len(analysis.get('ir_signals', []))
            
            print(f"   IR signals: {ir_count}")
            
            if ir_count > best_ir_count:
                best_file = pcap_file
                best_ir_count = ir_count
                print(f"   ⭐ New best candidate!")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return best_file, best_ir_count

def main():
    print("🔍 Batch Signal Comparator")
    print("="*50)
    
    # Find best original PCAP
    best_original, ir_count = find_best_original_pcap()
    
    if not best_original:
        print("❌ No original PCAP files with IR signals found!")
        return
    
    print(f"\n🎯 BEST ORIGINAL PCAP: {os.path.basename(best_original)} ({ir_count} IR signals)")
    
    # Run full comparison with best file
    print(f"\n🔄 Running full comparison...")
    
    # Import and run main comparator
    from signal_comparator import main as run_comparator
    
    # Temporarily modify the original file path
    import signal_comparator
    signal_comparator.original_pcap = best_original
    
    # Run comparison
    run_comparator()

if __name__ == "__main__":
    main()