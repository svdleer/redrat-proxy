#!/usr/bin/env python3
"""
Test the database signal data directly to see if it works
"""

import sys
sys.path.append('/home/svdleer/redrat-proxy')
from irnetbox_lib_new import IRNetBox, IRSignal, PowerLevel

def test_database_signal():
    """Test the signal data that comes from the database"""
    print("🧪 Testing DATABASE signal (what API uses)")
    print("=" * 50)
    
    # This is the signal data from the database (POWER_signal1)
    db_signal_hex = "00017343FF63000000180000008202455C236E04400D6504EF0B1400EC00DF00E70095028C0006010C00A500210012000A00E7006000710095009700DB11FF000102020202020202020202020202020202020202020202020202030202020202020202020202020202020202020204020202030203020302030203020302030203027F0506070802090A0B0C0D040E020F0210111213140A15161616160A16161616160A161616161616160C1616160A160C161616161616160C1616161617027F"
    
    db_signal = IRSignal(
        name='POWER_DATABASE',
        uid='power_db_test',
        modulation_freq=38238,  # From database
        lengths=[],
        sig_data=bytes.fromhex(db_signal_hex),
        no_repeats=1,
        intra_sig_pause=0.0
    )

    print(f"📊 Database signal:")
    print(f"  Frequency: {db_signal.modulation_freq}Hz")
    print(f"  Data size: {len(db_signal.sig_data)} bytes")
    print(f"  Data starts: {db_signal.sig_data[:20].hex()}")
    
    try:
        irnetbox = IRNetBox()
        print("🔌 Connecting to IRNetBox at 172.16.6.62...")
        
        if not irnetbox.connect("172.16.6.62"):
            print("❌ Connection failed")
            return False
            
        print("✅ Connected!")
        
        print("📡 Sending DATABASE signal...")
        result = irnetbox.send_signal_robust(
            signal=db_signal,
            port=9,
            power_level=PowerLevel.HIGH,
            max_retries=1
        )
        
        if result['success']:
            print(f"✅ Database signal sent successfully in {result['total_time']:.2f}s")
            success = True
        else:
            print(f"❌ Database signal failed: {result['error']}")
            success = False
        
        irnetbox.disconnect()
        print("🔌 Disconnected")
        
        return success
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_database_signal()
    print(f"\n🎯 Result: {'DATABASE SIGNAL WORKS' if success else 'DATABASE SIGNAL FAILS'}")