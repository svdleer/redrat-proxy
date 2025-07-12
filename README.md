# RedRat Proxy

A modern web dashboar#### XML Format Support

The import system supports multiple XML formats for maximum compatibility:

1. **RedRat XML Format**:
```xml
<AVDeviceDB>
  <AVDevices>
    <AVDevice>
      <n>Remote Name</n>
      <Manufacturer>Manufacturer Name</Manufacturer>
      <DeviceModelNumber>Model Number</DeviceModelNumber>
```

2. **Standard Device Format**:
```xml
<Device>
  <Name>Remote Name</Name>
  <Manufacturer>Manufacturer Name</Manufacturer>
  <DeviceType>TV</DeviceType>
  <Signals>
    <Signal name="POWER">
      <Data>0000 006C 0022 0002 015B 00AD...</Data>
      <ModulationFreq>38000</ModulationFreq>
    </Signal>
  </Signals>
</Device>
```

3. **LIRC-Compatible Format**:
```xml
<remote>
  <name>Remote Name</name>
  <manufacturer>Manufacturer Name</manufacturer>
  <codes>
    <code name="POWER">0000 006C 0022 0002...</code>
    <code name="VOLUME_UP">0000 006C 0022 0002...</code>
  </codes>
</remote>
```

The system will automatically detect and parse various XML formats, extracting all available information, including:

- Remote name, manufacturer, and model information
- Device type and decoder class/protocol
- Signal/command names and codes
- Modulation frequencies
- Button layout information (if available)
- Signal metadata like toggle bits, repeat settings, etc.
- Remote control images (embedded or referenced)

The system uses a robust parsing approach with multiple fallbacks to handle variations in XML structure, element naming, and data formats.

### Enhanced XML Processing

The XML processing system has been enhanced to:

1. **Process Multiple XML Formats**: Support for RedRat, LIRC, Pronto, and other common IR remote XML formats
2. **Extract Complete Metadata**: Captures all available metadata for both remotes and signals
3. **Handle Button Layouts**: Extracts visual layout information when available
4. **Process Embedded Images**: Supports base64-encoded images within XML
5. **Perform Memory-Efficient Processing**: Files are processed in memory without requiring permanent storage
6. **Generate Proper XML Output**: Creates well-formed XML files for imported remotes

## Features

- 🔒 Secure login system
- 📱 Responsive UI built with Tailwind CSS
- 🎮 Manage remote controls
- 📊 Command history tracking
- 🔍 Remote XML file management
- 👥 User management with admin controls
- 📤 XML Import for remotes and signals

## Enhanced Features

- ⏱️ **Command Scheduler**: Schedule IR commands to run at specific times
- 🔄 **Command Sequences**: Queue multiple commands in a row and save as reusable macros
- 📊 **Visual Dashboard**: Monitoring interface for command execution status
- 📱 **Direct Control Interface**: Send immediate IR commands to devices
- 📋 **Command Templates**: Create templates from XML files for quick access
- 📊 **Signal Visualization**: View visual representations of IR signal patterns
- 📤 **XML Import**: Import remotes from RedRat XML files

## Dashboard

The RedRat Proxy features a modern dashboard built with Tailwind CSS that includes:

- 📊 **Stats Overview**: Real-time counts of remotes, commands, sequences, and schedules
- 🎮 **Quick Command**: Send IR commands directly from the dashboard
- 📜 **Recent Commands**: View recent command history with status
- 📱 **Activity Feed**: Real-time feed of command executions and user actions

## Remote Management

### XML Import for Remotes

The system supports importing remote controls and their signals from RedRat XML files. This is useful for migrating existing RedRat configurations or adding new remotes in bulk.

#### XML Format Structure

The import system supports the standard RedRat XML format:

```xml
<AVDeviceDB>
  <AVDevices>
    <AVDevice>
      <Name>Remote Name</Name>
      <Manufacturer>Manufacturer Name</Manufacturer>
      <DeviceModelNumber>Model Number</DeviceModelNumber>
      <RemoteModelNumber>Remote Model</RemoteModelNumber>
      <DeviceType>DEVICE_TYPE</DeviceType>
      <DecoderClass>Decoder Class Path</DecoderClass>
      <RCCorrection>
        <!-- Configuration settings -->
      </RCCorrection>
      <Signals>
        <IRPacket xsi:type="ModulatedSignal">
          <Name>Button Name</Name>
          <UID>Signal UID</UID>
          <ModulationFreq>36000</ModulationFreq>
          <SigData>Signal Data Here</SigData>
          <!-- Other signal properties -->
        </IRPacket>
        <!-- More signals -->
      </Signals>
    </AVDevice>
    <!-- More devices -->
  </AVDevices>
</AVDeviceDB>
```

#### Importing XML Files

1. Navigate to the Admin > Remotes page
2. Use the "Upload Remotes XML" panel to select and upload your XML file
3. The system will process the file and create or update remotes in the database
4. Signal data will be saved as command templates, making them available for use in commands and sequences

#### Database Schema for Remotes

The database is structured to store all relevant information from the XML file:

```sql
CREATE TABLE remotes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    manufacturer VARCHAR(255),
    device_model_number VARCHAR(255),
    remote_model_number VARCHAR(255),
    device_type VARCHAR(255),
    decoder_class VARCHAR(255),
    description TEXT,
    image_path VARCHAR(255),
    config_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The `config_data` field stores additional configuration parameters from the XML as a JSON object.

### Command Templates

When importing remotes from XML, the system automatically creates command templates for each signal. These templates are used to send commands to the RedRat IrNetBox.

Note: Support for .irdb files has been removed in favor of XML-only imports.

### Importing XML Files

XML files can be imported through:

1. **Web Interface**: Upload through the admin remotes section
2. **API Endpoint**: POST to `/api/remotes/import` with the XML file
3. **Command Line**: Use the import_remotes script
