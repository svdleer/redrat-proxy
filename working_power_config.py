# WORKING POWER COMMAND CONFIGURATION
# Generated from successful test on 2025-09-28 23:02:53

WORKING_POWER_COMMAND = {
    "name": "POWER",
    "uid": "RgTVkXKDn0C7hK9giKnH9Q==",
    "modulation_freq": 38350,
    "lengths": [8.878, 4.535, 0.544, 1.7145, 0.6315, 1.418, 0.118, 0.1115, 0.1155, 0.0745, 0.326, 0.003, 0.134, 0.0825, 0.0165, 0.009, 0.005, 0.1155, 0.048, 0.0565, 0.0745, 0.0755, 0.1095, 2.3035],
    "signal_data_base64": "AAECAgICAgICAgICAgICAgICAgICAgICAgICAwICAgICAgICAgICAgICAgICAgIEAgICAwIDAgMCAwIDAgMCAwIDAn8FBgcIAgkKCwwNBA4CDwIQERITFAoVFhYWFgoWFhYWFgoWFhYWFhYWDBYWFgoWDBYWFhYWFhYMFhYWFhcCfw==",
    "no_repeats": 2,
    "intra_sig_pause": 47.5215,
    "device_type": "PVR",
    "remote_id": 16,
    "tested_port": 9,
    "tested_power_level": "HIGH",
    "protocol": "ASYNC_0x30"
}

# Usage example:
# power_signal = IRSignal(**WORKING_POWER_COMMAND)
# redrat.send_signal_async(power_signal, [OutputConfig(port=9, power_level=PowerLevel.HIGH)])
