#!/usr/bin/env python3
"""
Test XML import functionality
"""

import sys
import os
import logging

# Add the app directory to Python path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_xml_import():
    """Test importing an XML file"""
    try:
        from app.services.remote_service import import_remotes_from_xml
        
        xml_file = "/home/svdleer/redrat-proxy/test_remote.xml"
        
        if not os.path.exists(xml_file):
            logger.error(f"XML file not found: {xml_file}")
            return False
            
        logger.info(f"Testing XML import from: {xml_file}")
        
        # Test the import
        imported_count = import_remotes_from_xml(xml_file, user_id=1)
        
        logger.info(f"Import successful! Imported {imported_count} remotes")
        return True
        
    except Exception as e:
        logger.error(f"XML import failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing XML Import Functionality")
    print("===================================")
    
    success = test_xml_import()
    
    if success:
        print("✅ XML import test passed!")
    else:
        print("❌ XML import test failed!")
        sys.exit(1)