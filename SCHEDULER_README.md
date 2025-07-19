# RedRat Device Status Monitor and Scheduler

This script monitors RedRat device status and can execute scheduled commands. It provides comprehensive monitoring and maintenance capabilities for your RedRat infrastructure.

## Features

- **Device Status Monitoring**: Automatically checks all active RedRat devices
- **Database Integration**: Updates device status in real-time
- **Flexible Execution**: Run once or as a continuous daemon
- **Comprehensive Logging**: Detailed logs for troubleshooting
- **Graceful Shutdown**: Handles signals properly for clean shutdowns
- **Error Handling**: Robust error handling and recovery

## Usage

### Run Once (for cron jobs)
```bash
python redrat_scheduler.py
```

### Run as Daemon
```bash
python redrat_scheduler.py --daemon --interval=60
```

### Command Line Options
- `--daemon`: Run as daemon (continuous monitoring)
- `--interval=N`: Check interval in seconds (default: 60)
- `--log-level=L`: Log level (DEBUG, INFO, WARNING, ERROR)

## Installation

### 1. Cron Job (Recommended for periodic checks)
Add to your crontab:
```bash
# Check every 5 minutes
*/5 * * * * /path/to/redrat-proxy/redrat_status_check.sh

# Check every hour
0 * * * * /path/to/redrat-proxy/redrat_status_check.sh
```

### 2. Systemd Service (For continuous monitoring)
1. Copy the service file:
   ```bash
   sudo cp redrat-scheduler.service /etc/systemd/system/
   ```

2. Edit the service file with correct paths:
   ```bash
   sudo nano /etc/systemd/system/redrat-scheduler.service
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable redrat-scheduler
   sudo systemctl start redrat-scheduler
   ```

4. Check service status:
   ```bash
   sudo systemctl status redrat-scheduler
   ```

## Monitoring and Logs

### Log Files
- `redrat_scheduler.log`: Main application log
- `redrat_cron.log`: Cron execution log

### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General operational information
- **WARNING**: Warning messages (devices offline)
- **ERROR**: Error messages (connection failures)

### Example Log Output
```
2025-07-14 21:56:41,290 - __main__ - INFO - Starting device status check...
2025-07-14 21:56:41,481 - __main__ - INFO - Checking 3 devices...
2025-07-14 21:56:41,620 - __main__ - INFO - Device Office RedRat is online (response: 0.14s)
2025-07-14 21:56:41,755 - __main__ - WARNING - Device Lab RedRat is offline
2025-07-14 21:56:41,890 - __main__ - ERROR - Device Conference RedRat error: Connection timeout
2025-07-14 21:56:41,891 - __main__ - INFO - Status check complete: 1 online, 1 offline, 1 error
```

## Database Schema

The scheduler updates the following fields in the `redrat_devices` table:
- `last_status`: Current device status (online/offline/error)
- `last_status_check`: Timestamp of last status check
- `device_model`: Device model information (if available)
- `device_ports`: Number of device ports (if available)

## Configuration

The scheduler uses the same environment variables as the main application:
- `MYSQL_HOST`: Database host
- `MYSQL_PORT`: Database port
- `MYSQL_USER`: Database username
- `MYSQL_PASSWORD`: Database password
- `MYSQL_DB`: Database name

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check database credentials in `.env` file
   - Ensure MySQL server is running
   - Verify network connectivity

2. **Device Connection Timeouts**
   - Check RedRat device IP addresses
   - Verify network connectivity to devices
   - Confirm devices are powered on

3. **Permission Errors**
   - Ensure script has execute permissions
   - Check file ownership and permissions
   - Verify systemd service user permissions

### Debug Mode
Run with debug logging to see detailed information:
```bash
python redrat_scheduler.py --log-level=DEBUG
```

## Future Enhancements

The scheduler is designed to be extensible. Future features could include:
- Scheduled IR command execution
- Device health notifications
- Performance metrics collection
- Integration with monitoring systems
- Automated device recovery

## Examples

### Basic Status Check
```bash
# Run once and exit
python redrat_scheduler.py

# Run with info logging
python redrat_scheduler.py --log-level=INFO
```

### Daemon Mode
```bash
# Run continuously, check every 30 seconds
python redrat_scheduler.py --daemon --interval=30

# Run with debug logging
python redrat_scheduler.py --daemon --interval=60 --log-level=DEBUG
```

### Cron Integration
```bash
# Add to crontab for automatic execution
crontab -e

# Add line for every 5 minutes:
*/5 * * * * /path/to/redrat-proxy/redrat_status_check.sh
```
