# RedRat Proxy

A modern web dashboard for the RedRat IrNetBox - infrared remote control system.

## Features

- 🔒 Secure login system
- 📱 Responsive UI built with Tailwind CSS
- 🎮 Manage remote controls
- 📊 Command history tracking
- 🔍 IRDB file management
- 👥 User management with admin controls

## Enhanced Features

- ⏱️ **Command Scheduler**: Schedule IR commands to run at specific times
- 🔄 **Command Sequences**: Queue multiple commands in a row and save as reusable macros
- 📊 **Visual Dashboard**: Monitoring interface for command execution status
- 📱 **Direct Control Interface**: Send immediate IR commands to devices
- 📋 **Command Templates**: Create templates from IRDB files for quick access
- 📊 **Signal Visualization**: View visual representations of IR signal patterns

## Setup

### Prerequisites

- Python 3.7+
- MySQL/MariaDB
- No Node.js needed (Tailwind CSS via CDN)

### Installation

1. Clone the repository
   ```
   git clone https://github.com/yourusername/redrat-proxy.git
   cd redrat-proxy
   ```

2. Install Python dependencies
   ```
   pip install -r requirements.txt
   ```

3. Configure environment variables
   ```
   # Copy the example environment file
   cp .env.example .env
   
   # Edit the .env file with your settings
   # Especially the MYSQL_USER, MYSQL_PASSWORD, and SECRET_KEY
   ```

4. Initialize the database
   ```
   # On Windows
   mysql -u username -p < mysql_schema.sql
   
   # On Linux/Mac
   chmod +x init_db.sh
   ./init_db.sh
   ./init_db.sh
   ```

4. Start the application
   ```
   # On Windows
   run_dev.bat
   
   # On Linux/Mac
   chmod +x run_dev.sh
   ./run_dev.sh
   ```

5. Visit `http://localhost:5000/login` in your browser

## Development

### Docker Virtual Environment

When running in Docker, the project uses a virtual environment to isolate dependencies. This happens automatically inside the container and requires no action from you.

The local development setup does not require a virtual environment, although you can certainly use one if you prefer.

### Docker Deployment

1. Ensure Host MySQL is Running
   Make sure your MySQL server is running on the host machine and is accessible.
   ```
   # On Windows
   net start mysql
   
   # On Linux
   sudo systemctl status mysql
   ```

2. Configure environment variables
   Copy the example env file and modify it:
   ```
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

3. Initialize the Database
   ```
   # On Windows
   mysql -u username -p < mysql_schema.sql
   
   # On Linux/Mac
   chmod +x init_db.sh
   ./init_db.sh
   ```

4. Start the web application container
   ```
   # Start the web application
   docker-compose up -d
   
   # If you want to see the logs
   docker-compose logs -f
   ```

5. Database Connection Verification
   The container will verify database connectivity on startup and attempt to:
   
   - Connect to the host's MySQL service
   - Create the database if it doesn't exist
   - Create all required tables from the mysql_schema.sql file if they don't exist
   - Check for the default admin user
   
6. Troubleshooting database issues
   If the database connection fails:
   
   ```
   # Check container logs
   docker-compose logs web
   
   # Make sure your host MySQL is running and accessible
   mysql -u username -p -e "SHOW DATABASES;"
   
   # Check that the host.docker.internal DNS resolution works from the container
   docker-compose exec web ping -c 4 host.docker.internal
   
   # Restart the web service
   docker-compose restart web
   ```

This will start the Flask application in a container. The application will:
- Connect to MySQL running on your host machine
- Expose port 5000 on localhost, which your host's reverse proxy can forward to

## Command Management

### Command Queue

The RedRat Proxy allows you to queue multiple IR commands for sequential execution:

- Add commands to the queue from different remotes
- Set delay intervals between commands
- Monitor queue status in real-time
- Clear or modify the queue before execution

### Command Sequences

You can create and save sequences of frequently used commands:

1. Build a sequence by adding multiple commands in order
2. Save the sequence with a descriptive name
3. Execute saved sequences with a single click
4. Edit existing sequences to add/remove commands or adjust timing

### Command Templates

Create reusable command templates from your IRDB files:

1. Import IRDB files containing IR signal patterns
2. Generate command templates for specific devices
3. Use templates to quickly add common commands to sequences

### Command Scheduling

Schedule commands or sequences to run at specific times:

- Set one-time execution at a specific date and time
- Create recurring schedules (daily, weekly, etc.)
- View and manage all scheduled tasks from the dashboard

## Monitoring

The dashboard provides real-time monitoring of:

- Currently executing commands
- Command history with status indicators
- Signal visualization for debugging
- System health metrics

## Maintenance Tools

Several maintenance tools are included to help manage the RedRat Proxy system:

### Quick Start - Using maintenance.bat

A maintenance script is provided for common tasks:

1. Run `maintenance.bat` from the project root
2. Select the operation you want to perform:
   - Reset Admin Password - Creates or updates the admin user with password 'admin123'
   - Run Housekeeping - Cleans up unused files and sessions
   - Run Login Diagnostic - Checks database connection and login issues
   - Update Logo to PNG - Converts SVG logo to PNG format

### Manual Maintenance

You can also run these scripts individually:

```bash
# Reset admin password
python reset_admin_password.py

# Clean up unused files and expired sessions
python housekeeping.py

# Diagnose login issues
python login_diagnostic.py
```

### Fixing Login Issues

If you can't login, try these steps:

1. Run the login diagnostic: `python login_diagnostic.py`
2. Reset the admin password: `python reset_admin_password.py`
3. Check that your MySQL connection details are correct
4. Clear your browser cookies and cache

### Housekeeping Options

The housekeeping script accepts several parameters:

```bash
# Run with default settings (7-day threshold)
python housekeeping.py

# Only preview what would be removed (dry run)
python housekeeping.py --dry-run

# Set custom age threshold (in days)
python housekeeping.py --days 30

# Specify custom base directory
python housekeeping.py --base-dir /path/to/installation
```

### Reverse Proxy Configuration

The application is designed to work behind a reverse proxy. An example Apache configuration is provided in the `apache/redrat.conf` file, which you can use as a reference for setting up your reverse proxy on the Docker host.

## IRDB File Management

The RedRat Proxy includes comprehensive support for IRDB (Infrared Database) files:

### Importing IRDB Files

1. Navigate to the IRDB Management section
2. Upload IRDB files (`.irdb` extension)
3. The system will process and store the IR signal patterns

### Using IRDB Files

Once imported, IRDB files can be used to:

- Generate command templates for devices
- Create custom IR commands
- Map buttons to specific signals
- Build command sequences using predefined signals

### Managing IRDB Library

- View all imported IRDB files
- Search for specific signals
- Download or delete IRDB files as needed
- See which remotes are using specific IRDB files

## License

[MIT](LICENSE)
