# -*- coding: utf-8 -*-

"""Python module to control the RedRat irNetBox infrared emitter.

Author: David Rothlisberger <david@rothlis.net>
Copyright 2012 YouView TV Ltd and contributors.
License: LGPL v2.1 or (at your option) any later version (see
https://github.com/stb-tester/stb-tester/blob/master/LICENSE for details).

Enhanced for RedRat Proxy with logging and protocol optimizations.

The irNetBox is a network-controlled infrared emitter:
http://www.redrat.co.uk/products/irnetbox.html

This module supports versions II, III, and IV of the irNetBox hardware.

"§" section numbers in the function docstrings are from "The irNetBox
Network Control Protocol":
http://www.redrat.co.uk/products/IRNetBox_Comms-V3.0.pdf

Thanks to Chris Dodge at RedRat for friendly and prompt answers to all my
questions, and to Emmett Kelly for the mk-II implementation.

Classes:

IRNetBox
  An instance of IRNetBox holds a TCP connection to the device.

  Note that the device only accepts one TCP connection at a time, so keep this
  as short-lived as possible. For example::

    with irnetbox.IRNetBox("192.168.0.10") as ir:
        ir.power_on()
        ir.irsend_raw(port=1, power=100, data=binascii.unhexlify("000174F..."))

  Or run './irnetbox-proxy', which accepts multiple connections and forwards
  requests on to a real irNetBox.

RemoteControlConfig
  Holds infrared signal data from a config file produced by RedRat's "IR Signal
  Database Utility". Example usage (where "POWER" is a signal defined in the
  config file)::

    rcu = irnetbox.RemoteControlConfig("my-rcu.irnetbox.config")
    ir.irsend_raw(port=1, power=100, data=rcu["POWER"])

"""

import binascii
import errno
import logging
import random
import re
import socket
import struct
import sys
import time

