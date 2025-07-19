"""
API Key model for managing API access tokens
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.mysql_db import db
from app.utils.logger import logger


class APIKey:
    """API Key model for managing API access tokens."""
    
    def __init__(self, id: int = None, name: str = None, key_hash: str = None, 
                 user_id: int = None, expires_at: datetime = None, 
                 is_active: bool = True, created_at: datetime = None):
        self.id = id
        self.name = name
        self.key_hash = key_hash
        self.user_id = user_id
        self.expires_at = expires_at
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new API key."""
        return f"rr_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def create_key(name: str, user_id: int, expires_days: int = 365) -> tuple[str, 'APIKey']:
        """Create a new API key and return the key and APIKey object."""
        key = APIKey.generate_key()
        key_hash = APIKey.hash_key(key)
        
        # Ensure expires_days is an integer
        if isinstance(expires_days, str):
            expires_days = int(expires_days)
        
        expires_at = datetime.now() + timedelta(days=expires_days)
        
        api_key = APIKey(
            name=name,
            key_hash=key_hash,
            user_id=user_id,
            expires_at=expires_at
        )
        
        if api_key.save():
            return key, api_key
        else:
            return None, None
    
    @staticmethod
    def get_by_id(api_key_id: int) -> Optional['APIKey']:
        """Get API key by ID."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM api_keys WHERE id = %s", (api_key_id,))
                row = cursor.fetchone()
                
                if row:
                    return APIKey(
                        id=row['id'],
                        name=row['name'],
                        key_hash=row['key_hash'],
                        user_id=row['user_id'],
                        expires_at=row['expires_at'],
                        is_active=row['is_active'],
                        created_at=row['created_at']
                    )
        except Exception as e:
            logger.error(f"Error getting API key {api_key_id}: {str(e)}")
        
        return None
    
    @staticmethod
    def get_by_key(key: str) -> Optional['APIKey']:
        """Get API key by key value."""
        try:
            key_hash = APIKey.hash_key(key)
            with db.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT * FROM api_keys 
                    WHERE key_hash = %s AND is_active = TRUE 
                    AND (expires_at IS NULL OR expires_at > NOW())
                """, (key_hash,))
                row = cursor.fetchone()
                
                if row:
                    return APIKey(
                        id=row['id'],
                        name=row['name'],
                        key_hash=row['key_hash'],
                        user_id=row['user_id'],
                        expires_at=row['expires_at'],
                        is_active=row['is_active'],
                        created_at=row['created_at']
                    )
        except Exception as e:
            logger.error(f"Error getting API key by key: {str(e)}")
        
        return None
    
    @staticmethod
    def get_by_user(user_id: int) -> List['APIKey']:
        """Get all API keys for a user."""
        keys = []
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT * FROM api_keys 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC
                """, (user_id,))
                rows = cursor.fetchall()
                
                for row in rows:
                    keys.append(APIKey(
                        id=row['id'],
                        name=row['name'],
                        key_hash=row['key_hash'],
                        user_id=row['user_id'],
                        expires_at=row['expires_at'],
                        is_active=row['is_active'],
                        created_at=row['created_at']
                    ))
        except Exception as e:
            logger.error(f"Error getting API keys for user {user_id}: {str(e)}")
        
        return keys
    
    def save(self) -> bool:
        """Save the API key to database (insert only - updates not allowed)."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.id:
                    # API keys cannot be updated once created
                    logger.warning(f"Attempt to update API key {self.id} - this is not allowed")
                    return False
                else:
                    # Insert new key
                    cursor.execute("""
                        INSERT INTO api_keys (name, key_hash, user_id, expires_at, is_active)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (self.name, self.key_hash, self.user_id, self.expires_at, self.is_active))
                    
                    self.id = cursor.lastrowid
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error saving API key: {str(e)}")
            return False
    
    def delete(self) -> bool:
        """Delete the API key."""
        if not self.id:
            return False
            
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM api_keys WHERE id = %s", (self.id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting API key {self.id}: {str(e)}")
            return False
    
    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert API key to dictionary (without sensitive data)."""
        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_expired': self.is_expired(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
