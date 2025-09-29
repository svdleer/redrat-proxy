#!/usr/bin/env python3
import os
import sys
sys.path.append('app')
os.chdir('app')

try:
    from mysql_db import db
    print("✓ Database module imported successfully")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        print("✓ Database connection established")
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) FROM remotes")
        remote_count = cursor.fetchone()[0]
        print(f"✓ Remotes in database: {remote_count}")
        
        cursor.execute("SELECT COUNT(*) FROM command_templates")
        template_count = cursor.fetchone()[0]
        print(f"✓ Templates in database: {template_count}")
        
        cursor.execute("SELECT COUNT(*) FROM remote_files")
        file_count = cursor.fetchone()[0]
        print(f"✓ Remote files in database: {file_count}")
        
        # Test insert permissions
        cursor.execute("INSERT INTO remotes (name, manufacturer, device_type, description) VALUES ('TEST_REMOTE', 'TEST_MFG', 'TEST_TYPE', 'TEST_DESC')")
        test_remote_id = cursor.lastrowid
        print(f"✓ Test remote created with ID: {test_remote_id}")
        
        # Clean up
        cursor.execute("DELETE FROM remotes WHERE id = %s", (test_remote_id,))
        conn.commit()
        print("✓ Test remote cleaned up")
        
except Exception as e:
    print(f"✗ Database error: {e}")
    import traceback
    traceback.print_exc()
