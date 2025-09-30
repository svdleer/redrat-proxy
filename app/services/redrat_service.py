# -*- coding: utf-8 -*-

"""Enhanced RedRat service for the RedRat Proxy project.

This module extends the original redratlib.py with features needed for
our web application including JSON support, database integration, 
logging, and better error handling.

Author: Enhanced for RedRat Proxy Project
Based on: redratlib.py by David Rothlisberger
"""

import json
import logging
import time
import threading
from contextlib import contextmanager
from typing import Dict, Any, Optional, List
import binascii

# Import the new irnetbox_lib_new functionality
from .irnetbox_lib_new import IRNetBox

try:
    from app.mysql_db import db
    from app.utils.logger import logger
except ImportError:
    # Fallback logging if app logger not available
    logger = logging.getLogger("redrat_service")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
    
    # Mock db if not available
    class MockDB:
        @contextmanager
        def get_connection(self):
            yield None
    db = MockDB()


class RedRatService:
    """Enhanced RedRat service with web application integration."""
    
    def __init__(self, host: str, port: int = 10001, timeout: int = 10):
        """Initialize the RedRat service.
        
        Args:
            host: RedRat device IP address or hostname
            port: RedRat device port (default 10001)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._lock = threading.Lock()
        # Track alternation state for double signals (signal1 <-> signal2)
        self._alternation_state = {}  # Key: (remote_id, base_command), Value: 'signal1' or 'signal2'
        
    def validate_device_and_port(self, ir_port: int = 1) -> Dict[str, Any]:
        """Validate that the RedRat device is accessible and the IR port is valid.
        
        Args:
            ir_port: IR output port to validate (1-16)
            
        Returns:
            Dict with validation results
        """
        result = {
            'success': False,
            'device_accessible': False,
            'port_valid': False,
            'error': None
        }
        
        try:
            # Validate port number range
            if not (1 <= ir_port <= 16):
                result['error'] = f"Invalid IR port {ir_port}. Must be between 1 and 16"
                return result
            
            result['port_valid'] = True
            
            # Test device connectivity
            logger.debug(f"Testing connectivity to RedRat device at {self.host}:{self.port}")
            
            with self._lock:
                ir = IRNetBox(self.host)
                try:
                    if ir.connect():
                        result['device_accessible'] = True
                        logger.debug(f"RedRat device accessible, IR port {ir_port} ready")
                    else:
                        result['error'] = "Failed to connect to RedRat device"
                        return result
                finally:
                    ir.disconnect()
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = f"Device validation failed: {str(e)}"
            logger.error(f"RedRat device validation error: {str(e)}")
            
        return result
        
    def send_command(self, command_id: int, remote_id: int, command_name: str, 
                    ir_port: int = 1, power: int = 50) -> Dict[str, Any]:
        """Send a command to the RedRat device.
        
        Args:
            command_id: Database ID of the command
            remote_id: Database ID of the remote
            command_name: Name of the command to send
            ir_port: IR output port (1-16)
            power: IR power level (1-100)
            
        Returns:
            Dict with execution results
        """
        result = {
            'success': False,
            'message': '',
            'command_id': command_id,
            'executed_at': None,
            'error_details': None
        }
        
        try:
            # Validate device connectivity and port before executing command
            logger.debug(f"Validating RedRat device and IR port {ir_port}")
            validation_result = self.validate_device_and_port(ir_port)
            if not validation_result['success']:
                result['message'] = validation_result['error']
                result['error_details'] = f"Device validation failed for port {ir_port}"
                return result
            
            logger.debug(f"Device validation successful, proceeding with command execution")
            
            # Get command template data from database
            template_data = self._get_command_template(remote_id, command_name)
            if not template_data:
                logger.error(f"Command '{command_name}' not found for remote {remote_id}")
                result['message'] = f"Command '{command_name}' not found for remote {remote_id}"
                return result
            

            
            # Convert JSON template data to binary IR data and extract IR parameters
            ir_conversion_result = self._convert_template_to_ir_data(template_data)
            if not ir_conversion_result:
                result['message'] = "Failed to convert template data to IR signal"
                return result

            # Send command to RedRat device with IR parameters
            execution_result = self._execute_ir_command(ir_port, power, ir_conversion_result)
            
            if execution_result['success']:
                result['success'] = True
                result['message'] = f"Command '{command_name}' sent successfully"
                result['executed_at'] = time.time()
                
                # Update command status in database
                self._update_command_status(command_id, 'executed', result['executed_at'])
                
                logger.info(f"Successfully sent command '{command_name}' to RedRat device {self.host}")
            else:
                result['message'] = f"Failed to send command: {execution_result['error']}"
                result['error_details'] = execution_result.get('error_details')
                
                # Update command status in database
                self._update_command_status(command_id, 'failed', time.time(), result['message'])
                
                logger.error(f"Failed to send command '{command_name}': {result['message']}")
                
        except Exception as e:
            result['message'] = f"Unexpected error: {str(e)}"
            result['error_details'] = str(e)
            logger.error(f"Error sending command '{command_name}': {str(e)}")
            
            # Update command status in database
            self._update_command_status(command_id, 'failed', time.time(), str(e))
            
        return result
    
    def send_sequence(self, sequence_id: int, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send a sequence of commands to the RedRat device.
        
        Args:
            sequence_id: Database ID of the sequence
            commands: List of command dictionaries with delay information
            
        Returns:
            Dict with execution results
        """
        result = {
            'success': False,
            'message': '',
            'sequence_id': sequence_id,
            'executed_commands': 0,
            'failed_commands': 0,
            'executed_at': None,
            'errors': []
        }
        
        try:
            logger.info(f"Starting sequence {sequence_id} with {len(commands)} commands")
            
            for i, cmd in enumerate(commands):
                try:
                    # Send individual command
                    cmd_result = self.send_command(
                        cmd.get('id', 0),
                        cmd.get('remote_id'),
                        cmd.get('command'),
                        cmd.get('ir_port', 1),
                        cmd.get('power', 50)
                    )
                    
                    if cmd_result['success']:
                        result['executed_commands'] += 1
                        logger.info(f"Sequence {sequence_id}: Command {i+1}/{len(commands)} succeeded")
                    else:
                        result['failed_commands'] += 1
                        result['errors'].append({
                            'command': cmd.get('command'),
                            'error': cmd_result['message']
                        })
                        logger.error(f"Sequence {sequence_id}: Command {i+1}/{len(commands)} failed: {cmd_result['message']}")
                    
                    # Apply delay if specified
                    delay_ms = cmd.get('delay_ms', 0)
                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000.0)
                        
                except Exception as e:
                    result['failed_commands'] += 1
                    result['errors'].append({
                        'command': cmd.get('command', 'unknown'),
                        'error': str(e)
                    })
                    logger.error(f"Sequence {sequence_id}: Command {i+1}/{len(commands)} exception: {str(e)}")
            
            # Determine overall success
            if result['executed_commands'] > 0 and result['failed_commands'] == 0:
                result['success'] = True
                result['message'] = f"Sequence completed successfully. {result['executed_commands']} commands executed."
            elif result['executed_commands'] > 0:
                result['success'] = False
                result['message'] = f"Sequence partially completed. {result['executed_commands']} succeeded, {result['failed_commands']} failed."
            else:
                result['success'] = False
                result['message'] = "Sequence failed completely. No commands executed successfully."
            
            result['executed_at'] = time.time()
            logger.info(f"Sequence {sequence_id} completed: {result['message']}")
            
        except Exception as e:
            result['message'] = f"Sequence execution failed: {str(e)}"
            logger.error(f"Error executing sequence {sequence_id}: {str(e)}")
            
        return result
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to RedRat device.
        
        Returns:
            Dict with connection test results
        """
        result = {
            'success': False,
            'message': '',
            'device_info': None,
            'response_time': None
        }
        
        try:
            start_time = time.time()
            
            ir = IRNetBox(self.host)
            try:
                if ir.connect():
                    device_info = ir.get_device_info()
                    # Get device model safely
                    device_model = device_info.get('device_type', 'Unknown')
                    if hasattr(device_model, 'value'):
                        device_model = device_model.value
                    result['device_info'] = {
                        'model': device_model,
                        'ports': 16,  # Standard for IRNetBox
                        'host': self.host,
                        'port': self.port
                    }
                else:
                    result['message'] = "Failed to connect to RedRat device"
                    return result
            finally:
                ir.disconnect()
                
                result['response_time'] = time.time() - start_time
                result['success'] = True
                # Get device model safely
                device_model = getattr(ir, 'device_type', 'Unknown')
                if hasattr(device_model, 'value'):
                    device_model = device_model.value
                result['message'] = f"Successfully connected to RedRat device (model {device_model})"
                
                logger.info(f"Connection test successful: {result['message']}")
                
        except Exception as e:
            result['message'] = f"Connection test failed: {str(e)}"
            logger.error(f"Connection test failed: {str(e)}")
            
        return result
    
    def _get_command_template(self, remote_id: int, command_name: str) -> Optional[Dict[str, Any]]:
        """Get command template data from database with automatic alternation between signal1 and signal2.
        
        Args:
            remote_id: Database ID of the remote
            command_name: Name of the command
            
        Returns:
            Template data as dictionary or None if not found
        """
        try:
            with db.get_connection() as conn:
                if not conn:
                    logger.error("Database connection failed")
                    return None
                    
                cursor = conn.cursor()
                
                logger.debug(f"Looking for template: command='{command_name}', remote_id={remote_id}")
                
                # PRIORITY: Check for alternating double signals first (signal1/signal2)
                # This gives precedence to IRNetBox double signals over single commands
                signal1_name = f"{command_name}_signal1"
                signal2_name = f"{command_name}_signal2"
                
                # Check for double signals first
                cursor.execute("""
                    SELECT ct.name, ct.template_data 
                    FROM command_templates ct
                    WHERE ct.name IN (%s, %s) AND ct.file_id = %s
                    ORDER BY ct.name
                """, (signal1_name, signal2_name, remote_id))
                
                double_signals = cursor.fetchall()
                if double_signals:
                    # Use alternation state to switch between signal1 and signal2
                    alternation_key = (remote_id, command_name)
                    current_state = self._alternation_state.get(alternation_key, 'signal2')  # Start with signal2 so first call uses signal1
                    
                    if current_state == 'signal1':
                        # Switch to signal2
                        self._alternation_state[alternation_key] = 'signal2'
                        preferred_signal = signal2_name
                    else:
                        # Switch to signal1
                        self._alternation_state[alternation_key] = 'signal1'
                        preferred_signal = signal1_name
                    
                    # Find the preferred signal in results
                    for signal_name, signal_data in double_signals:
                        if signal_name == preferred_signal:
                            logger.debug(f"Using alternating signal '{preferred_signal}' for command '{command_name}' on remote {remote_id}")
                            return self._parse_template_data(signal_data)
                    
                    # If preferred signal not found, use the first available double signal
                    logger.debug(f"Preferred signal '{preferred_signal}' not found, using first available double signal '{double_signals[0][0]}' for command '{command_name}' on remote {remote_id}")
                    return self._parse_template_data(double_signals[0][1])
                
                # Fallback: Direct lookup using file_id which matches remote_id
                cursor.execute("""
                    SELECT ct.template_data 
                    FROM command_templates ct
                    WHERE ct.name = %s AND ct.file_id = %s
                    LIMIT 1
                """, (command_name, remote_id))
                
                result = cursor.fetchone()
                if result:
                    logger.debug(f"Found exact template for command '{command_name}' on remote {remote_id}")
                    return self._parse_template_data(result[0])
                
                logger.warning(f"No template found for command '{command_name}' on remote {remote_id}")
                cursor.close()
                return None
                
        except Exception as e:
            logger.error(f"Error getting command template: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_template_data(self, template_data) -> Optional[Dict[str, Any]]:
        """Parse template data from database format to dictionary.
        
        Args:
            template_data: Raw template data from database (bytes, str, or dict)
            
        Returns:
            Parsed template data as dictionary
        """
        try:
            # Parse the template data
            if isinstance(template_data, bytes):
                template_data = template_data.decode('utf-8')
            
            if isinstance(template_data, str):
                parsed_data = json.loads(template_data)
            else:
                parsed_data = template_data
            
            return parsed_data
        except Exception as e:
            logger.error(f"Error parsing template data: {e}")
            return None
    
    def _convert_template_to_ir_data(self, template_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert JSON template data to binary IR data and extract IR parameters.
        
        Args:
            template_data: JSON template data from database
            
        Returns:
            Dict containing IR data and parameters, or None if conversion fails
        """
        try:
            sig_data = None
            ir_params = {
                'modulation_freq': None,
                'no_repeats': 1,
                'intra_sig_pause': 100  # Default pause in milliseconds
            }
            
            # Extract IR parameters from template data (handle both root level and IRPacket formats)
            # NOTE: Each command can have its own frequency - this extracts per-command modulation_freq
            if 'modulation_freq' in template_data:
                # Direct format (Humax style) - modulation_freq can be string or int
                raw_freq = template_data['modulation_freq']
                ir_params['modulation_freq'] = int(float(raw_freq)) if isinstance(raw_freq, str) else int(raw_freq)

            if 'no_repeats' in template_data:
                ir_params['no_repeats'] = int(template_data['no_repeats'])
            if 'intra_sig_pause' in template_data:
                ir_params['intra_sig_pause'] = float(template_data['intra_sig_pause'])
            
            # Handle different template data formats
            if 'SigData' in template_data:
                # Direct signal data (hex string format)
                sig_data = template_data['SigData']
                if isinstance(sig_data, str):
                    # Clean the hex string - remove spaces, newlines, and non-hex characters
                    cleaned_sig_data = ''.join(c for c in sig_data if c in '0123456789abcdefABCDEF')
                    if cleaned_sig_data:
                        # Ensure even length for proper hex conversion
                        if len(cleaned_sig_data) % 2 != 0:
                            cleaned_sig_data = '0' + cleaned_sig_data
                        ir_data = binascii.unhexlify(cleaned_sig_data)
                        return {
                            'ir_data': ir_data,
                            'modulation_freq': ir_params['modulation_freq'],
                            'no_repeats': ir_params['no_repeats'],
                            'intra_sig_pause': ir_params['intra_sig_pause']
                        }
                    
            elif 'IRPacket' in template_data:
                # IRPacket format from XML
                ir_packet = template_data['IRPacket']
                
                # Extract parameters from IRPacket (XML format uses different key names)
                if 'ModulationFreq' in ir_packet:
                    raw_freq = ir_packet['ModulationFreq']
                    ir_params['modulation_freq'] = int(float(raw_freq))
                    logger.debug(f"Raw ModulationFreq from XML: '{raw_freq}' (type: {type(raw_freq)}) -> parsed: {ir_params['modulation_freq']}")
                else:
                    logger.debug(f"No ModulationFreq found in IRPacket. Available keys: {list(ir_packet.keys())}")
                    # Check if it's stored under a different name
                    for key in ir_packet:
                        if 'freq' in key.lower() or 'modulation' in key.lower():
                            logger.debug(f"Found frequency-related key '{key}': {ir_packet[key]}")
                if 'NoRepeats' in ir_packet:
                    ir_params['no_repeats'] = int(ir_packet['NoRepeats'])
                if 'IntraSigPause' in ir_packet:
                    ir_params['intra_sig_pause'] = float(ir_packet['IntraSigPause'])
                
                # Extract Lengths array for RedRat3 signals
                lengths = []
                if 'Lengths' in ir_packet and isinstance(ir_packet['Lengths'], list):
                    lengths = [float(x) for x in ir_packet['Lengths']]
                    logger.debug(f"Extracted {len(lengths)} lengths from XML")
                ir_params['lengths'] = lengths
                
                if 'SigData' in ir_packet:
                    sig_data = ir_packet['SigData']
                    if isinstance(sig_data, str):
                        # SigData from XML is base64-encoded, not hex
                        try:
                            import base64
                            ir_data = base64.b64decode(sig_data)
                            logger.debug(f"Decoded base64 SigData: {len(ir_data)} bytes")
                            logger.debug(f"Using ModulationFreq: {ir_params['modulation_freq']}Hz")
                            return {
                                'ir_data': ir_data,
                                'modulation_freq': ir_params['modulation_freq'],
                                'no_repeats': ir_params['no_repeats'],
                                'intra_sig_pause': ir_params['intra_sig_pause'],
                                'lengths': ir_params.get('lengths', [])
                            }
                        except Exception as e:
                            logger.warning(f"Failed to decode base64 SigData, trying hex: {e}")
                            # Fallback to hex if base64 fails
                            cleaned_sig_data = ''.join(c for c in sig_data if c in '0123456789abcdefABCDEF')
                            if cleaned_sig_data:
                                if len(cleaned_sig_data) % 2 != 0:
                                    cleaned_sig_data = '0' + cleaned_sig_data
                                ir_data = binascii.unhexlify(cleaned_sig_data)
                                return {
                                    'ir_data': ir_data,
                                    'modulation_freq': ir_params['modulation_freq'],
                                    'no_repeats': ir_params['no_repeats'],
                                    'intra_sig_pause': ir_params['intra_sig_pause']
                                }
                        
            elif 'signal_data' in template_data or 'sig_data' in template_data:
                # Database format - signal_data is binary data encoded as base64 or raw bytes
                # Also handle sig_data format from JSON files and Humax direct format
                sig_data = template_data.get('signal_data') or template_data.get('sig_data')
                
                # Extract Lengths array for RedRat3 signals if available (Humax format)
                lengths = []
                if 'lengths' in template_data and isinstance(template_data['lengths'], list):
                    lengths = [float(x) for x in template_data['lengths']]
                    logger.debug(f"Extracted {len(lengths)} lengths from direct format")
                ir_params['lengths'] = lengths
                
                if isinstance(sig_data, str):
                    # Skip empty strings
                    if not sig_data.strip():
                        logger.warning("Empty signal data string found in template")
                        return None
                        
                    # Could be base64 encoded binary data
                    try:
                        import base64
                        ir_data = base64.b64decode(sig_data)
                        if len(ir_data) == 0:
                            logger.warning("Base64 decoded to empty data")
                            return None
                        logger.debug(f"Decoded signal_data: {len(ir_data)} bytes")
                        logger.debug(f"Using ModulationFreq: {ir_params['modulation_freq']}Hz")
                        return {
                            'ir_data': ir_data,
                            'modulation_freq': ir_params['modulation_freq'],
                            'no_repeats': ir_params['no_repeats'],
                            'intra_sig_pause': ir_params['intra_sig_pause'],
                            'lengths': ir_params.get('lengths', [])
                        }
                    except:
                        # If base64 fails, treat as hex string
                        cleaned_sig_data = ''.join(c for c in sig_data if c in '0123456789abcdefABCDEF')
                        if cleaned_sig_data:
                            if len(cleaned_sig_data) % 2 != 0:
                                cleaned_sig_data = '0' + cleaned_sig_data
                            ir_data = binascii.unhexlify(cleaned_sig_data)
                            return {
                                'ir_data': ir_data,
                                'modulation_freq': ir_params['modulation_freq'],
                                'no_repeats': ir_params['no_repeats'],
                                'intra_sig_pause': ir_params['intra_sig_pause'],
                                'lengths': ir_params.get('lengths', [])
                            }
                        else:
                            logger.warning("No valid hex data found in signal data")
                            return None
                elif isinstance(sig_data, bytes):
                    # Already binary data
                    if len(sig_data) == 0:
                        logger.warning("Empty binary signal data")
                        return None
                    return {
                        'ir_data': sig_data,
                        'modulation_freq': ir_params['modulation_freq'],
                        'no_repeats': ir_params['no_repeats'],
                        'intra_sig_pause': ir_params['intra_sig_pause'],
                        'lengths': ir_params.get('lengths', [])
                    }
                elif isinstance(sig_data, list):
                    # List of bytes
                    if len(sig_data) == 0:
                        logger.warning("Empty list signal data")
                        return None
                    ir_data = bytes(sig_data)
                    return {
                        'ir_data': ir_data,
                        'modulation_freq': ir_params['modulation_freq'],
                        'no_repeats': ir_params['no_repeats'],
                        'intra_sig_pause': ir_params['intra_sig_pause'],
                        'lengths': ir_params.get('lengths', [])
                    }
            
            logger.warning(f"No valid signal data found in template. Available keys: {list(template_data.keys())}")
            
        except binascii.Error as e:
            logger.error(f"Hex conversion error: {str(e)}")
            logger.error(f"Problematic data: {str(sig_data)[:100]}...")
            
        except Exception as e:
            logger.error(f"Error converting template data to IR: {str(e)}")
            logger.error(f"Template data type: {type(template_data)}")
            logger.error(f"Signal data type: {type(sig_data) if sig_data else 'None'}")
            
        return None
    
    def _execute_ir_command(self, ir_port: int, power: int, ir_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute IR command on RedRat device with IR parameters.
        
        Args:
            ir_port: IR output port
            power: IR power level
            ir_params: Dict containing IR data and parameters
            
        Returns:
            Dict with execution results
        """
        result = {
            'success': False,
            'error': None,
            'error_details': None
        }
        
        try:
            ir_data = ir_params.get('ir_data')
            if not ir_data:
                result['error'] = "No IR data provided"
                return result
                
            modulation_freq = ir_params.get('modulation_freq')
            no_repeats = ir_params.get('no_repeats', 1)
            intra_sig_pause = ir_params.get('intra_sig_pause', 100)
            
            logger.info(f"Executing IR command: port={ir_port}, power={power}, repeats={no_repeats}, pause={intra_sig_pause}ms")
            if modulation_freq:
                logger.info(f"Modulation frequency: {modulation_freq}Hz")
            
            with self._lock:  # Ensure thread safety
                # Validate port number is within reasonable range
                if not (1 <= ir_port <= 16):
                    result['error'] = f"Invalid IR port {ir_port}. Must be between 1 and 16"
                    return result
                
                ir = IRNetBox(self.host)
                try:
                    # Connect to device
                    logger.debug(f"Connecting to RedRat device at {self.host}")
                    if not ir.connect():
                        result['error'] = "Failed to connect to RedRat device"
                        return result
                    
                    logger.debug(f"Device ready, sending IR signal to port {ir_port}")
                    
                    # Create IRSignal object from the data
                    from .irnetbox_lib_new import IRSignal, OutputConfig, PowerLevel
                    
                    # Map power percentage to PowerLevel enum
                    if power >= 75:
                        power_level = PowerLevel.HIGH
                    elif power >= 50:
                        power_level = PowerLevel.MEDIUM
                    elif power >= 25:
                        power_level = PowerLevel.LOW
                    else:
                        power_level = PowerLevel.OFF
                    
                    # Extract lengths from IR data if available
                    lengths = ir_params.get('lengths', [])
                    
                    # Create signal object using the actual command name from template
                    command_name = ir_params.get('command_name', f"Command_{ir_port}")
                    signal = IRSignal(
                        name=command_name,
                        uid=f"cmd_{ir_port}_{int(time.time())}",
                        modulation_freq=modulation_freq or 38000,  # Default to 38kHz if not specified
                        lengths=lengths,  # Use lengths from XML data
                        sig_data=ir_data,
                        no_repeats=no_repeats,
                        intra_sig_pause=intra_sig_pause
                    )
                    
                    # Send the signal using ASYNC protocol
                    output_configs = [OutputConfig(port=ir_port, power_level=power_level)]
                    
                    # Force ASYNC mode for MK-III/MK-IV devices
                    if hasattr(ir, 'device_type') and ir.device_type.value in ['MK-III', 'MK-IV']:
                        # Use async protocol with sequence number and proper timing
                        seq_num = ir.send_signal_async(signal, output_configs, post_delay_ms=500, enforce_timing=True)
                        logger.info(f"Sent ASYNC signal with sequence {seq_num}")
                    else:
                        # Fallback to regular send for older devices
                        ir.send_signal(signal, [ir_port], power_level)
                    
                finally:
                    ir.disconnect()
                    
                    logger.debug(f"IR command completed successfully on port {ir_port}")
                    result['success'] = True
                    result['repeats_sent'] = no_repeats
                    result['port_used'] = ir_port
                    
        except Exception as e:
            result['error'] = str(e)
            result['error_details'] = str(e)
            logger.error(f"Error executing IR command: {str(e)}")
            
        return result
    
    def _update_command_status(self, command_id: int, status: str, 
                             executed_at: float, error_message: str = None):
        """Update command status in database.
        
        Args:
            command_id: Database ID of the command
            status: New status ('executed', 'failed', 'pending')
            executed_at: Execution timestamp
            error_message: Error message if failed
        """
        try:
            with db.get_connection() as conn:
                if not conn:
                    return
                    
                cursor = conn.cursor()
                
                if error_message:
                    cursor.execute("""
                        UPDATE commands 
                        SET status = %s, executed_at = FROM_UNIXTIME(%s), 
                            status_updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (status, executed_at, command_id))
                else:
                    cursor.execute("""
                        UPDATE commands 
                        SET status = %s, executed_at = FROM_UNIXTIME(%s), 
                            status_updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (status, executed_at, command_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating command status: {str(e)}")


# Factory function for creating RedRat service instances
def create_redrat_service(host: str, port: int = 10001, timeout: int = 10) -> RedRatService:
    """Create a RedRat service instance.
    
    Args:
        host: RedRat device IP address or hostname
        port: RedRat device port (default 10001)
        timeout: Connection timeout in seconds
        
    Returns:
        RedRatService instance
    """
    return RedRatService(host, port, timeout)


# Singleton instance for the application
_redrat_service = None

def get_redrat_service() -> Optional[RedRatService]:
    """Get the global RedRat service instance.
    
    Returns:
        RedRatService instance or None if not configured
    """
    global _redrat_service
    
    if _redrat_service is None:
        # Try to get RedRat configuration from environment
        import os
        redrat_host = os.getenv('REDRAT_HOST')
        redrat_port = int(os.getenv('REDRAT_PORT', '10001'))
        
        if redrat_host:
            _redrat_service = create_redrat_service(redrat_host, redrat_port)
            logger.info(f"Created RedRat service for {redrat_host}:{redrat_port}")
        else:
            logger.debug("REDRAT_HOST not configured - using database-driven device selection")
    
    return _redrat_service


def reset_redrat_service():
    """Reset the global RedRat service instance.
    
    This forces a new service instance to be created with the latest configuration.
    Useful after database schema changes or configuration updates.
    """
    global _redrat_service
    _redrat_service = None
    logger.info("RedRat service instance reset - will be recreated on next access")
