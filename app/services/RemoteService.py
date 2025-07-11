import os
import logging
import xml.etree.ElementTree as ET
import json
from datetime import datetime

# Try to import necessary modules with fallbacks for testing
try:
    from werkzeug.utils import secure_filename
except ImportError:
    def secure_filename(filename):
        return filename.replace(' ', '_')

try:
    from app.utils.logger import logger
except ImportError:
    logger = logging.getLogger("redrat")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

try:
    from app.mysql_db import db
    from app.services.remote_service import parse_remotes_xml, import_remotes_to_db
except ImportError:
    db = None

class RemoteService:
    """Service for handling remote XML files - replaces the old IRDB functionality"""
    
    @staticmethod
    def upload_remote_file(file, user_id):
        """Upload an XML file containing remote data"""
        if not file.filename.endswith('.xml'):
            raise ValueError("Only .xml files are accepted")
        
        filename = secure_filename(file.filename)
        filepath = f"static/remote_files/{filename}"
        
        # Make sure the directory exists
        os.makedirs("app/static/remote_files", exist_ok=True)
        
        # Save the file
        file_path = f"app/{filepath}"
        file.save(file_path)
        
        try:
            # Parse and import remote data
            from app.services.remote_service import parse_remotes_xml, import_remotes_to_db
            remotes = parse_remotes_xml(file_path)
            
            if not remotes:
                logger.warning(f"No valid remotes found in {filename}")
                return 0
                
            imported_count = import_remotes_to_db(remotes, user_id)
            return imported_count
            
        except Exception as e:
            logger.error(f"Error importing XML: {str(e)}")
            raise
        
    @staticmethod
    def get_remote_files():
        """Get all remote files from the database"""
        if not db:
            return []
            
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM remote_files")
            return cursor.fetchall()
    
    @staticmethod
    def get_remote_file(file_id):
        """Get a specific remote file by ID"""
        if not db:
            return None
            
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM remote_files WHERE id = %s", (file_id,))
            return cursor.fetchone()
    
    @staticmethod
    def delete_remote_file(file_id):
        """Delete a remote file"""
        if not db:
            return False
            
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the filepath first
            cursor.execute("SELECT filepath FROM remote_files WHERE id = %s", (file_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
                
            filepath = result[0]
            
            # Delete the file record
            cursor.execute("DELETE FROM remote_files WHERE id = %s", (file_id,))
            conn.commit()
            
            # Delete the actual file if it exists
            full_path = f"app/{filepath}"
            if os.path.exists(full_path):
                os.remove(full_path)
                
            return True
