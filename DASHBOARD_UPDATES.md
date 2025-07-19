# Dashboard Command Form Updates

## Changes Made

### 1. Template Updates (`app/templates/dashboard.html`)
- **Removed:** Device input field with datalist suggestions
- **Added:** RedRat Device selection dropdown as first field
- **Maintained:** Remote selection, Command selection, IR Port, and Power controls
- **New structure:** RedRat Device → Remote → Command → IR Port + Power

### 2. JavaScript Updates (`app/static/js/dashboard.js`)
- **Added:** `loadRedRatDevices()` function to populate RedRat device dropdown
- **Updated:** Form validation to require RedRat device, remote, and command
- **Updated:** API call to send `redrat_device_id` instead of `device`
- **Removed:** `loadDeviceInfo()` function (no longer needed)
- **Updated:** Remote change event handler (removed device loading)

### 3. API Updates (`app/app.py`)
- **Updated:** `/api/commands` POST endpoint Swagger documentation
- **Changed:** Required field from `device` to `redrat_device_id`
- **Updated:** Command insertion to use RedRat device ID
- **Updated:** Command queue data to include `redrat_device_id`

## New Form Flow

1. **User selects RedRat Device** - Populates from `/api/redrat/devices`
2. **User selects Remote** - Triggers loading of commands via `/api/remotes/{id}/commands`
3. **User selects Command** - Available commands for the selected remote
4. **User configures IR Port** - Dropdown with ports 1-16 (dynamic based on device capabilities)
5. **User sets Power Level** - Slider with real-time percentage display
6. **User submits** - Sends command with all parameters to `/api/commands`

## API Request Format
```json
{
  "redrat_device_id": 1,
  "remote_id": 2,
  "command": "power_on",
  "ir_port": 1,
  "power": 100
}
```

## Benefits
- ✅ Proper RedRat device selection for command execution
- ✅ Commands populate correctly when remote is selected
- ✅ Full port and power control per command
- ✅ Cleaner, more logical form flow
- ✅ Eliminates manual device type entry
- ✅ Device status indication (🟢/🔴) in dropdown

## Testing Required
1. Verify RedRat devices load in dropdown with status indicators
2. Test remote selection triggers command loading
3. Confirm command execution uses specified RedRat device, port, and power
4. Validate form validation works for all required fields
