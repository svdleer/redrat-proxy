import os
import uuid
import logging

# Try to import necessary modules, with fallbacks for testing/standalone use
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
except ImportError:
    # For standalone testing
    db = None

# Define IRDBService class for compatibility with existing code
class IRDBService:
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
        
        file.save(f"app/{filepath}")
        
        if db:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if file already exists
                cursor.execute("SELECT id FROM remote_files WHERE filename = %s", (filename,))
                result = cursor.fetchone()
                
                if result:
                    file_id = result[0]
                    logger.info(f"Remote file '{filename}' already exists with ID {file_id}")
                else:
                    cursor.execute(
                        """INSERT INTO remote_files 
                           (name, filename, filepath, uploaded_by) 
                           VALUES (%s, %s, %s, %s)""",
                        (filename, filename, filepath, user_id)
                    )
                    file_id = cursor.lastrowid
                    conn.commit()
                    logger.info(f"Created new remote file '{filename}' with ID {file_id}")
        
        logger.info(f"Uploaded remote XML file: {filename}")
        return f"app/{filepath}"

def get_irdb_files():
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM irdb_files")
        rows = cursor.fetchall()
        return [IRDBFile.from_db_row(row) for row in rows]