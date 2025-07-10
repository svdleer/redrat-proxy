import os
from werkzeug.utils import secure_filename
from app.database import get_db
from app.utils.logger import logger
from app.config import Config

def upload_irdb_file(file):
    if not file.filename.endswith('.irdb'):
        raise ValueError("Only .irdb files are accepted")
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(Config.UPLOAD_FOLDER, 'irdb', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO irdb_files 
            (filename, filepath) 
            VALUES (%s, %s)
        """, (filename, filepath))
        conn.commit()
    
    logger.info(f"Uploaded IRDB file: {filename}")
    return filename

def get_irdb_files():
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM irdb_files")
        return cursor.fetchall()