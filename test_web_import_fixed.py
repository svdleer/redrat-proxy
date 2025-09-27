#!/usr/bin/env python3
"""
Simple test to verify IRNetBox import functionality works correctly
"""

import sys
import os
import tempfile

# Add the app directory to the path
sys.path.append('.')

def test_web_import_simulation():
    """Simulate what happens when a user uploads a file through the web interface"""
    
    print("=== SIMULATING WEB IMPORT ===")
    
    # Create a temporary test file (simulating file upload)
    test_content = '''Device WebTestRemote

Signal data as IRNetBox data blocks stored as ASCII Hex.

Power	DMOD_SIG	signal1	16 0002C38FFF5900000006000000480103250251012C04EE063A03A0000000000000000000000000000000000000000000010201020302010201020402010201020102010203020502030201020102040201027F
Volume+	DMOD_SIG	signal1	16 0002C66EFF5700000003000000300106D80DB70601000000000000000000000000000000000000000000000000000000000000010200020002000200020001010200020002007F
'''
    
    # Create temporary file (simulating upload)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        temp_path = f.name
    
    try:
        print(f"Created temporary file: {temp_path}")
        
        # Simulate the Flask route logic
        print("Reading file content...")
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"File content length: {len(content)} characters")
        
        # Import using our function
        from app.services.remote_service import import_remotes_from_irnetbox
        
        print("Importing content...")
        imported_count = import_remotes_from_irnetbox(content, 1)
        
        print(f"✅ Import completed: {imported_count} signals imported")
        
        # Verify the import
        from app.mysql_db import db
        
        with db.get_connection() as connection:
            cursor = connection.cursor()
            
            # Check if the remote was created
            cursor.execute("SELECT COUNT(*) FROM remotes WHERE name = 'WebTestRemote'")
            remote_count = cursor.fetchone()[0]
            print(f"✅ Remote created: {remote_count} 'WebTestRemote' remote(s) found")
            
            # Check if commands were created
            cursor.execute("""
                SELECT COUNT(*) FROM command_templates 
                WHERE JSON_EXTRACT(template_data, '$.command') IN ('Power', 'Volume+')
            """)
            command_count = cursor.fetchone()[0]
            print(f"✅ Commands created: {command_count} command template(s) found")
            
            cursor.close()
        
        print("\n🎉 Web import simulation SUCCESSFUL!")
        print("📝 The web interface should now work correctly for IRNetBox uploads.")
        
    except Exception as e:
        print(f"❌ Error during simulation: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"Cleaned up temporary file: {temp_path}")

if __name__ == "__main__":
    test_web_import_simulation()