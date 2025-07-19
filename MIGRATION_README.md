# Node-RED Migration Script

This script helps migrate Node-RED flows to use new API endpoints and patterns. It's particularly useful when you need to update function nodes to work with a new version of your API.

## Features

- ✅ Search and replace patterns in Node-RED function nodes
- ✅ Regex support for complex pattern matching
- ✅ Automatic backup creation
- ✅ YAML configuration support
- ✅ Batch processing of multiple files
- ✅ Detailed migration statistics
- ✅ Logging and error handling

## Installation

1. **Basic version** (uses only Python standard library):
   ```bash
   python nodered_migration.py
   ```

2. **Enhanced version with YAML support**:
   ```bash
   pip install PyYAML
   python nodered_migration_yaml.py
   ```

## Usage

### Basic Usage

Migrate a single flow file:
```bash
python nodered_migration.py flows.json
```

Migrate all JSON files in a directory:
```bash
python nodered_migration.py ./flows/
```

### Advanced Usage

Use custom migration rules from YAML:
```bash
python nodered_migration_yaml.py flows.json --rules migration_rules.yaml
```

Skip creating backups:
```bash
python nodered_migration_yaml.py flows.json --no-backup
```

Verbose logging:
```bash
python nodered_migration_yaml.py flows.json --verbose
```

### Options

- `--rules FILE`: Load migration rules from YAML file
- `--no-backup`: Skip creating backup files
- `--pattern PATTERN`: File pattern for directory migration (default: `*.json`)
- `--custom-rules-only`: Only apply rules from YAML file
- `--verbose, -v`: Verbose logging
- `--dry-run`: Show what would be changed without making changes

## Configuration

### YAML Configuration File

Create a `migration_rules.yaml` file to define your migration patterns:

```yaml
migration_rules:
  - old_pattern: 'http://localhost:5000/api/v1/'
    new_pattern: 'http://localhost:5000/api/'
    description: 'Update API base URL'
    
  - old_pattern: 'msg\.payload = \{\s*"command":\s*"([^"]+)",\s*"remote":\s*"([^"]+)"\s*\}'
    new_pattern: |
      msg.payload = {
          "remote_id": "\2",
          "command": "\1",
          "redrat_device_id": 1,
          "ir_port": 1,
          "power": 100
      }
    description: 'Update command payload structure'
```

### Default Rules

The script includes default rules for common RedRat API migrations:

1. **API URL updates**: `v1` → current API
2. **Command structure**: Old payload format → New RedRat API format
3. **Endpoint paths**: `/send_command` → `/api/commands`
4. **Authentication**: Bearer tokens → Session cookies
5. **Status endpoints**: `/get_status` → `/api/redrat/devices`

## Examples

### Example 1: Simple Text Replace

Replace old API URLs:
```yaml
- old_pattern: 'http://old-server.com/api/'
  new_pattern: 'http://new-server.com/api/'
  description: 'Update server URL'
```

### Example 2: Complex Payload Transformation

Transform command structure using regex groups:
```yaml
- old_pattern: 'sendCommand\("([^"]+)",\s*"([^"]+)"\)'
  new_pattern: |
    msg.payload = {
        "command": "\1",
        "remote_id": "\2",
        "power": 100
    };
    node.send(msg)
  description: 'Convert function calls to HTTP requests'
```

### Example 3: Add New Required Fields

Add missing fields to existing payloads:
```yaml
- old_pattern: '(\{\s*"command":\s*"[^"]+"\s*\})'
  new_pattern: |
    {
        "command": msg.payload.command,
        "redrat_device_id": 1,
        "ir_port": 1,
        "power": 100
    }
  description: 'Add required fields to command payload'
```

## File Structure

After running the migration, you'll see:

```
flows/
├── flow1.json                    # Migrated file
├── flow1.json.backup_20250119_143022  # Backup file
├── flow2.json                    # Migrated file  
└── flow2.json.backup_20250119_143022  # Backup file
```

## Migration Statistics

The script provides detailed statistics:

```
============================================================
MIGRATION STATISTICS
============================================================
Flows processed: 5
Function nodes found: 12
Nodes updated: 8
Total replacements made: 15

Rules Applied:
----------------------------------------
✓ Rule 0: Update API base URL (3 times)
✓ Rule 1: Update command payload structure (5 times)
○ Rule 2: Update authentication method (0 times)
✓ Rule 3: Update command endpoint path (7 times)
============================================================
```

## Safety Features

1. **Automatic Backups**: Original files are backed up with timestamps
2. **Error Handling**: Failed migrations don't stop the batch process
3. **Validation**: JSON validation ensures files remain valid
4. **Logging**: Detailed logs show exactly what was changed

## Troubleshooting

### Common Issues

1. **"No migration rules defined"**
   - Make sure you have rules in your YAML file or remove `--custom-rules-only`

2. **"Failed to load YAML rules"**
   - Install PyYAML: `pip install PyYAML`
   - Check YAML syntax

3. **"No flow files found"**
   - Check the file pattern with `--pattern "*.json"`
   - Ensure files exist in the specified directory

### Testing Your Rules

1. Test on a single file first
2. Use `--verbose` to see detailed logs
3. Check backup files to compare changes
4. Validate flows in Node-RED after migration

## Extending the Script

### Add Custom Rules Programmatically

Edit the `setup_custom_migration_rules()` function:

```python
def setup_custom_migration_rules(migrator: NodeRedMigrator):
    migrator.add_migration_rule(
        r'old_pattern',
        'new_replacement',
        'Description of what this does'
    )
```

### Add New Node Types

Currently supports `function` nodes. To support other types, modify the `migrate_function_node()` method.

## License

This script is part of the RedRat Proxy project. Modify as needed for your use case.
