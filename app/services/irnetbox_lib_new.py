"""
IRNetBox Library for Python
Implements the IRNetBox Network Control Protocol for detecting device types
and sending IR commands.

Based on "The irNetBox Network Control Protocol" documentation.
"""

import socket
import struct
import time
import xml.etree.ElementTree as ET
import base64
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum


class IRNetBoxType(Enum):
    """IRNetBox hardware types."""
    MK_I = "MK-I"
    MK_II = "MK-II" 
    MK_III = "MK-III"
    MK_IV = "MK-IV"
    UNKNOWN = "Unknown"


class PowerLevel(Enum):
    """IR output power levels."""
    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class OutputConfig:
    """Configuration for IR output ports."""
    port: int  # 1-16
    power_level: PowerLevel
    
    def __post_init__(self):
        if not 1 <= self.port <= 16:
            raise ValueError("Port must be between 1 and 16")


@dataclass
class AsyncResponse:
    """Response from async IR output operation."""
    sequence_number: int
    success: bool
    error_code: int = 0


@dataclass
@dataclass
class IRSignal:
    """Represents an IR signal from XML data."""
    name: str
    uid: str
    modulation_freq: int
    lengths: List[float]
    sig_data: bytes
    no_repeats: int
    intra_sig_pause: float
    toggle_data: Optional[Dict] = None  # Dict[int, tuple[int, int]] - bit_no: (len1, len2)


@dataclass
class AVDevice:
    """Represents an audio/video device with its IR signals."""
    name: str
    manufacturer: str
    device_model: str
    remote_model: str
    device_type: str
    signals: List[IRSignal]


class IRNetBoxError(Exception):
    """Exception for IRNetBox communication errors."""
    pass


