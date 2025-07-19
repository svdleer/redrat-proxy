# -*- coding: utf-8 -*-

"""RedRat Device Management Service

This service handles RedRat device management operations including
device status checks, power control, and device configuration.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.models.redrat_device import RedRatDevice
from app.services.redrat_service import RedRatService
from app.utils.logger import logger


class RedRatDeviceService:
    """Service for managing RedRat devices."""
    
    @staticmethod
    def get_all_devices() -> List[Dict[str, Any]]:
        """Get all RedRat devices with current status."""
        devices = RedRatDevice.get_all()
        device_list = []
        
        for device in devices:
            device_dict = device.to_dict()
            
            # If the device hasn't been checked recently, do a quick status check
            if device.is_active and (not device.last_status_check or 
                                   (datetime.now() - device.last_status_check).total_seconds() > 300):  # 5 minutes
                try:
                    # Quick connection test
                    redrat_service = RedRatService(device.ip_address, device.port)
                    connection_result = redrat_service.test_connection()
                    
                    if connection_result['success']:
                        device.update_status('online', 
                                           connection_result.get('device_info', {}).get('model'),
                                           connection_result.get('device_info', {}).get('ports'))
                        device_dict['last_status'] = 'online'
                    else:
                        device.update_status('offline')
                        device_dict['last_status'] = 'offline'
                        
                except Exception as e:
                    logger.debug(f"Quick status check failed for {device.name}: {str(e)}")
                    device.update_status('error')
                    device_dict['last_status'] = 'error'
            
            device_list.append(device_dict)
            
        return device_list
    
    @staticmethod
    def get_device(device_id: int) -> Optional[Dict[str, Any]]:
        """Get device by ID."""
        device = RedRatDevice.get_by_id(device_id)
        return device.to_dict() if device else None
    
    @staticmethod
    def create_device(name: str, ip_address: str, port: int = 10001, 
                     description: str = None, user_id: int = None,
                     port_descriptions: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a new RedRat device."""
        result = {
            'success': False,
            'message': '',
            'device_id': None
        }
        
        try:
            # Validate input
            if not name or not ip_address:
                result['message'] = 'Name and IP address are required'
                return result
            
            # Create device
            device = RedRatDevice(
                name=name,
                ip_address=ip_address,
                port=port,
                description=description,
                created_by=user_id,
                port_descriptions=port_descriptions
            )
            
            if device.save():
                result['success'] = True
                result['message'] = 'Device created successfully'
                result['device_id'] = device.id
                logger.info(f"Created RedRat device: {name} ({ip_address}:{port})")
            else:
                result['message'] = 'Failed to save device to database'
                
        except Exception as e:
            result['message'] = f'Error creating device: {str(e)}'
            logger.error(f"Error creating device: {str(e)}")
            
        return result
    
    @staticmethod
    def update_device(device_id: int, name: str = None, ip_address: str = None, 
                     port: int = None, description: str = None, 
                     is_active: bool = None, port_descriptions: Dict[str, str] = None) -> Dict[str, Any]:
        """Update an existing RedRat device."""
        result = {
            'success': False,
            'message': ''
        }
        
        try:
            device = RedRatDevice.get_by_id(device_id)
            if not device:
                result['message'] = 'Device not found'
                return result
            
            # Update fields if provided
            if name is not None:
                device.name = name
            if ip_address is not None:
                device.ip_address = ip_address
            if port is not None:
                device.port = port
            if description is not None:
                device.description = description
            if is_active is not None:
                device.is_active = is_active
            if port_descriptions is not None:
                device.port_descriptions = port_descriptions
            
            if device.save():
                result['success'] = True
                result['message'] = 'Device updated successfully'
                logger.info(f"Updated RedRat device: {device.name} ({device.ip_address}:{device.port})")
            else:
                result['message'] = 'Failed to save device changes'
                
        except Exception as e:
            result['message'] = f'Error updating device: {str(e)}'
            logger.error(f"Error updating device: {str(e)}")
            
        return result
    
    @staticmethod
    def delete_device(device_id: int) -> Dict[str, Any]:
        """Delete a RedRat device."""
        result = {
            'success': False,
            'message': ''
        }
        
        try:
            device = RedRatDevice.get_by_id(device_id)
            if not device:
                result['message'] = 'Device not found'
                return result
            
            if device.delete():
                result['success'] = True
                result['message'] = 'Device deleted successfully'
                logger.info(f"Deleted RedRat device: {device.name}")
            else:
                result['message'] = 'Failed to delete device'
                
        except Exception as e:
            result['message'] = f'Error deleting device: {str(e)}'
            logger.error(f"Error deleting device: {str(e)}")
            
        return result
    
    @staticmethod
    def test_device_connection(device_id: int) -> Dict[str, Any]:
        """Test connection to a RedRat device."""
        result = {
            'success': False,
            'message': '',
            'device_info': None,
            'response_time': None
        }
        
        try:
            device = RedRatDevice.get_by_id(device_id)
            if not device:
                result['message'] = 'Device not found'
                return result
            
            # Test connection using RedRat service
            redrat_service = RedRatService(device.ip_address, device.port)
            connection_result = redrat_service.test_connection()
            
            # Update device status in database
            if connection_result['success']:
                device_model = connection_result['device_info'].get('model')
                device_ports = connection_result['device_info'].get('ports')
                device.update_status('online', device_model, device_ports)
                
                result['success'] = True
                result['message'] = connection_result['message']
                result['device_info'] = connection_result['device_info']
                result['response_time'] = connection_result['response_time']
            else:
                device.update_status('offline')
                result['message'] = connection_result['message']
                
        except Exception as e:
            result['message'] = f'Connection test failed: {str(e)}'
            logger.error(f"Connection test failed for device {device_id}: {str(e)}")
            
            # Update device status to error
            device = RedRatDevice.get_by_id(device_id)
            if device:
                device.update_status('error')
                
        return result
    
    @staticmethod
    def power_on_device(device_id: int) -> Dict[str, Any]:
        """Power on a RedRat device."""
        result = {
            'success': False,
            'message': ''
        }
        
        try:
            device = RedRatDevice.get_by_id(device_id)
            if not device:
                result['message'] = 'Device not found'
                return result
            
            # Power on device
            from app.services.redratlib import IRNetBox
            with IRNetBox(device.ip_address, device.port) as ir:
                ir.power_on()
                ir.indicators_on()
                
                result['success'] = True
                result['message'] = f'Device {device.name} powered on successfully'
                logger.info(f"Powered on RedRat device: {device.name}")
                
                # Update device status
                device.update_status('online')
                
        except Exception as e:
            result['message'] = f'Power on failed: {str(e)}'
            logger.error(f"Power on failed for device {device_id}: {str(e)}")
            
        return result
    
    @staticmethod
    def power_off_device(device_id: int) -> Dict[str, Any]:
        """Power off a RedRat device."""
        result = {
            'success': False,
            'message': ''
        }
        
        try:
            device = RedRatDevice.get_by_id(device_id)
            if not device:
                result['message'] = 'Device not found'
                return result
            
            # Power off device
            from app.services.redratlib import IRNetBox
            with IRNetBox(device.ip_address, device.port) as ir:
                ir.power_off()
                
                result['success'] = True
                result['message'] = f'Device {device.name} powered off successfully'
                logger.info(f"Powered off RedRat device: {device.name}")
                
                # Update device status
                device.update_status('offline')
                
        except Exception as e:
            result['message'] = f'Power off failed: {str(e)}'
            logger.error(f"Power off failed for device {device_id}: {str(e)}")
            
        return result
    
    @staticmethod
    def reset_device(device_id: int) -> Dict[str, Any]:
        """Reset a RedRat device."""
        result = {
            'success': False,
            'message': ''
        }
        
        try:
            device = RedRatDevice.get_by_id(device_id)
            if not device:
                result['message'] = 'Device not found'
                return result
            
            # Reset device
            from app.services.redratlib import IRNetBox
            with IRNetBox(device.ip_address, device.port) as ir:
                ir.reset()
                time.sleep(0.5)  # Wait for reset to complete
                ir.power_on()
                ir.indicators_on()
                
                result['success'] = True
                result['message'] = f'Device {device.name} reset successfully'
                logger.info(f"Reset RedRat device: {device.name}")
                
                # Update device status
                device.update_status('online')
                
        except Exception as e:
            result['message'] = f'Reset failed: {str(e)}'
            logger.error(f"Reset failed for device {device_id}: {str(e)}")
            
        return result
    
    @staticmethod
    def get_device_status_summary() -> Dict[str, Any]:
        """Get a summary of all device statuses."""
        devices = RedRatDevice.get_all()
        summary = {
            'total_devices': len(devices),
            'online': 0,
            'offline': 0,
            'error': 0,
            'active': 0,
            'inactive': 0
        }
        
        for device in devices:
            if device.is_active:
                summary['active'] += 1
            else:
                summary['inactive'] += 1
                
            if device.last_status == 'online':
                summary['online'] += 1
            elif device.last_status == 'offline':
                summary['offline'] += 1
            else:
                summary['error'] += 1
                
        return summary
    
    @staticmethod
    def get_devices_status() -> Dict[str, Any]:
        """Get status of all RedRat devices with real-time connection checks."""
        devices = RedRatDevice.get_all()
        device_statuses = []
        
        for device in devices:
            device_status = {
                'id': device.id,
                'name': device.name,
                'ip_address': device.ip_address,
                'port': device.port,
                'is_active': device.is_active,
                'last_status': device.last_status,
                'last_seen': device.last_status_check,
                'device_model': device.device_model,
                'device_ports': device.device_ports,
                'status': 'unknown',
                'response_time': None,
                'error_message': None
            }
            
            # Only test connection for active devices
            if device.is_active:
                try:
                    # Test connection using RedRat service
                    redrat_service = RedRatService(device.ip_address, device.port)
                    connection_result = redrat_service.test_connection()
                    
                    if connection_result['success']:
                        device_status['status'] = 'online'
                        device_status['response_time'] = connection_result['response_time']
                        
                        # Update device info if available
                        if connection_result['device_info']:
                            device_status['device_model'] = connection_result['device_info'].get('model')
                            device_status['device_ports'] = connection_result['device_info'].get('ports')
                        
                        # Update database status
                        device.update_status('online', device_status['device_model'], device_status['device_ports'])
                        
                    else:
                        device_status['status'] = 'offline'
                        device_status['error_message'] = connection_result['message']
                        
                        # Update database status
                        device.update_status('offline')
                        
                except Exception as e:
                    device_status['status'] = 'error'
                    device_status['error_message'] = str(e)
                    logger.error(f"Error checking device {device.name}: {str(e)}")
                    
                    # Update database status
                    device.update_status('error')
            else:
                device_status['status'] = 'inactive'
                
            device_statuses.append(device_status)
        
        return {
            'devices': device_statuses,
            'summary': RedRatDeviceService.get_device_status_summary()
        }
