import os
import uuid
from werkzeug.utils import secure_filename
from app.database import get_db
from app.utils.logger import logger
from app.config import Config
from app.models.irdb import IRDBFile

def upload_irdb_file(file):
    if not file.filename.endswith('.irdb'):
        raise ValueError("Only .irdb files are accepted")
    
    file_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    filepath = os.path.join(Config.UPLOAD_FOLDER, 'irdb', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO irdb_files 
            (id, filename, filepath) 
            VALUES (%s, %s, %s)
        """, (file_id, filename, filepath))
        conn.commit()
    
    logger.info(f"Uploaded IRDB file: {filename}")
    return filename

def get_irdb_files():
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM irdb_files")
        rows = cursor.fetchall()
        return [IRDBFile.from_db_row(row) for row in rows]