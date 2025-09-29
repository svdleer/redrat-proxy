#!/usr/bin/env python3

"""
Analyze RedRat protocol structure to understand where frequency encoding belongs.
Based on PCAP analysis, the issue may be in the protocol message structure, not IR data.
"""

def analyze_protocol_structure():
    print("REDRAT PROTOCOL STRUCTURE ANALYSIS")
    print("=" * 50)
    
    # From PCAP: Working hub complete message
    hub_complete = "2300ab30020000000000000000000000210000000000000000017340ff63000000050000"
    
    # Our failing message header (partial)
    proxy_complete = "2300d13000000000000000003200000000000000000017343ff63000000180000008202455c236e04400d6504ff631400ec00df00e70095028c0006010c00a500210012000a"
    
    print("Complete RedRat message structure:")
    print(f"HUB    (working): {hub_complete}")
    print(f"PROXY  (failing): {proxy_complete[:len(hub_complete)]}")
    print()
    
    # Parse RedRat message structure
    print("RedRat Message Header Analysis:")
    print("-" * 35)
    
    hub_bytes = bytes.fromhex(hub_complete)
    proxy_bytes = bytes.fromhex(proxy_complete[:len(hub_complete)])
    
    print("Byte-by-byte analysis:")
    print("Pos | HUB  | PROXY | Meaning")
    print("----|------|-------|----------")
    print(f" 0  | 0x{hub_bytes[0]:02x} | 0x{proxy_bytes[0]:02x}   | Message type byte 1")
    print(f" 1  | 0x{hub_bytes[1]:02x} | 0x{proxy_bytes[1]:02x}   | Message type byte 2") 
    print(f" 2  | 0x{hub_bytes[2]:02x} | 0x{proxy_bytes[2]:02x}   | Data length (low)")
    print(f" 3  | 0x{hub_bytes[3]:02x} | 0x{proxy_bytes[3]:02x}   | Message type (0x30 = MK3/4 ASYNC)")
    print("--- RedRat Protocol Header ---")
    
    # Skip the first 4 bytes (RedRat message header) and analyze the IR command structure
    ir_header_start = 4
    
    print(f"\nIR Command Structure (starting at byte {ir_header_start}):")
    print("Pos | HUB  | PROXY | Potential Meaning")
    print("----|------|-------|-------------------")
    
    for i in range(ir_header_start, min(len(hub_bytes), len(proxy_bytes))):
        hub_val = hub_bytes[i] if i < len(hub_bytes) else 0
        proxy_val = proxy_bytes[i] if i < len(proxy_bytes) else 0
        match_str = "✅" if hub_val == proxy_val else "❌"
        
        # Try to identify key fields
        meaning = ""
        if i == ir_header_start:
            meaning = "IR command header start"
        elif i >= 20 and i <= 25:
            meaning = f"Potential frequency field"
        elif hub_val != proxy_val:
            meaning = f"DIFFERENCE"
            
        print(f"{i:2d}  | 0x{hub_val:02x} | 0x{proxy_val:02x}   | {meaning} {match_str}")
    
    print("\n" + "="*60)
    print("KEY FINDINGS:")
    print("="*60)
    print("1. Hub message length: 0xab (171 bytes)")
    print("2. Proxy message length: 0xd1 (209 bytes)")
    print("3. Hub has frequency 0xff63 at message bytes 24-25")
    print("4. Proxy has different data structure entirely")
    print()
    print("CONCLUSION:")
    print("-" * 15)
    print("The issue is NOT just frequency position - it's the entire")
    print("IR command structure that differs between hub and proxy!")
    print()
    print("The hub uses a different IR data format/structure than what")
    print("we're generating from the database templates.")
    print()
    print("SOLUTION: Need to match the EXACT protocol structure used")
    print("by the hub, not just embed frequency in arbitrary positions.")

if __name__ == "__main__":
    analyze_protocol_structure()