class IRNetBox:
    """IRNetBox communication class."""
    
    # Message types from the protocol documentation
    MSG_ERROR = 0x01
    MSG_READ_FIRMWARE = 0x04
    MSG_CPLD_POWER_ON = 0x05
    MSG_CPLD_POWER_OFF = 0x06
    MSG_CPLD_INSTRUCTION = 0x07
    MSG_READ_SERIAL = 0x08
    MSG_READ_VERSION = 0x09
    MSG_ALLOCATE_MEMORY = 0x10
    MSG_DOWNLOAD_SIGNAL = 0x11
    MSG_OUTPUT_SIGNAL = 0x12
    MSG_READ_PARAMS = 0x20
    MSG_SET_PARAMS = 0x21
    MSG_SET_OUTPUT_MASK = 0x22
    MSG_ASYNC_OUTPUT = 0x30
    MSG_ASYNC_COMPLETE = 0x31
    MSG_SET_OUTPUT_POWER_MULTI = 0x43
    
    # UDP Discovery ports
    UDP_DISCOVERY_PORT = 30718  # 0x77FE
    TCP_CONTROL_PORT = 10001
    
    # CPLD Instructions
    CPLD_RESET = 0x00
    CPLD_ENABLE_LOW_1 = 0x02
    CPLD_ENABLE_ALL = 0x12
    CPLD_ENABLE_HIGH_1 = 0x13
    CPLD_LED_REFLECT = 0x17
    CPLD_LED_OFF = 0x18
    
    # Complete error code mapping from protocol documentation
    ERROR_CODES = {
        0x20: "Signal Capture: Initial IR signal pulse not long enough to measure carrier frequency",
        0x21: "Signal Capture: Not enough length values allocated for this IR signal",
        0x22: "Signal Capture: Not enough memory allocated for the sampled signal data",
        0x23: "Signal Capture: Too many repeats in signal (exceeds maximum of 255)",
        0x28: "Signal Download: Not enough memory on device to allocate memory for modulated signal",
        0x29: "Signal Download: No memory for modulated signal has been allocated",
        0x2A: "No signal data has been captured or downloaded",
        0x2B: "Signal Download: Not enough memory available on device for IrDA signal buffer",
        0x2C: "Signal Download: No memory for IrDA data has been allocated",
        0x2D: "Signal Download: No IrDA signal data has been downloaded",
    }
    
    def __init__(self, ip_address: str = None):
        """Initialize IRNetBox connection."""
        self.ip_address = ip_address
        self.socket = None
        self.device_type = IRNetBoxType.UNKNOWN
        self.serial_number = None
        self.firmware_version = None
        self.toggle_states = {}  # Track toggle states per signal UID
        self.port_last_used = {}  # Track when each port was last used for timing
        self.signal_database = {}  # Signal name -> IRSignal lookup
        
    def discover_devices(self, timeout: float = 2.0) -> List[Dict[str, str]]:
        """
        Discover IRNetBox devices on the network via UDP broadcast.
        Returns list of discovered devices with IP and MAC addresses.
        """
        devices = []
        
        try:
            # Create UDP socket for discovery
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.settimeout(timeout)
            
            # Send discovery packet (0x00, 0x00, 0x00, 0xF6)
            discovery_packet = struct.pack('>I', 0x000000F6)
            udp_socket.sendto(discovery_packet, ('255.255.255.255', self.UDP_DISCOVERY_PORT))
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = udp_socket.recvfrom(1024)
                    if len(data) >= 30:
                        # Parse response: 4 bytes type + 16 bytes firmware + 4 bytes info + 6 bytes MAC
                        firmware_id = data[4:6].decode('ascii', errors='ignore')
                        mac_bytes = data[24:30]
                        mac_address = ':'.join(f'{b:02x}' for b in mac_bytes)
                        
                        device_info = {
                            'ip_address': addr[0],
                            'firmware_id': firmware_id,
                            'mac_address': mac_address,
                            'raw_data': data
                        }
                        devices.append(device_info)
                        
                except socket.timeout:
                    break
                    
            udp_socket.close()
            
        except Exception as e:
            raise IRNetBoxError(f"Device discovery failed: {e}")
            
        return devices
    
    def identify_device_type(self, ip_address: str) -> IRNetBoxType:
        """
        Identify the IRNetBox type using UDP queries.
        """
        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.settimeout(2.0)
            
            # First, get firmware type with 0xF6 query
            discovery_packet = struct.pack('>I', 0x000000F6)
            udp_socket.sendto(discovery_packet, (ip_address, self.UDP_DISCOVERY_PORT))
            
            data, _ = udp_socket.recvfrom(1024)
            if len(data) >= 6:
                firmware_id = data[4:6].decode('ascii', errors='ignore')
                
                # Determine type based on firmware ID
                if firmware_id in ['X1', 'X2']:
                    return IRNetBoxType.MK_I
                elif firmware_id == 'X9':
                    return IRNetBoxType.MK_III
                elif firmware_id == 'X5':
                    # Need further identification with 0xE4 query
                    type_packet = struct.pack('>I', 0x000000E4)
                    udp_socket.sendto(type_packet, (ip_address, self.UDP_DISCOVERY_PORT))
                    
                    type_data, _ = udp_socket.recvfrom(1024)
                    if len(type_data) > 32:
                        label_len = type_data[32]
                        if label_len > 0:
                            label = type_data[33:33+label_len].decode('ascii', errors='ignore')
                            if 'REDRAT4-III' in label:
                                return IRNetBoxType.MK_III
                            elif 'REDRAT4-II' in label:
                                return IRNetBoxType.MK_II
                            elif 'REDRAT4' in label:
                                return IRNetBoxType.MK_I
                                
            udp_socket.close()
            
        except Exception as e:
            print(f"Warning: Could not identify device type: {e}")
            
        return IRNetBoxType.UNKNOWN
    
    def _detect_type_from_firmware(self, firmware_version: str) -> IRNetBoxType:
        """
        Detect device type from firmware version string.
        
        Args:
            firmware_version: Firmware version string
            
        Returns:
            IRNetBoxType: Detected device type
        """
        if not firmware_version:
            return IRNetBoxType.UNKNOWN
            
        firmware_upper = firmware_version.upper()
        
        # Check for explicit version markers in firmware
        if 'MKIV' in firmware_upper or 'MK-IV' in firmware_upper:
            return IRNetBoxType.MK_IV
        elif 'MKIII' in firmware_upper or 'MK-III' in firmware_upper:
            return IRNetBoxType.MK_III
        elif 'MKII' in firmware_upper or 'MK-II' in firmware_upper:
            return IRNetBoxType.MK_II
        elif 'MKI' in firmware_upper or 'MK-I' in firmware_upper:
            return IRNetBoxType.MK_I
            
        # Fallback: try to infer from firmware patterns
        if 'IRNETBOX' in firmware_upper:
            # If we see "irNetBox" but no specific version, assume newer model
            if any(word in firmware_upper for word in ['2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']):
                return IRNetBoxType.MK_IV  # Newer firmware likely MK-IV
            else:
                return IRNetBoxType.MK_III  # Older but still modern
        
        return IRNetBoxType.UNKNOWN
    
    def connect(self, ip_address: str = None) -> bool:
        """
        Connect to IRNetBox via TCP.
        """
        if ip_address:
            self.ip_address = ip_address
            
        if not self.ip_address:
            raise IRNetBoxError("No IP address specified")
            
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.ip_address, self.TCP_CONTROL_PORT))
            
            # Identify device type
            self.device_type = self.identify_device_type(self.ip_address)
            
            # Initialize device
            self._initialize_device()
            
            return True
            
        except Exception as e:
            if self.socket:
                self.socket.close()
                self.socket = None
            raise IRNetBoxError(f"Connection failed: {e}")
    
    def disconnect(self):
        """Disconnect from IRNetBox."""
        if self.socket:
            try:
                # CPLD instructions are only needed for MK-I and MK-II devices
                needs_cpld = self.device_type in [IRNetBoxType.MK_I, IRNetBoxType.MK_II, IRNetBoxType.UNKNOWN]
                
                if needs_cpld:
                    # Reset CPLD and power off
                    self._send_cpld_instruction(self.CPLD_RESET)
                    self._send_message(self.MSG_CPLD_POWER_OFF, b'')
            except:
                pass
            finally:
                self.socket.close()
                self.socket = None
    
    def _initialize_device(self):
        """Initialize device after connection."""
        # CPLD instructions are only needed for MK-I and MK-II devices
        # MK-III and MK-IV devices may not require CPLD instructions
        needs_cpld = self.device_type in [IRNetBoxType.MK_I, IRNetBoxType.MK_II, IRNetBoxType.UNKNOWN]
        
        if needs_cpld:
            # Power on CPLD
            self._send_message(self.MSG_CPLD_POWER_ON, b'')
            
            # Reset CPLD
            self._send_cpld_instruction(self.CPLD_RESET)
            
            # Enable LED reflection
            self._send_cpld_instruction(self.CPLD_LED_REFLECT)
        
        # Read firmware version
        response = self._send_message(self.MSG_READ_FIRMWARE, b'')
        if response:
            self.firmware_version = response.decode('ascii', errors='ignore').strip('\x00')
            
            # Try to detect device type from firmware if UDP detection failed
            if self.device_type == IRNetBoxType.UNKNOWN:
                self.device_type = self._detect_type_from_firmware(self.firmware_version)
            
        # Read serial number
        try:
            response = self._send_message(self.MSG_READ_SERIAL, b'')
            if len(response) >= 18:
                # Parse USB descriptor format
                serial_chars = []
                for i in range(4, 18, 2):
                    if i + 1 < len(response):
                        char = chr(response[i])
                        if char.isprintable():
                            serial_chars.append(char)
                self.serial_number = ''.join(serial_chars)
        except:
            pass
    
    def _send_message(self, msg_type: int, data: bytes) -> bytes:
        """Send a message to the IRNetBox and return response."""
        if not self.socket:
            raise IRNetBoxError("Not connected")
            
        # Build message: '#' + length (ushort, big-endian) + type + data
        message = struct.pack('>cHB', b'#', len(data), msg_type) + data
        
        try:
            self.socket.send(message)
            
            # Read response: length (ushort, big-endian) + type + data
            response_header = self.socket.recv(3)
            if len(response_header) < 3:
                raise IRNetBoxError("Incomplete response header")
                
            response_length, response_type = struct.unpack('>HB', response_header)
            
            # Check for error response
            if response_type == self.MSG_ERROR:
                if response_length > 0:
                    error_data = self.socket.recv(response_length)
                    error_code = error_data[0] if error_data else 0
                    error_msg = self.ERROR_CODES.get(error_code, f"Unknown error code: 0x{error_code:02X}")
                    raise IRNetBoxError(f"Device returned error: {error_msg}")
                else:
                    raise IRNetBoxError("Device returned error")
            
            # Read response data
            response_data = b''
            if response_length > 0:
                response_data = self.socket.recv(response_length)
                
            return response_data
            
        except socket.timeout:
            raise IRNetBoxError("Communication timeout")
        except Exception as e:
            raise IRNetBoxError(f"Communication error: {e}")
    
    def _send_cpld_instruction(self, instruction: int):
        """Send CPLD instruction."""
        self._send_message(self.MSG_CPLD_INSTRUCTION, struct.pack('B', instruction))
    
    def allocate_signal_memory(self):
        """Allocate memory for modulated IR signals."""
        self._send_message(self.MSG_ALLOCATE_MEMORY, b'')
    
    def set_output_power(self, port: int, power_level: PowerLevel = PowerLevel.MEDIUM):
        """
        Set power level for a specific output port (1-16).
        
        Args:
            port: Output port number (1-16)
            power_level: Power level (OFF, LOW, MEDIUM, HIGH). Defaults to MEDIUM.
        """
        if not 1 <= port <= 16:
            raise ValueError("Port must be between 1 and 16")
        
        if power_level == PowerLevel.OFF:
            # Reset CPLD disables all outputs
            self._send_cpld_instruction(self.CPLD_RESET)
        elif power_level == PowerLevel.LOW:
            if port == 1:
                self._send_cpld_instruction(self.CPLD_ENABLE_LOW_1)
            else:
                self._send_cpld_instruction(0x02 + port - 1)  # Enable low power outputs 2-16
        elif power_level == PowerLevel.HIGH:
            if port == 1:
                self._send_cpld_instruction(self.CPLD_ENABLE_HIGH_1)
            else:
                # For MK-II and later: high power = low + medium power combined
                # MK-IV is MK-III compatible
                if self.device_type in [IRNetBoxType.MK_II, IRNetBoxType.MK_III, IRNetBoxType.MK_IV]:
                    self._send_cpld_instruction(0x02 + port - 1)  # Low power
                    self._send_cpld_instruction(0x20 + port - 1)  # Medium power
                else:
                    # For MK-I, treat as low power
                    self._send_cpld_instruction(0x02 + port - 1)
        elif power_level == PowerLevel.MEDIUM:
            # Medium power available on MK-II and later (MK-III, MK-IV)
            # MK-IV is MK-III compatible
            if self.device_type in [IRNetBoxType.MK_II, IRNetBoxType.MK_III, IRNetBoxType.MK_IV]:
                if port == 1:
                    self._send_cpld_instruction(0x20)  # Enable medium power on port 1
                else:
                    self._send_cpld_instruction(0x20 + port - 1)  # Medium power ports 2-16
            else:
                # Fallback to low power for MK-I
                self.set_output_power(port, PowerLevel.LOW)
    
    def set_output_mask(self, output_configs: List[OutputConfig]):
        """
        Set multiple outputs using bit mask (MK-II and MK-III only).
        More efficient than setting outputs individually.
        
        Args:
            output_configs: List of OutputConfig objects specifying port and power
        """
        if self.device_type == IRNetBoxType.MK_I:
            # Fallback to individual commands for MK-I
            self._send_cpld_instruction(self.CPLD_RESET)
            for config in output_configs:
                if config.power_level != PowerLevel.OFF:
                    self.set_output_power(config.port, config.power_level)
            return
        
        # Build 4-byte bit mask for MK-II/III
        # Each port uses 2 bits: 00=OFF, 01=LOW, 10=MEDIUM, 11=HIGH
        mask_bytes = [0, 0, 0, 0]
        
        for config in output_configs:
            port = config.port
            power_bits = config.power_level.value
            
            # Calculate byte and bit position
            byte_index = (port - 1) // 4
            bit_offset = ((port - 1) % 4) * 2
            
            # Clear existing bits and set new ones
            mask_bytes[byte_index] &= ~(3 << bit_offset)  # Clear 2 bits
            mask_bytes[byte_index] |= (power_bits << bit_offset)  # Set new bits
        
        # Send bit mask command
        mask_data = struct.pack('4B', mask_bytes[3], mask_bytes[2], mask_bytes[1], mask_bytes[0])
        self._send_message(self.MSG_SET_OUTPUT_MASK, mask_data)
    
    def send_signal_async(self, signal: IRSignal, output_configs: List[OutputConfig], 
                         sequence_number: int = None, post_delay_ms: int = 500, 
                         enforce_timing: bool = True) -> int:
        """
        Send IR signal asynchronously (MK-III and MK-IV).
        Returns sequence number for tracking completion.
        
        Args:
            signal: IR signal to send
            output_configs: List of output configurations
            sequence_number: Optional sequence number (auto-generated if None)
            post_delay_ms: Delay after signal in milliseconds (100-10000). 
                         Default 500ms for slow STBs. Set to 0 to use device default (100ms).
                         This prevents rapid signals from confusing the receiving device.
            enforce_timing: Whether to enforce 10-second timing between same-port commands
            
        Returns:
            Sequence number for tracking this command
        """
        if self.device_type not in [IRNetBoxType.MK_III, IRNetBoxType.MK_IV]:
            raise IRNetBoxError("Async output only supported on MK-III and MK-IV devices")
        
        # Check timing constraints for async-aware devices (MK-IV)
        if enforce_timing and self.device_type == IRNetBoxType.MK_IV:
            current_time = time.time()
            min_delay = 10.0  # 10 seconds minimum between same-port commands (realistic for slow STBs)
            
            for config in output_configs:
                port = config.port
                if port in self.port_last_used:
                    time_since_last = current_time - self.port_last_used[port]
                    if time_since_last < min_delay:
                        wait_time = min_delay - time_since_last
                        print(f"   ⏳ Port {port} needs {wait_time:.1f}s cooldown (slow STB timing), waiting...")
                        time.sleep(wait_time)
                        current_time = time.time()  # Update current time after wait
        
        if sequence_number is None:
            sequence_number = int(time.time() * 1000) % 65536  # Use timestamp mod 65536
        
        # Validate and set post-delay (prevents rapid signals from confusing receiver)
        if not 0 <= post_delay_ms <= 10000:
            post_delay_ms = 500  # Default 500ms for slow STBs
        
        if post_delay_ms == 0:
            post_delay_ms = 100  # Use device default if 0 specified
        
        # Build async message data
        async_data = struct.pack('<H', sequence_number)  # Little-endian sequence number
        async_data += struct.pack('<H', post_delay_ms)   # Little-endian delay
        
        # Add power levels for all 16 ports (0 = not used)
        power_levels = [0] * 16
        for config in output_configs:
            if 1 <= config.port <= 16:
                # Convert power level to percentage (0-100)
                power_map = {
                    PowerLevel.OFF: 0,
                    PowerLevel.LOW: 25,
                    PowerLevel.MEDIUM: 50,
                    PowerLevel.HIGH: 100
                }
                power_levels[config.port - 1] = power_map.get(config.power_level, 0)
        
        async_data += struct.pack('16B', *power_levels)
        
        # Add IR signal data
        signal_binary = self.download_signal(signal)
        async_data += signal_binary
        
        # Send async output command
        response = self._send_message(self.MSG_ASYNC_OUTPUT, async_data)
        
        # Update port usage timestamps
        current_time = time.time()
        for config in output_configs:
            self.port_last_used[config.port] = current_time
        
        # Parse ACK/NACK response
        if len(response) >= 4:
            resp_seq, error_code, ack_nack = struct.unpack('>HBB', response)
            if ack_nack == 0:  # NACK
                error_messages = {
                    0x31: "IRNetBox is busy on one or more requested ports",
                    0x32: "IRNetBox processor message queue is full", 
                    0x33: "IR signal modulation frequency is too low (< 5KHz)",
                    0x34: "IR signal modulation frequency is too high (> 490KHz)",
                    0x35: "IR signal data section size is too large (max 2048 bytes)",
                    0x36: "Invalid signal data - too many EOS or EOR markers",
                    0x37: "Too many length values in the IR signal data"
                }
                error_msg = error_messages.get(error_code, f"Unknown error code: {error_code}")
                raise IRNetBoxError(f"Async command rejected: {error_msg}")
        
        return sequence_number
    
    def wait_for_async_completion(self, sequence_number: int, timeout: float = 10.0) -> bool:
        """
        Wait for async IR output completion (MK-III only).
        
        Args:
            sequence_number: Sequence number to wait for
            timeout: Timeout in seconds
            
        Returns:
            True if completed successfully, False if timeout
        """
        if self.device_type != IRNetBoxType.MK_III:
            return True  # Non-async devices complete immediately
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check for completion message
                self.socket.settimeout(0.1)  # Short timeout for non-blocking check
                
                # Read message header
                header = self.socket.recv(3)
                if len(header) == 3:
                    length, msg_type = struct.unpack('>HB', header)
                    
                    if msg_type == self.MSG_ASYNC_COMPLETE and length >= 4:
                        # Read completion data
                        data = self.socket.recv(length)
                        if len(data) >= 2:
                            completed_seq = struct.unpack('<H', data[:2])[0]  # Little-endian
                            if completed_seq == sequence_number:
                                return True
                                
            except socket.timeout:
                continue
            except Exception:
                break
        
        return False  # Timeout
    
    def enable_all_outputs(self):
        """Enable all IR outputs at low power."""
        self._send_cpld_instruction(self.CPLD_ENABLE_ALL)
    
    def enable_port(self, port: int, power_level: PowerLevel = PowerLevel.MEDIUM):
        """
        Enable a specific IR output port with the specified power level.
        This is the explicit enable step that activates the port.
        
        Args:
            port: Port number (1-16) to enable
            power_level: Power level for the port. Defaults to MEDIUM.
        """
        if not 1 <= port <= 16:
            raise ValueError("Port must be between 1 and 16")
            
        # Set the power level (which also enables the port)
        self.set_output_power(port, power_level)
        
        # For advanced devices, also enable in output mask
        # MK-IV is MK-III compatible
        if self.device_type in [IRNetBoxType.MK_II, IRNetBoxType.MK_III, IRNetBoxType.MK_IV]:
            # Set the output mask to enable this specific port
            output_configs = [OutputConfig(port=port, power_level=power_level)]
            self.set_output_mask(output_configs)
    
    def reset_outputs(self):
        """Reset all outputs (turn off) - only for CPLD devices."""
        if self.device_type in [IRNetBoxType.MK_I, IRNetBoxType.MK_II, IRNetBoxType.UNKNOWN]:
            self._send_cpld_instruction(self.CPLD_RESET)
    
    def reset_device(self):
        """
        Reset the device to clear any busy/error states.
        This is useful when commands start failing with busy or unknown errors.
        """
        try:
            # For CPLD devices, reset the CPLD
            if self.device_type in [IRNetBoxType.MK_I, IRNetBoxType.MK_II, IRNetBoxType.UNKNOWN]:
                self._send_cpld_instruction(self.CPLD_RESET)
                time.sleep(0.1)  # Brief pause after reset
                # Re-enable LED reflection
                self._send_cpld_instruction(self.CPLD_LED_REFLECT)
            
            # For all devices, allocate fresh memory
            self.allocate_signal_memory()
            
            print("Device reset completed")
            
        except Exception as e:
            print(f"Warning: Device reset failed: {e}")
    
    def reset_network_connection(self):
        """
        Reset the network connection to clear any connection state issues.
        This includes closing and reopening the TCP connection.
        """
        print("🔄 Resetting network connection...")
        
        old_ip = self.ip_address
        
        try:
            # Close existing connection
            if self.socket:
                self.socket.close()
                self.socket = None
            
            # Wait a moment for the connection to fully close
            time.sleep(0.5)
            
            # Reconnect
            self.connect(old_ip)
            
            print("✅ Network connection reset successful")
            return True
            
        except Exception as e:
            print(f"❌ Network connection reset failed: {e}")
            return False
    
    def full_reset(self):
        """
        Perform a comprehensive reset of both network and device state.
        Use this when experiencing persistent communication errors.
        """
        print("🔄 Performing full device and network reset...")
        
        try:
            # Step 1: Reset network connection
            if not self.reset_network_connection():
                return False
            
            # Step 2: Reset device state
            self.reset_device()
            
            # Step 3: Clear any cached state
            self.toggle_states.clear()
            self.port_last_used.clear()
            
            print("✅ Full reset completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Full reset failed: {e}")
            return False
    
    def configure_port(self, port: int, power_level: PowerLevel = PowerLevel.MEDIUM) -> bool:
        """
        Properly configure and enable a specific IR output port.
        This method ensures the port is reset, configured, and enabled correctly.
        
        Args:
            port: Port number (1-16) 
            power_level: Power level to configure. Defaults to MEDIUM.
            
        Returns:
            bool: True if configuration was successful
        """
        try:
            # Step 1: Reset all outputs to ensure clean state
            self.reset_outputs()
            
            # Step 2: Enable the specific port with proper power level
            self.enable_port(port, power_level)
            
            # Step 3: Verify port is properly configured (enable_port already handles mask)
            # This ensures the port is ready for signal transmission
            
            return True
            
        except Exception as e:
            print(f"Warning: Port configuration failed: {e}")
            return False
    
    def detect_signal_protocol(self, signal: IRSignal) -> dict:
        """
        Analyze an IR signal and detect its likely protocol characteristics.
        
        Args:
            signal: IRSignal to analyze
            
        Returns:
            dict: Protocol information including recommended power level
        """
        freq = signal.modulation_freq
        
        protocol_info = {
            'name': 'Unknown IR Protocol',
            'frequency': freq,
            'recommended_power': PowerLevel.MEDIUM,
            'characteristics': [],
            'confidence': 'Low'
        }
        
        # Analyze frequency ranges for common IR protocols
        if 35000 <= freq <= 40000:
            if 36000 <= freq <= 38000:
                protocol_info.update({
                    'name': 'NEC/RC5 (Consumer Electronics)',
                    'recommended_power': PowerLevel.HIGH,
                    'confidence': 'High'
                })
                protocol_info['characteristics'].append('Standard consumer IR frequency')
            else:
                protocol_info.update({
                    'name': 'Consumer IR Protocol',
                    'recommended_power': PowerLevel.HIGH,
                    'confidence': 'Medium'
                })
        elif 30000 <= freq < 35000:
            protocol_info.update({
                'name': 'Alternative Consumer Protocol',
                'recommended_power': PowerLevel.MEDIUM,
                'confidence': 'Medium'
            })
        elif freq < 30000:
            protocol_info.update({
                'name': 'Low Frequency IR Protocol', 
                'recommended_power': PowerLevel.HIGH,
                'confidence': 'Medium'
            })
            protocol_info['characteristics'].append('Low frequency - may need high power')
        elif freq > 40000:
            protocol_info.update({
                'name': 'High Frequency IR Protocol',
                'recommended_power': PowerLevel.MEDIUM,
                'confidence': 'Medium'  
            })
        
        # Add characteristics based on signal properties
        if signal.no_repeats > 1:
            protocol_info['characteristics'].append(f'Repeat count: {signal.no_repeats}')
        
        if signal.intra_sig_pause > 100:
            protocol_info['characteristics'].append('Long inter-signal pause')
        
        if len(signal.lengths) > 10:
            protocol_info['characteristics'].append('Complex timing pattern')
        elif len(signal.lengths) <= 4:
            protocol_info['characteristics'].append('Simple timing pattern')
        
        return protocol_info
    
    def download_signal(self, signal: IRSignal, max_lengths: int = 16, max_data_size: int = 512) -> bytes:
        """
        Convert IR signal to binary format for download to IRNetBox.
        Returns the binary signal data that can be sent with MSG_DOWNLOAD_SIGNAL.
        
        If the signal has toggle data, this method will apply the current toggle state
        and update the toggle state for the next transmission.
        """
        # Apply toggle data if present
        modified_sig_data = self._apply_toggle_data(signal)
        
        # Convert modulation frequency to timer count (6MHz timer)
        # Use floating-point division for more accurate timer calculation
        timer_value = int(65536 - (6000000.0 / signal.modulation_freq))
        
        # Convert lengths from ms to 2MHz timer counts
        length_values = []
        for length_ms in signal.lengths:
            length_count = int((length_ms / 1000.0) * 2000000)
            length_values.append(length_count)
        
        # Pad length array to max_lengths
        while len(length_values) < max_lengths:
            length_values.append(0)
        
        # Convert intra-signal pause to 2MHz timer count
        pause_count = int((signal.intra_sig_pause / 1000.0) * 2000000)
        
        # Build signal data structure (all values big-endian except where noted)
        signal_data = struct.pack('>I', pause_count)  # Intra-signal pause
        signal_data += struct.pack('>H', timer_value)  # Modulation frequency timer count
        signal_data += struct.pack('>H', 0)  # No. of periods (0 for download)
        signal_data += struct.pack('B', max_lengths)  # Maximum number of lengths
        signal_data += struct.pack('B', len(signal.lengths))  # Actual number of lengths
        signal_data += struct.pack('>H', max_data_size)  # Maximum signal data size
        signal_data += struct.pack('>H', len(modified_sig_data))  # Actual signal data size
        signal_data += struct.pack('B', signal.no_repeats)  # Number of repeats
        
        # Add length data array (big-endian ushorts)
        for length_val in length_values:
            signal_data += struct.pack('>H', min(length_val, 65535))
        
        # Add signal data (potentially modified by toggle data)
        signal_data += modified_sig_data
        
        return signal_data
    
    def _apply_toggle_data(self, signal: IRSignal) -> bytes:
        """
        Apply toggle data to signal data if present.
        
        Toggle data contains bits that alternate each time the signal is output.
        Each ToggleBit specifies a bit number (offset in signal data) and two
        values (len1, len2) that alternate on each transmission.
        
        Args:
            signal: IR signal with potential toggle data
            
        Returns:
            Modified signal data bytes with current toggle state applied
        """
        if not signal.toggle_data:
            return signal.sig_data
        
        # Convert signal data to mutable bytearray
        modified_data = bytearray(signal.sig_data)
        signal_uid = signal.uid
        
        # Initialize toggle state for this signal if not present
        if signal_uid not in self.toggle_states:
            # Start with len1 values (False = use len1, True = use len2)
            self.toggle_states[signal_uid] = {bit_no: False for bit_no in signal.toggle_data.keys()}
        
        # Apply current toggle state
        for bit_no, (len1, len2) in signal.toggle_data.items():
            if bit_no < len(modified_data):
                current_state = self.toggle_states[signal_uid][bit_no]
                if current_state:
                    modified_data[bit_no] = len2  # Use second value
                else:
                    modified_data[bit_no] = len1  # Use first value
        
        # Toggle state for next transmission
        for bit_no in signal.toggle_data.keys():
            self.toggle_states[signal_uid][bit_no] = not self.toggle_states[signal_uid][bit_no]
        
        return bytes(modified_data)
    
    def reset_toggle_states(self, signal_uid: str = None):
        """
        Reset toggle states to initial values.
        
        Args:
            signal_uid: UID of specific signal to reset, or None to reset all
        """
        if signal_uid is None:
            # Reset all toggle states
            self.toggle_states.clear()
        elif signal_uid in self.toggle_states:
            # Reset specific signal's toggle state
            for bit_no in self.toggle_states[signal_uid]:
                self.toggle_states[signal_uid][bit_no] = False
    
    def send_signal(self, signal: IRSignal, outputs: List[int] = None, power_level: PowerLevel = PowerLevel.MEDIUM,
                   use_async: bool = None):
        """
        Send an IR signal through specified outputs.
        
        Args:
            signal: IR signal to send
            outputs: List of output numbers (1-16), or None for output 1 only
            power_level: Power level for all specified outputs. Defaults to MEDIUM.
            use_async: Use async mode if available (MK-III), None for auto-detect
        """
        if not outputs:
            outputs = [1]
        
        # Auto-detect async mode based on device type
        if use_async is None:
            # MK-III and MK-IV support async mode
            use_async = (self.device_type in [IRNetBoxType.MK_III, IRNetBoxType.MK_IV])
        
        # Convert to output configurations
        output_configs = [OutputConfig(port=port, power_level=power_level) for port in outputs]
        
        try:
            if use_async and self.device_type in [IRNetBoxType.MK_III, IRNetBoxType.MK_IV]:
                # Use async mode with automatic timing enforcement and longer post-delay for slow STBs
                seq_num = self.send_signal_async(signal, output_configs, enforce_timing=True, post_delay_ms=500)
                print(f"Signal '{signal.name}' queued for async transmission (seq: {seq_num})")
                
                # Wait for completion
                if self.wait_for_async_completion(seq_num, timeout=5.0):
                    print(f"Signal '{signal.name}' sent successfully")
                else:
                    print(f"Warning: Async signal completion timeout (seq: {seq_num})")
            else:
                # Use synchronous mode
                self._send_signal_sync(signal, output_configs)
                print(f"Signal '{signal.name}' sent successfully")
                
        except Exception as e:
            raise IRNetBoxError(f"Failed to send signal: {e}")
    
    def send_signal_fast(self, signal: IRSignal, port: int, power_level: PowerLevel = PowerLevel.HIGH, 
                        max_retries: int = 3):
        """
        Send an IR signal with automatic timing management and retry logic for MK-IV devices.
        This method handles port timing automatically and retries on errors - use this for reliable operation.
        
        Args:
            signal: IR signal to send
            port: Output port number (1-16)
            power_level: Power level for the output. Defaults to HIGH.
            max_retries: Maximum number of retry attempts. Defaults to 3.
            
        Returns:
            bool: True if signal was sent successfully
        """
        output_configs = [OutputConfig(port=port, power_level=power_level)]
        
        for attempt in range(max_retries + 1):
            try:
                if self.device_type == IRNetBoxType.MK_IV:
                    # Use async mode with timing enforcement and longer post-delay for slow STBs
                    seq_num = self.send_signal_async(signal, output_configs, enforce_timing=True, post_delay_ms=500)
                    self.wait_for_async_completion(seq_num, timeout=3.0)
                    return True
                else:
                    # Fallback to regular send for other devices
                    self.send_signal(signal, [port], power_level)
                    return True
                    
            except IRNetBoxError as e:
                error_msg = str(e)
                
                # Handle different error types with appropriate delays for slow STBs
                if "busy" in error_msg.lower():
                    retry_delay = 5.0 + (attempt * 2.0)  # Progressive delay: 5s, 7s, 9s, 11s
                    if attempt < max_retries:
                        print(f"   ⚠️  Port {port} busy, retry {attempt + 1}/{max_retries} in {retry_delay:.1f}s...")
                        time.sleep(retry_delay)
                        continue
                        
                elif "unknown error code: 0" in error_msg:
                    retry_delay = 8.0 + (attempt * 3.0)  # Progressive delay: 8s, 11s, 14s, 17s
                    if attempt < max_retries:
                        print(f"   ⚠️  Queue overflow, retry {attempt + 1}/{max_retries} in {retry_delay:.1f}s...")
                        time.sleep(retry_delay)
                        continue
                        
                elif "message queue is full" in error_msg:
                    retry_delay = 10.0 + (attempt * 5.0)  # Progressive delay: 10s, 15s, 20s, 25s
                    if attempt < max_retries:
                        print(f"   ⚠️  Queue full, retry {attempt + 1}/{max_retries} in {retry_delay:.1f}s...")
                        time.sleep(retry_delay)
                        continue
                else:
                    # For other errors, don't retry
                    print(f"Error sending signal '{signal.name}': {e}")
                    return False
                    
            except Exception as e:
                print(f"Unexpected error sending signal '{signal.name}': {e}")
                return False
        
        # All retries exhausted
        print(f"❌ Failed to send signal '{signal.name}' after {max_retries + 1} attempts")
        return False
    
    def send_signal_robust(self, signal: IRSignal, port: int, power_level: PowerLevel = PowerLevel.HIGH,
                          max_retries: int = 2, base_delay: float = 2.0, enable_network_reset: bool = True):
        """
        Send an IR signal with comprehensive error handling and retry logic.
        This is the most robust method for sending signals.
        
        Args:
            signal: IR signal to send
            port: Output port number (1-16)
            power_level: Power level for the output. Defaults to HIGH.
            max_retries: Maximum number of retry attempts. Defaults to 2.
            base_delay: Base delay for retries in seconds. Defaults to 2.0.
            enable_network_reset: Whether to reset network connection on persistent errors.
            
        Returns:
            dict: Result with success status and details
        """
        result = {
            'success': False,
            'attempts': 0,
            'total_time': 0.0,
            'error': None,
            'network_reset_used': False
        }
        
        start_time = time.time()
        output_configs = [OutputConfig(port=port, power_level=power_level)]
        consecutive_failures = 0
        
        for attempt in range(max_retries + 1):
            result['attempts'] = attempt + 1
            
            try:
                if self.device_type == IRNetBoxType.MK_IV:
                    seq_num = self.send_signal_async(signal, output_configs, enforce_timing=True, post_delay_ms=500)
                    self.wait_for_async_completion(seq_num, timeout=3.0)
                    result['success'] = True
                    break
                else:
                    self.send_signal(signal, [port], power_level)
                    result['success'] = True
                    break
                    
            except IRNetBoxError as e:
                error_msg = str(e)
                result['error'] = error_msg
                consecutive_failures += 1
                
                # Check if we should try network reset
                if (enable_network_reset and consecutive_failures >= 2 and 
                    attempt < max_retries and
                    ("timeout" in error_msg.lower() or "connection" in error_msg.lower() or consecutive_failures >= 3)):
                    
                    print(f"   🔌 Network issues detected, attempting connection reset...")
                    if self.reset_network_connection():
                        result['network_reset_used'] = True
                        consecutive_failures = 0  # Reset failure counter
                        time.sleep(1.0)  # Brief pause after reset
                        continue
                
                if attempt < max_retries:
                    # Calculate retry delay based on error type - generous delays for slow STBs
                    if "busy" in error_msg.lower():
                        retry_delay = base_delay + (attempt * 2.0)  # 2s, 4s, 6s
                    elif "unknown error code: 0" in error_msg:
                        retry_delay = base_delay + (attempt * 3.0)  # 2s, 5s, 8s
                    elif "queue" in error_msg.lower():
                        retry_delay = base_delay + (attempt * 4.0)  # 2s, 6s, 10s
                    else:
                        retry_delay = base_delay + (attempt * 2.0)  # Default: generous delays
                    
                    print(f"   🔄 Retry {attempt + 1}/{max_retries} in {retry_delay:.1f}s...")
                    time.sleep(retry_delay)
                else:
                    break
                    
            except Exception as e:
                result['error'] = str(e)
                consecutive_failures += 1
                
                # Try network reset for connection-related exceptions
                if (enable_network_reset and consecutive_failures >= 2 and 
                    attempt < max_retries):
                    print(f"   🔌 Connection error detected, attempting reset...")
                    if self.reset_network_connection():
                        result['network_reset_used'] = True
                        consecutive_failures = 0
                        time.sleep(1.0)
                        continue
                break
        
        result['total_time'] = time.time() - start_time
        return result
    
    def _send_signal_sync(self, signal: IRSignal, output_configs: List[OutputConfig]):
        """Send signal synchronously (all device types)."""
        # Allocate memory if needed
        self.allocate_signal_memory()
        
        # Configure outputs
        if len(output_configs) > 1 and self.device_type in [IRNetBoxType.MK_II, IRNetBoxType.MK_III]:
            # Use bit mask for multiple outputs on MK-II/III
            self.set_output_mask(output_configs)
        else:
            # Use individual commands - only reset outputs for devices with CPLD (MK-I/MK-II)
            if self.device_type in [IRNetBoxType.MK_I, IRNetBoxType.MK_II]:
                self.reset_outputs()  # Start fresh - only for CPLD devices
            for config in output_configs:
                self.set_output_power(config.port, config.power_level)
        
        # Download signal data
        signal_data = self.download_signal(signal)
        self._send_message(self.MSG_DOWNLOAD_SIGNAL, signal_data)
        
        # Output signal
        self._send_message(self.MSG_OUTPUT_SIGNAL, b'')
    
    def get_device_info(self) -> Dict[str, str]:
        """Get device information."""
        return {
            'ip_address': self.ip_address or 'Unknown',
            'device_type': self.device_type.value,
            'serial_number': self.serial_number or 'Unknown',
            'firmware_version': self.firmware_version or 'Unknown'
        }
    
    def get_memory_parameters(self) -> Dict[str, int]:
        """Get signal capture and memory parameters."""
        try:
            response = self._send_message(self.MSG_READ_PARAMS, b'')
            if len(response) >= 24:  # Expected parameter structure size
                import struct
                # Unpack the parameter structure (big-endian format)
                params = struct.unpack('>6I', response[:24])
                return {
                    'max_lengths': params[0],
                    'signal_data_size': params[1],
                    'carrier_periods': params[2],
                    'length_fuzz': params[3],
                    'pause_timeout': params[4],
                    'min_pause': params[5]
                }
            else:
                return {}
        except Exception as e:
            print(f"Warning: Could not read memory parameters: {e}")
            return {}
    
    def set_memory_parameters(self, max_lengths: int = None, signal_data_size: int = None,
                            carrier_periods: int = None, length_fuzz: int = None,
                            pause_timeout: int = None, min_pause: int = None):
        """Set signal capture and memory parameters.
        
        Args:
            max_lengths: Maximum number of length values allowed (default: keep current)
            signal_data_size: Size of memory for signal data array (default: keep current)
            carrier_periods: Periods of carrier wave to measure (default: keep current) 
            length_fuzz: Length measurement tolerance (default: keep current)
            pause_timeout: Pause measurement timeout (default: keep current)
            min_pause: Minimum pause value (default: keep current)
        """
        try:
            # Get current parameters first
            current = self.get_memory_parameters()
            if not current:
                # Use protocol defaults if we can't read current values
                current = {
                    'max_lengths': 256,
                    'signal_data_size': 512,
                    'carrier_periods': 8,
                    'length_fuzz': 112,
                    'pause_timeout': 300000,
                    'min_pause': 115
                }
            
            # Update only specified parameters
            params = [
                max_lengths if max_lengths is not None else current.get('max_lengths', 256),
                signal_data_size if signal_data_size is not None else current.get('signal_data_size', 512),
                carrier_periods if carrier_periods is not None else current.get('carrier_periods', 8),
                length_fuzz if length_fuzz is not None else current.get('length_fuzz', 112),
                pause_timeout if pause_timeout is not None else current.get('pause_timeout', 300000),
                min_pause if min_pause is not None else current.get('min_pause', 115)
            ]
            
            import struct
            # Pack parameters in big-endian format
            param_data = struct.pack('>6I', *params)
            self._send_message(self.MSG_SET_PARAMS, param_data)
            
        except Exception as e:
            raise IRNetBoxError(f"Failed to set memory parameters: {e}")


