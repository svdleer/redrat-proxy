"""
Remote File Model
"""
import uuid
from datetime import datetime

class RemoteFile:
    def __init__(self, id=None, name=None, filename=None, filepath=None, 
                 device_type=None, manufacturer=None, uploaded_by=None, uploaded_at=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.filename = filename
        self.filepath = filepath
        self.device_type = device_type
        self.manufacturer = manufacturer
        self.uploaded_by = uploaded_by
        self.uploaded_at = uploaded_at or datetime.now()
    
    @classmethod
    def from_db_row(cls, row):
        """Create a RemoteFile from a database row"""
        if not row:
            return None
        
        return cls(
            id=row['id'],
            name=row['name'],
            filename=row['filename'],
            filepath=row['filepath'],
            device_type=row.get('device_type'),
            manufacturer=row.get('manufacturer'),
            uploaded_by=row['uploaded_by'],
            uploaded_at=row['uploaded_at']
        )

    def to_dict(self):
        """Convert to a dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'filename': self.filename,
            'filepath': self.filepath,
            'device_type': self.device_type,
            'manufacturer': self.manufacturer,
            'uploaded_by': self.uploaded_by,
            'uploaded_at': self.uploaded_at.isoformat() if isinstance(self.uploaded_at, datetime) else self.uploaded_at
        }
