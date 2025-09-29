#!/usr/bin/env python3
"""
Quick fix: Recreate the working remote and command template data
"""

import mysql.connector
import json
import base64

def recreate_working_data():
    """Recreate the working remote and command data"""
    
    # Database connection
    conn = mysql.connector.connect(
        host='localhost',
        user='redrat',
        password='Clad6DytmucAr',
        database='redrat_proxy'
    )
    cursor = conn.cursor()
    
    try:
        print("🔄 Recreating working remote data...")
        
        # 1. Create the remote_files entries
        cursor.execute("""
            INSERT INTO remote_files (id, name, filename, filepath, device_type, uploaded_by, uploaded_at)
            VALUES (11, 'Humax', 'Humax.xml', 'static/remote_files/Humax.xml', 'PVR', 1, NOW())
            ON DUPLICATE KEY UPDATE name=VALUES(name)
        """)
        
        # 2. Create the remotes entries
        cursor.execute("""
            INSERT INTO remotes (id, name, manufacturer, device_model_number, device_type, description, created_by, created_at)
            VALUES (16, 'Humax', 'Humax', 'PVR-9150T', 'PVR', 'Humax PVR Remote Control', 1, NOW())
            ON DUPLICATE KEY UPDATE name=VALUES(name)
        """)
        
        # 3. Create the working POWER command template
        working_template = {
            "uid": "RgTVkXKDn0C7hK9giKnH9Q==",
            "command": "POWER", 
            "lengths": [8.878, 4.535, 0.544, 1.7145, 0.6315, 1.418, 0.118, 0.1115, 0.1155, 0.0745, 0.326, 0.003, 0.134, 0.0825, 0.0165, 0.009, 0.005, 0.1155, 0.048, 0.0565, 0.0745, 0.0755, 0.1095, 2.3035],
            "remote_id": 16,
            "no_repeats": 2,
            "signal_data": "AAECAgICAgICAgICAgICAgICAgICAgICAgICAwICAgICAgICAgICAgICAgICAgIEAgICAwIDAgMCAwIDAgMCAwIDAn8FBgcIAgkKCwwNBA4CDwIQERITFAoVFhYWFgoWFhYWFgoWFhYWFhYWDBYWFgoWDBYWFhYWFhYMFhYWFhcCfw==",
            "toggle_data": [],
            "intra_sig_pause": 47.5215,
            "modulation_freq": "38350"
        }
        
        cursor.execute("""
            INSERT INTO command_templates (id, file_id, name, device_type, template_data, created_by, created_at)
            VALUES (223, 11, 'POWER', 'PVR', %s, 1, NOW())
            ON DUPLICATE KEY UPDATE template_data=VALUES(template_data)
        """, (json.dumps(working_template),))
        
        conn.commit()
        print("✅ Working remote data recreated successfully!")
        
        # Verify the data
        cursor.execute("SELECT COUNT(*) FROM remotes")
        remote_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM command_templates")
        template_count = cursor.fetchone()[0]
        
        print(f"📊 Database status:")
        print(f"   - Remotes: {remote_count}")
        print(f"   - Command templates: {template_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error recreating data: {e}")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🛠️  Quick Fix: Recreating Working Data")
    print("=====================================")
    
    success = recreate_working_data()
    
    if success:
        print("🎉 Success! You should now be able to send working IR commands via the GUI.")
        print("💡 Try sending a POWER command through the web interface - it should work now!")
    else:
        print("❌ Failed to recreate working data.")