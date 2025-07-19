# MK3 Protocol Fix - Apply this to a clean redratlib.py

# 1. In the MessageTypes class, add this line after CPLD_INSTRUCTION:
OUTPUT_IR_SYNC = 0x08  # Added missing sync IR output message type

# 2. In the irsend_raw method, replace the "else:" block (for MK3/MK4/RRX) with:

else:
    # MK3, MK4, RRX protocol - Use SYNC mode like the working signal database
    logger.debug(f"Using MK3/MK4/RRX protocol for device model: {self.irnetbox_model}")
    
    # For MK3+ devices, use SYNC mode with proper data format
    # Based on working packet analysis: use message type 0x08 (OUTPUT_IR_SYNC)
    ports = [0] * self.ports
    ports[port - 1] = power
    
    logger.debug(f"Port configuration: {ports}")
    
    # Format the data payload for SYNC mode (matching working packets)
    packet_format = "{0}s{1}s".format(self.ports, len(data))
    logger.debug(f"Packet format: {packet_format}")
    
    payload = struct.pack(
        packet_format,
        struct.pack("{}B".format(self.ports), *ports),
        data)
    
    self._send(MessageTypes.OUTPUT_IR_SYNC, payload)
    logger.info("SYNC IR signal sent successfully")

# 3. In the _send method response handling, add this before the OUTPUT_IR_ASYNC check:

if response_type == MessageTypes.OUTPUT_IR_SYNC:
    logger.debug("Processing sync IR response")
    # For SYNC mode, the response should be immediate and simple
    if len(response_data) > 0:
        logger.debug(f"SYNC response data: {binascii.hexlify(response_data).decode()}")
    logger.debug("SYNC IR command completed successfully")
    
elif response_type == MessageTypes.OUTPUT_IR_ASYNC:
    # ... existing ASYNC handling code ...
