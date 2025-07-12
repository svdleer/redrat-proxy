"""
IRDB File Model
"""
import uuid
from datetime import datetime

class IRDBFile:
    def __init__(self, id=None, filename=None, filepath=None, uploaded_at=None):
        self.id = id or str(uuid.uuid4())
        self.filename = filename
        self.filepath = filepath
        self.uploaded_at = uploaded_at or datetime.now()
    
    @classmethod
    def from_db_row(cls, row):
        """Create an IRDBFile from a database row"""
        if not row:
            return None
        
        return cls(
            id=row['id'],
            filename=row['filename'],
            filepath=row['filepath'],
            uploaded_at=row['uploaded_at']
        )

    def to_dict(self):
        """Convert to a dictionary for API responses"""
        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': self.filepath,
            'uploaded_at': self.uploaded_at.isoformat() if isinstance(self.uploaded_at, datetime) else self.uploaded_at
        }