# Set up logging for redratlib
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler if no handlers exist
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class IRNetBox():
    def __init__(self, hostname, port=10001):  # §5
        logger.info(f"Initializing IRNetBox connection to {hostname}:{port}")
        self._socket = None
        self._responses = None
        self.irnetbox_model = 0
        self.ports = 16
        
        for i in range(6):
            try:
                logger.debug(f"Connection attempt {i+1}/6 to {hostname}:{port}")
                self._socket = socket.socket()
                self._socket.settimeout(10)
                self._socket.connect((hostname, port))
                logger.info(f"Successfully connected to {hostname}:{port}")
                break
            except socket.error as e:
                logger.warning(f"Connection attempt {i+1} failed: {e}")
                if e.errno == errno.ECONNREFUSED and i < 5:
                    delay = 0.1 * (2 ** i)
                    logger.info(f"Connection refused, retrying in {delay:.2f}s")
                    sys.stderr.write(
                        "Connection to irNetBox '%s:%d' refused; "
                        "retrying in %.2fs.\n" %
                        (hostname, port, delay))
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to connect to {hostname}:{port} after {i+1} attempts")
                    raise
        
        if not self._socket:
            raise Exception(f"Failed to create socket connection to {hostname}:{port}")
            
        logger.debug("Setting up response reader")
        self._responses = _read_responses(self._socket)
        
        logger.debug("Getting device version")
        self._get_version()
        logger.info(f"IRNetBox initialized: model={self.irnetbox_model}, ports={self.ports}")
        logger.info(f"Device type: {NetBoxTypes.get_name(self.irnetbox_model)}")

    def __enter__(self):
        logger.debug("Entering IRNetBox context manager")
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        logger.debug("Exiting IRNetBox context manager")
        if ex_type:
            logger.error(f"Exception during IRNetBox context: {ex_type.__name__}: {ex_value}")
        if self._socket:
            logger.debug("Closing socket connection")
            self._socket.close()
        else:
            logger.warning("Socket was None during context exit")

    def close(self):
        """Explicit close method for non-context manager usage"""
        if self._socket:
            logger.debug("Explicitly closing socket connection")
            self._socket.close()
            self._socket = None
        else:
            logger.debug("Socket already closed or None")

    def get_device_info(self):
        """Get device information"""
        return {
            'model': self.irnetbox_model,
            'model_name': NetBoxTypes.get_name(self.irnetbox_model),
            'ports': self.ports
        }

    def power_on(self):
        """Power on the irNetBox device (§5.2.3).

        §5.2.3 calls this "power to the CPLD device"; the irNetBox-III doesn't
        have a CPLD, but according to Chris Dodge @ RedRat, this is now "power
        on the whole irNetBox".

        """
        logger.info("Powering on IRNetBox device")
        self._send(MessageTypes.POWER_ON)
        logger.debug("Power on command sent successfully")

    def power_off(self):
        """Put the irNetBox in low-power standby mode (§5.2.3).

        In low power mode the LEDs on the front will be doing the Cylon
        pattern.

        """
        logger.info("Powering off IRNetBox device")
        self._send(MessageTypes.POWER_OFF)
        logger.debug("Power off command sent successfully")

    def reset(self):
        """Reset the CPLD"""
        logger.info("Resetting IRNetBox CPLD")
        self._send(
            MessageTypes.CPLD_INSTRUCTION,
            struct.pack("B", 0x00))
        logger.debug("CPLD reset command sent successfully")

    def indicators_on(self):
        """Enable LED indicators on the front panel (§5.2.4)."""
        logger.info("Enabling LED indicators")
        self._send(
            MessageTypes.CPLD_INSTRUCTION,
            struct.pack("B", 0x17))
        logger.debug("LED indicators on command sent successfully")

    def indicators_off(self):
        """Disable LED indicators on the front panel (§5.2.4)."""
        logger.info("Disabling LED indicators")
        self._send(
            MessageTypes.CPLD_INSTRUCTION,
            struct.pack("B", 0x18))
        logger.debug("LED indicators off command sent successfully")

    def irsend_raw(self, port, power, data):
        """Output the IR data on the given port at the set power (§6.1.1).

        * `port` is a number between 1 and 16 (or 1 and 4 for RedRat X).
        * `power` is a number between 1 and 100.
        * `data` is a byte array as exported by the RedRat Signal DB Utility.

        """
        logger.info(f"Sending IR signal: port={port}, power={power}, data_length={len(data)}")
        logger.debug(f"Device model: {self.irnetbox_model} ({NetBoxTypes.get_name(self.irnetbox_model)})")
        logger.debug(f"Available ports: {self.ports}")
        
        # Validate inputs
        if not (1 <= port <= self.ports):
            error_msg = f"Invalid port {port}. Must be between 1 and {self.ports}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not (1 <= power <= 100):
            error_msg = f"Invalid power {power}. Must be between 1 and 100"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not data:
            error_msg = "IR data cannot be empty"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.debug(f"IR data hex: {binascii.hexlify(data[:50]).decode()}..." if len(data) > 50 else f"IR data hex: {binascii.hexlify(data).decode()}")
        
        if self.irnetbox_model == NetBoxTypes.MK1:
            error_msg = "IRNetBox MK1 not supported"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        elif self.irnetbox_model == NetBoxTypes.MK2:
            logger.debug("Using MK2 protocol")
            # Original MK2 implementation from stb-tester
            self.reset()
            self.indicators_on()
            self._send(MessageTypes.SET_MEMORY)
            self._send(MessageTypes.CPLD_INSTRUCTION, struct.pack("B", 0x00))
            if power < 33:
                self._send(
                    MessageTypes.CPLD_INSTRUCTION,
                    struct.pack("B", port + 1))
            elif power < 66:
                self._send(
                    MessageTypes.CPLD_INSTRUCTION,
                    struct.pack("B", port + 31))
            else:
                self._send(
                    MessageTypes.CPLD_INSTRUCTION,
                    struct.pack("B", port + 1))
                self._send(
                    MessageTypes.CPLD_INSTRUCTION,
                    struct.pack("B", port + 31))
            self._send(MessageTypes.DOWNLOAD_SIGNAL, data)
            self._send(MessageTypes.OUTPUT_IR_SIGNAL)
            self.reset()
            logger.info("MK2 IR signal sent successfully")
        else:
            # MK3/MK4/RRX - Use async mode like the official tool
            logger.debug(f"Using async protocol for model {self.irnetbox_model}")
            ports = [0] * self.ports
            ports[port - 1] = power
            sequence_number = random.randint(0, (2 ** 16) - 1)
            delay = 0  # use the default delay of 100ms
            
            logger.debug(f"Sequence number: {sequence_number}, delay: {delay}")
            logger.debug(f"Port configuration: {ports}")
            
            self._send(
                MessageTypes.OUTPUT_IR_ASYNC,
                struct.pack(
                    ">HH{0}s{1}s".format(self.ports, len(data)),
                    sequence_number,
                    delay,
                    struct.pack("{}B".format(self.ports), *ports),
                    data))
            logger.info("Async IR signal sent successfully")

    def _send(self, message_type, message_data=b""):
        logger.debug(f"Sending message: type={message_type:#04x}, data_length={len(message_data)}")
        
        try:
            message = _message(message_type, message_data)
            logger.debug(f"Formatted message length: {len(message)} bytes")
            if len(message) <= 100:  # Only log full hex for short messages
                logger.debug(f"Message hex: {binascii.hexlify(message).decode()}")
            
            self._socket.sendall(message)
            logger.debug("Message sent successfully")
            
            logger.debug("Waiting for response...")
            response_type, response_data = next(self._responses)
            logger.debug(f"Received response: type={response_type:#04x}, data_length={len(response_data)}")
            
            if response_data and len(response_data) <= 100:
                logger.debug(f"Response data hex: {binascii.hexlify(response_data).decode()}")
            
            if response_type == MessageTypes.ERROR:
                error_msg = "IRNetBox returned ERROR"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            if response_type != message_type:
                error_msg = f"IRNetBox returned unexpected response type {response_type:#04x} to request {message_type:#04x}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            if response_type == MessageTypes.OUTPUT_IR_ASYNC:
                logger.debug("Processing async IR response")
                sequence_number, error_code, ack = struct.unpack(
                    # Sequence number in the ACK message is defined as big-endian
                    # in §5.1 and §6.1.2, but due to a known bug it is
                    # little-endian.
                    '<HBB', response_data)
                logger.debug(f"Async response: seq={sequence_number}, error={error_code}, ack={ack}")
                
                if ack == 1:
                    logger.debug("Received ACK, waiting for completion message")
                    async_type, async_data = next(self._responses)
                    logger.debug(f"Async completion: type={async_type:#04x}, data_length={len(async_data)}")
                    
                    if async_type != MessageTypes.IR_ASYNC_COMPLETE:
                        error_msg = f"IRNetBox returned unexpected message {async_type:#04x}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                        
                    (async_sequence_number,) = struct.unpack(">H", async_data[:2])
                    logger.debug(f"Async completion sequence number: {async_sequence_number}")
                    
                    if async_sequence_number != sequence_number:
                        error_msg = f"IRNetBox returned message IR_ASYNC_COMPLETE with unexpected sequence number {async_sequence_number} (expected {sequence_number})"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    logger.debug("Async IR operation completed successfully")
                else:
                    error_msg = f"IRNetBox returned NACK (error code: {error_code})"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
            if response_type == MessageTypes.DEVICE_VERSION:
                logger.debug("Processing device version response")
                if len(response_data) >= 12:
                    self.irnetbox_model, = struct.unpack(
                        '<H', response_data[10:12])  # == §5.2.6's payload_data[8:10]
                    logger.debug(f"Device model extracted: {self.irnetbox_model} ({NetBoxTypes.get_name(self.irnetbox_model)})")
                else:
                    logger.warning(f"Device version response too short: {len(response_data)} bytes")
                    
            logger.debug("Message processed successfully")
            
        except Exception as e:
            logger.error(f"Error in _send: {e}")
            raise

    def _get_version(self):
        logger.debug("Getting device version")
        self._send(MessageTypes.DEVICE_VERSION)
        
        # Set port count based on device model
        if self.irnetbox_model == NetBoxTypes.RRX:
            self.ports = 4
            logger.debug(f"RRX device detected, setting ports to {self.ports}")
        else:
            self.ports = 16
            logger.debug(f"Standard device detected, setting ports to {self.ports}")
            
        logger.info(f"Device version retrieved: model={self.irnetbox_model}, ports={self.ports}")


