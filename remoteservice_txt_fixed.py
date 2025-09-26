#!/usr/bin/env python3
"""
IRNetBox txt file parser for RedRat proxy.
This module parses IRNetBox format .txt files and extracts IR signal data.
"""

import binascii
import re

def parse_irnetbox_file(file_path):
    """
    Parse an IRNetBox format .txt file and return device name and signals.
    
    Returns:
        tuple: (device_name, signals_dict)
    """
    signals = {}
    device_name = "Unknown"
    
    # Read the file
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Parse device name from first line
        if line.startswith('Device '):
            device_name = line.replace('Device ', '').strip()
            i += 1
            continue
            
        # Skip description lines
        if 'Signal data as IRNetBox' in line or 'Note:' in line or 'Where signals' in line:
            i += 1
            continue
            
        # Parse signal lines (both MOD_SIG and DMOD_SIG)
        if 'MOD_SIG' in line or 'DMOD_SIG' in line:
            # Skip documentation lines containing angle brackets
            if '<' in line and '>' in line:
                i += 1
                continue
                
            # Split by tabs for the IRNetBox format
            parts = line.strip().split('\t')
            
            if 'DMOD_SIG' in line and len(parts) >= 4:
                signal_name = parts[0]
                # DMOD_SIG format: signal_name \t DMOD_SIG \t signal1/signal2 \t max_lengths hex_data
                signal_type = parts[2]  # 'signal1' or 'signal2'
                # Parts[3] contains "max_lengths hex_data" combined, need to split
                lengths_and_data = parts[3].strip().split(' ', 1)
                if len(lengths_and_data) >= 2:
                    max_lengths = int(lengths_and_data[0])
                    hex_data = lengths_and_data[1].strip()
                else:
                    i += 1
                    continue
                # Only process signal1 for simplicity
                if signal_type != 'signal1':
                    i += 1
                    continue
                key = signal_name  # Use just the signal name, not the combined key
            elif 'MOD_SIG' in line and 'DMOD_SIG' not in line and len(parts) >= 4:
                signal_name = parts[0]
                # MOD_SIG format: signal_name \t MOD_SIG \t max_lengths \t hex_data
                max_lengths = int(parts[2])
                hex_data = parts[3].strip()
                key = signal_name
            else:
                i += 1
                continue
                
            # Convert hex string to bytes and analyze
            frequency = 38000  # Default for consumer IR
            num_repeats = 1    # Default
            
            try:
                if hex_data:
                    # Clean hex data - remove all non-hex characters
                    clean_hex = re.sub(r'[^0-9A-Fa-f]', '', hex_data)
                    
                    # Handle odd-length hex strings (IRNetBox format may have nibble alignment)
                    if len(clean_hex) % 2 == 1:
                        clean_hex = '0' + clean_hex  # Pad with leading zero
                        
                    signal_bytes = binascii.unhexlify(clean_hex)
                    
                    if len(signal_bytes) >= 12:
                        # RedRat MK4 structure: intra_pause(4) + timer(2) + periods(2) + lengths_info(2) + ...
                        # Extract timer value (bytes 4-5, big-endian) and convert to frequency
                        timer_value = int.from_bytes(signal_bytes[4:6], byteorder='big')
                        if timer_value > 0:
                            frequency = int(1000000 / timer_value)  # Convert to Hz
                        
                        # Extract number of periods (bytes 6-7, big-endian)
                        num_periods = int.from_bytes(signal_bytes[6:8], byteorder='big')
                        if num_periods > 1:
                            num_repeats = num_periods
                    
                    # Debug output
                    print(f"Parsed signal {key}: freq={frequency}Hz, repeats={num_repeats}, data_len={len(signal_bytes)}")
                    
                    # Store in signals dictionary
                    signals[key] = {
                        'name': key,
                        'frequency': frequency,
                        'data': binascii.hexlify(signal_bytes).decode('ascii').upper(),
                        'repeats': num_repeats,
                        'max_lengths': max_lengths
                    }
                    
            except Exception as e:
                print(f"Error processing signal {key}: {e}")
            
        # Move to next line
        i += 1
    
    return device_name, signals