# -*- coding: utf-8 -*-

"""RedRat Device Model

This module defines the RedRat device model for database operations.
"""

from typing import Dict, Any, Optional, List
import json
import time
from datetime import datetime
from app.mysql_db import db
from app.utils.logger import logger


class RedRatDevice:
    """Model for RedRat devices."""
    
    def __init__(self, device_id: int = None, name: str = None, ip_address: str = None, 
                 port: int = 10001, description: str = None, is_active: bool = True, 
                 created_by: int = None, port_descriptions: Dict[str, str] = None):
        self.id = device_id
        self.name = name
        self.ip_address = ip_address
        self.port = port
        self.description = description
        self.is_active = is_active
        self.created_by = created_by
        self.port_descriptions = port_descriptions or {}
        self.last_status_check = None
        self.last_status = 'offline'
        self.device_model = None
        self.device_ports = None
        self.port_descriptions = None  # JSON object mapping port numbers to descriptions
        self.created_at = None
        self.updated_at = None
    
    @classmethod
    def get_all(cls) -> List['RedRatDevice']:
        """Get all RedRat devices."""
        devices = []
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, ip_address, port, description, is_active,
                           last_status_check, last_status, device_model, device_ports,
                           created_by, created_at, updated_at, port_descriptions
                    FROM redrat_devices
                    ORDER BY name
                """)
                
                for row in cursor.fetchall():
                    device = cls()
                    device.id = row[0]
                    device.name = row[1]
                    device.ip_address = row[2]
                    device.port = row[3]
                    device.description = row[4]
                    device.is_active = bool(row[5])
                    device.last_status_check = row[6]
                    device.last_status = row[7]
                    device.device_model = row[8]
                    device.device_ports = row[9]
                    device.created_by = row[10]
                    device.created_at = row[11]
                    device.updated_at = row[12]
                    # Parse port_descriptions JSON
                    device.port_descriptions = json.loads(row[13]) if row[13] else {}
                    devices.append(device)
                    
        except Exception as e:
            logger.error(f"Error getting RedRat devices: {str(e)}")
            
        return devices
    
    @classmethod
    def get_by_id(cls, device_id: int) -> Optional['RedRatDevice']:
        """Get RedRat device by ID."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, ip_address, port, description, is_active,
                           last_status_check, last_status, device_model, device_ports,
                           created_by, created_at, updated_at, port_descriptions
                    FROM redrat_devices
                    WHERE id = %s
                """, (device_id,))
                
                row = cursor.fetchone()
                if row:
                    device = cls()
                    device.id = row[0]
                    device.name = row[1]
                    device.ip_address = row[2]
                    device.port = row[3]
                    device.description = row[4]
                    device.is_active = bool(row[5])
                    device.last_status_check = row[6]
                    device.last_status = row[7]
                    device.device_model = row[8]
                    device.device_ports = row[9]
                    device.created_by = row[10]
                    device.created_at = row[11]
                    device.updated_at = row[12]
                    # Parse port_descriptions JSON
                    device.port_descriptions = json.loads(row[13]) if row[13] else {}
                    return device
                    
        except Exception as e:
            logger.error(f"Error getting RedRat device {device_id}: {str(e)}")
            
        return None
    
    def save(self) -> bool:
        """Save the RedRat device to database."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.id:
                    # Update existing device
                    cursor.execute("""
                        UPDATE redrat_devices
                        SET name = %s, ip_address = %s, port = %s, description = %s,
                            is_active = %s, port_descriptions = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (self.name, self.ip_address, self.port, self.description,
                          self.is_active, json.dumps(self.port_descriptions) if self.port_descriptions else None, self.id))
                else:
                    # Insert new device
                    cursor.execute("""
                        INSERT INTO redrat_devices (name, ip_address, port, description,
                                                   is_active, created_by, port_descriptions)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (self.name, self.ip_address, self.port, self.description,
                          self.is_active, self.created_by, json.dumps(self.port_descriptions) if self.port_descriptions else None))
                    
                    self.id = cursor.lastrowid
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error saving RedRat device: {str(e)}")
            return False
    
    def delete(self) -> bool:
        """Delete the RedRat device."""
        if not self.id:
            return False
            
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM redrat_devices WHERE id = %s", (self.id,))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error deleting RedRat device {self.id}: {str(e)}")
            return False
    
    def update_status(self, status: str, device_model: int = None, device_ports: int = None) -> bool:
        """Update device status after connection test."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE redrat_devices
                    SET last_status_check = CURRENT_TIMESTAMP,
                        last_status = %s,
                        device_model = %s,
                        device_ports = %s
                    WHERE id = %s
                """, (status, device_model, device_ports, self.id))
                
                conn.commit()
                self.last_status = status
                self.device_model = device_model
                self.device_ports = device_ports
                return True
                
        except Exception as e:
            logger.error(f"Error updating device status: {str(e)}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.ip_address,
            'port': self.port,
            'description': self.description,
            'is_active': self.is_active,
            'last_status_check': self.last_status_check.isoformat() if self.last_status_check else None,
            'last_status': self.last_status,
            'device_model': self.device_model,
            'device_ports': self.device_ports,
            'port_descriptions': self.port_descriptions,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