def RemoteControlConfig(filename):
    """Read irNetBox configuration file and return signal dictionary."""
    logger.info(f"Loading remote control config from: {filename}")
    try:
        with open(filename, "rb") as f:
            config = _parse_config(f)
            logger.info(f"Loaded {len(config)} signals from config file")
            logger.debug(f"Available signals: {list(config.keys())}")
            return config
    except Exception as e:
        logger.error(f"Failed to load remote control config: {e}")
        raise


class MessageTypes():
    """§5.2"""
    ERROR = 0x01
    POWER_ON = 0x05
    POWER_OFF = 0x06
    CPLD_INSTRUCTION = 0x07
    DEVICE_VERSION = 0x09
    SET_MEMORY = 0x10
    DOWNLOAD_SIGNAL = 0x11
    OUTPUT_IR_SIGNAL = 0x12
    OUTPUT_IR_ASYNC = 0x30
    IR_ASYNC_COMPLETE = 0x31


class NetBoxTypes():
    """§5.2.6"""
    MK1 = 2
    MK2 = 7
    MK3 = 8
    MK4 = 12
    RRX = 13

    @classmethod
    def get_name(cls, value):
        """Get the friendly name for a NetBoxType value"""
        name_map = {
            cls.MK1: "RedRat MK1",
            cls.MK2: "RedRat MK2", 
            cls.MK3: "RedRat MK3",
            cls.MK4: "RedRat MK4",
            cls.RRX: "RedRat RRX"
        }
        return name_map.get(value, f"Unknown ({value})")