class IRSignalParser:
    """Parser for RedRat XML signal database files."""
    
    @staticmethod
    def parse_xml_file(file_path: str) -> List[AVDevice]:
        """Parse XML file and return list of AV devices."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            devices = []
            
            for device_elem in root.findall('.//AVDevice'):
                name = device_elem.find('Name').text or 'Unknown'
                manufacturer = device_elem.find('Manufacturer').text or 'Unknown'
                device_model = device_elem.find('DeviceModelNumber').text or 'Unknown'
                remote_model = device_elem.find('RemoteModelNumber').text or 'Unknown'
                device_type = device_elem.find('DeviceType').text or 'Unknown'
                
                signals = []
                
                for signal_elem in device_elem.findall('.//IRPacket'):
                    signal = IRSignalParser._parse_signal(signal_elem)
                    if signal:
                        signals.append(signal)
                
                device = AVDevice(
                    name=name,
                    manufacturer=manufacturer,
                    device_model=device_model,
                    remote_model=remote_model,
                    device_type=device_type,
                    signals=signals
                )
                devices.append(device)
            
            return devices
            
        except Exception as e:
            raise IRNetBoxError(f"Failed to parse XML file: {e}")
    
    @staticmethod
    def _parse_signal(signal_elem) -> Optional[IRSignal]:
        """Parse individual IR signal from XML element."""
        try:
            # Check if this is a DoubleSignal type
            xsi_type = signal_elem.get('{http://www.w3.org/2001/XMLSchema-instance}type')
            is_double_signal = xsi_type == 'DoubleSignal'
            
            if is_double_signal:
                # For DoubleSignal, get the main name but parse Signal1 for the actual signal data
                main_name_elem = signal_elem.find('Name')
                main_uid_elem = signal_elem.find('UID')
                
                # Use Signal1 as the primary signal data
                signal1_elem = signal_elem.find('Signal1')
                if signal1_elem is None:
                    return None
                
                # Extract signal data from Signal1
                name_elem = main_name_elem  # Use main command name
                uid_elem = main_uid_elem    # Use main UID
                mod_freq_elem = signal1_elem.find('ModulationFreq')
                sig_data_elem = signal1_elem.find('SigData')
                no_repeats_elem = signal1_elem.find('NoRepeats')
                pause_elem = signal1_elem.find('IntraSigPause')
                lengths_elem = signal1_elem.find('Lengths')
                toggle_elem = signal1_elem.find('ToggleData')
            else:
                # Regular signal parsing
                name_elem = signal_elem.find('Name')
                uid_elem = signal_elem.find('UID')
                mod_freq_elem = signal_elem.find('ModulationFreq')
                sig_data_elem = signal_elem.find('SigData')
                no_repeats_elem = signal_elem.find('NoRepeats')
                pause_elem = signal_elem.find('IntraSigPause')
                lengths_elem = signal_elem.find('Lengths')
                toggle_elem = signal_elem.find('ToggleData')
            
            if not all([name_elem is not None, mod_freq_elem is not None, sig_data_elem is not None]):
                return None
            name = name_elem.text
            uid = uid_elem.text if uid_elem is not None else ''
            modulation_freq = int(float(mod_freq_elem.text))
            no_repeats = int(no_repeats_elem.text) if no_repeats_elem is not None else 1
            intra_sig_pause = float(pause_elem.text) if pause_elem is not None else 0.0
            
            # Parse lengths
            lengths = []
            if lengths_elem is not None:
                for length_elem in lengths_elem.findall('double'):
                    lengths.append(float(length_elem.text))
            
            # Decode base64 signal data
            sig_data = base64.b64decode(sig_data_elem.text)
            
            # Parse toggle data if present
            toggle_data = None
            if toggle_elem is not None:
                toggle_data = {}
                for toggle_bit in toggle_elem.findall('ToggleBit'):
                    bit_no = int(toggle_bit.find('bitNo').text)
                    len1 = int(toggle_bit.find('len1').text)
                    len2 = int(toggle_bit.find('len2').text)
                    toggle_data[bit_no] = (len1, len2)
            
            return IRSignal(
                name=name,
                uid=uid,
                modulation_freq=modulation_freq,
                lengths=lengths,
                sig_data=sig_data,
                no_repeats=no_repeats,
                intra_sig_pause=intra_sig_pause,
                toggle_data=toggle_data
            )
            
        except Exception as e:
            print(f"Warning: Failed to parse signal: {e}")
            return None