def _message(message_type, message_data):
    # §5.1. Message Structure: Host to irNetBox
    #
    # '#'              byte     The '#' character indicates to the control
    #                           microprocessor the start of a message.
    # Message length   ushort   The length of the data section of this message.
    # Message type     byte     One of the values listed below.
    # Data             byte[]   Any data associated with this type of message.
    #
    # A ushort value is a 16-bit unsigned integer in big-endian format.
    #
    return struct.pack(
        ">cHB%ds" % len(message_data),
        b"#",
        len(message_data),
        message_type,
        message_data)


def _read_responses(stream):
    """Generator that splits stream into (type, data) tuples."""

    # §5.1. Message Structure: irNetBox to Host
    #
    # Message length   ushort   The length of the data section of this message.
    # Message type     byte     Contains either:
    #                           a) The same value as the original message from
    #                              the host, or
    #                           b) A value (0x01) indicating "Error".
    # Data             byte[]   Any data associated with this type of message.
    #
    buf = b""
    while True:
        s = stream.recv(4096)
        if len(s) == 0:
            break
        buf += s
        while len(buf) >= 3:
            data_len, = struct.unpack(">H", buf[0:2])
            if len(buf) < 3 + data_len:
                break
            response_type, response_data = struct.unpack(
                ">B%ds" % data_len,
                buf[2:(3 + data_len)])
            yield response_type, response_data
            buf = buf[(3 + data_len):]


def _parse_config(config_file):
    """Read irNetBox configuration file.

    Which is produced by RedRat's (Windows-only) "IR Signal Database Utility".
    """
    d = {}
    for line in config_file:
        fields = re.split(b"[\t ]+", line.rstrip(), maxsplit=4)
        if len(fields) == 4:
            # (name, type, max_num_lengths, data)
            name, type_, _, data = fields
            if type_ == b"MOD_SIG":
                d[name.decode("utf-8")] = binascii.unhexlify(data)
        if len(fields) == 5:
            # "Double signals" where pressing the button on the remote control
            # alternates between signal1 & signal2. We'll always send signal1,
            # but that shouldn't matter.
            # (name, type, signal1 or signal2, max_num_lengths, data)
            name, type_, signal, _, data = fields
            if type_ == b"DMOD_SIG" and signal == b"signal1":
                d[name.decode("utf-8")] = binascii.unhexlify(data)
    return d


# Tests
# ===========================================================================

def test_that_read_responses_doesnt_hang_on_incomplete_data():
    import io

    data = b"abcdefghij"
    m = struct.pack(
        ">HB%ds" % len(data),
        len(data),
        0x01,
        data)

    assert next(_read_responses(_FileToSocket(io.BytesIO(m)))) == \
        (0x01, data)
    try:
        next(_read_responses(_FileToSocket(io.BytesIO(m[:5]))))
    except StopIteration:
        pass
    else:
        assert False  # expected StopIteration exception


def test_that_parse_config_understands_redrat_format():
    import io

    f = io.BytesIO(
        re.sub(
            b"^ +", b"", flags=re.MULTILINE,
            string=b"""Device TestRCU

            Note: The data is of the form <signal name> MOD_SIG <max_num_lengths> <byte_array_in_ascii_hex>.

            DOWN	MOD_SIG	16	000174F5FF600000000600000048024502222F704540D12116A464F00000000000000000000000000000000000000000001020202020202020202020202020202020202020202030202020202020202020202030202020202020203020202030203020202030203020302020203027F0004027F

            UP	MOD_SIG	16	000174FAFF60000000050000004803457422F7045A0D13116A000000000000000000000000000000000000000000000102020202020202020202020202020202020202020202020202030202020202020303020202020202020202020203020202020203020302030203020302020203027F0004027F

            RED	DMOD_SIG	signal1	16	0002BCAFFF5A000000030000002401034E3206E60DB1000000000000000000000000000000000000000000000000000001010101020002000200020002010101017F00010101010200020002000200020101017F
            RED	DMOD_SIG	signal2	16	0002BCE3FF5A00000003000000240010E2C0DB006EC0000000000000000000000000000000000000000000000000000000100010001000100010001020202027F0001000100010001000100010202027F

          """))
    config = _parse_config(f)
    assert config["DOWN"].startswith(b"\x00\x01\x74\xF5")
    assert config["UP"].startswith(b"\x00\x01\x74\xFA")
    assert config["RED"].startswith(b"\x00\x02\xBC\xAF")


class _FileToSocket():
    """Makes something File-like behave like a Socket for testing purposes.

    >>> import io
    >>> s = _FileToSocket(io.BytesIO(b'Hello'))
    >>> s.recv(3)
    'Hel'
    >>> s.recv(3)
    'lo'
    >>> s.recv(3)
    ''
    """

    def __init__(self, f):
        self.file = f

    def recv(self, bufsize, flags=0):  # pylint:disable=unused-argument
        return self.file.read(bufsize)
