# RedR### Core Functionality
- 🎮 **IR Remote Control Management** - Complete CRUD operations for remote controls and commands
- 📤 **XML Import/Export** - Import and export XML files in RedRat/IRNetBox format
- 🔌 **RedRat Device Integration** - Direct communication with RedRat hardware via XML-RPC
- 📊 **Real-time Dashboard** - Live statistics, command history, and system monitoring
- ⏱️ **Command Scheduling** - Schedule IR commands to run at specific times
- 🔄 **Command Sequences** - Create and execute multi-command macrosy - Complete IR Remote Control Management System

A modern, production-ready web application for managing IR remote controls through RedRat hardware devices. Features a comprehensive Flask-based backend with MySQL database, Docker containerization, and a responsive web interface.

## 🚀 Key Features

### Core Functionality
- 🎮 **IR Remote Control Management** - Complete CRUD operations for remote controls and commands
- 📤 **XML Import/Export** - Import IRNetBox format files and export to XML
- � **RedRat Device Integration** - Direct communication with RedRat hardware via XML-RPC
- 📊 **Real-time Dashboard** - Live statistics, command history, and system monitoring
- ⏱️ **Command Scheduling** - Schedule IR commands to run at specific times
- 🔄 **Command Sequences** - Create and execute multi-command macros

### Security & Authentication
- � **Dual Authentication** - Session-based login + API key authentication
- 👑 **Admin Controls** - Role-based access with admin-only features
- � **API Key Management** - Complete API key lifecycle with usage tracking
- 🛡️ **Secure Sessions** - Encrypted session management with expiration

### API & Integration
- 📡 **RESTful API** - Comprehensive REST API for all operations
- � **Swagger Documentation** - Interactive API documentation
- 🔑 **API Authentication** - Support for Bearer tokens and API keys
- 📊 **Activity Logging** - Complete audit trail of all operations

### Technical Excellence
- 🐳 **Docker Ready** - Complete containerization with Docker Compose
- 💾 **MySQL Database** - Robust relational database with proper constraints
- � **Health Monitoring** - Built-in health checks and logging
- 🔧 **Production Ready** - Gunicorn WSGI server with resource limits

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │────│   Flask API     │────│   MySQL DB      │
│  (HTML/JS/CSS)  │    │   (Python)      │    │  (Data Layer)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   RedRat Device │
                       │   (XML-RPC)     │
                       └─────────────────┘
```

### Database Schema
- **Users** - Authentication and authorization
- **API Keys** - API authentication with usage tracking
- **Remotes** - IR remote control definitions
- **Commands** - Individual IR commands with signal data
- **Sequences** - Multi-command macros
- **Schedules** - Timed command execution
- **Templates** - Reusable command templates
- **Activity Logs** - Complete audit trail

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- MySQL server (local or containerized)
- RedRat IR hardware device (optional for development)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/svdleer/redrat-proxy.git
   cd redrat-proxy
   ```

2. **Setup environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Initialize database**
   ```bash
   mysql -h localhost -u root -p < mysql_schema.sql
   ```

4. **Start the application**
   ```bash
   docker-compose up -d
   ```

5. **Access the application**
   - Web Interface: http://localhost:5000
   - API Documentation: http://localhost:5000/swagger
   - Default Login: admin/admin

## 🔧 Configuration

### Environment Variables (.env)
```bash
# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=redrat_proxy
MYSQL_USER=redrat
MYSQL_PASSWORD=your_password

# Application Settings
SECRET_KEY=your_secret_key
UPLOAD_FOLDER=app/static/uploads
LOG_LEVEL=INFO

# RedRat Device
REDRAT_XMLRPC_URL=http://your-redrat-ip:40000/RPC2

# Web Server
SERVER_NAME=localhost:5000
APPLICATION_ROOT=/
PREFERRED_URL_SCHEME=http
```

### Docker Compose Features
- **Host networking** for optimal RedRat device communication
- **Health checks** with automatic restart policies
- **Volume mounts** for persistent data and logs
- **Resource limits** for production stability

## 📡 API Usage

### Authentication
The API supports two authentication methods:

**1. API Key Authentication**
```bash
# Using Authorization header
curl -H "Authorization: Bearer rr_your_api_key_here" \
     http://localhost:5000/api/remotes

# Using X-API-Key header
curl -H "X-API-Key: rr_your_api_key_here" \
     http://localhost:5000/api/remotes
```

**2. Session Authentication**
```bash
# Login to get session cookie
curl -c cookies.txt -X POST \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin"}' \
     http://localhost:5000/api/login

# Use session cookie for subsequent requests
curl -b cookies.txt http://localhost:5000/api/remotes
```

### Key Endpoints
- `GET /api/remotes` - List all remotes
- `POST /api/remotes` - Create new remote
- `GET /api/commands` - List commands
- `POST /api/commands` - Execute IR command
- `GET /api/sequences` - List sequences
- `POST /api/sequences` - Create/execute sequence
- `GET /api/keys` - Manage API keys (admin only)

## 📤 XML Import/Export

### Importing XML Files
1. Navigate to Admin → Remotes
2. Use "Upload IRNetBox file" section
3. Select your XML file with RedRat/IRNetBox format
4. System automatically processes and creates remotes and commands

### XML Format Example
```xml
<?xml version="1.0" encoding="UTF-8"?>
<IRNetBox xmlns="http://www.redrat.co.uk/irnetbox">
  <DeviceInfo>
    <DeviceName>Humax HDR-FOX T2</DeviceName>
    <Manufacturer>Humax</Manufacturer>
    <DeviceType>SET_TOP_BOX</DeviceType>
  </DeviceInfo>
  <Commands>
    <Command name="POWER">
      <SignalData>...</SignalData>
    </Command>
    <Command name="GUIDE">
      <SignalData>...</SignalData>
    </Command>
  </Commands>
</IRNetBox>
```

### Export to XML
- Use the web interface to export remotes to XML format
- Compatible with RedRat tools and IRNetBox systems
- Maintains signal integrity and device information

## 🔑 API Key Management

### Features
- **Last Used Tracking** - See when each API key was last used
- **Expiration Management** - Set custom expiration dates
- **Admin Only Access** - Only administrators can manage API keys
- **Usage Monitoring** - Track API key usage patterns

### Creating API Keys
1. Login as admin
2. Navigate to API Keys page
3. Click "Create New API Key"
4. Set name and expiration
5. Copy the generated key (shown only once!)

## 📊 Monitoring & Logging

### Dashboard Metrics
- Total remotes, commands, sequences
- Recent command history
- System activity feed
- Real-time execution status

### Logging
- **Application logs** - All system events and errors
- **Command execution** - IR command success/failure
- **API usage** - Request logging with authentication
- **Database operations** - Query and transaction logs

## 🔧 Development

### Local Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
```

### Database Migrations
```bash
# Reset database (WARNING: destroys data)
mysql -h localhost -u redrat -p'password' redrat_proxy < mysql_schema.sql

# Backup before changes
mysqldump -h localhost -u redrat -p'password' redrat_proxy > backup.sql
```

## 🐳 Production Deployment

### Docker Production Features
- **Gunicorn WSGI server** for high performance
- **Health checks** with automatic recovery
- **Resource limits** (1 CPU, 512MB RAM)
- **Log rotation** with size limits
- **Non-root execution** for security

### Scaling Considerations
- Database connection pooling included
- Stateless design allows horizontal scaling
- Redis can be added for session storage
- Load balancer compatible

## 🛠️ Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs web

# Rebuild without cache
docker-compose build --no-cache
```

**Database connection errors:**
```bash
# Test database connectivity
mysql -h localhost -u redrat -p'password' redrat_proxy

# Check database schema
SHOW TABLES;
```

**RedRat device not responding:**
```bash
# Test XML-RPC connection
curl http://your-redrat-ip:40000/RPC2

# Check device configuration in .env
```

### Support Files
- `docker-reset-admin.sh` - Reset admin password
- `generate_admin_password.py` - Generate password hashes
- Log files in `./logs/` directory

## 📝 License

This project is proprietary software. All rights reserved.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For technical support or questions:
- Check the logs in `./logs/`
- Review the API documentation at `/swagger`
- Ensure all environment variables are properly set
- Verify RedRat device connectivity

---

**RedRat Proxy** - Professional IR Remote Control Management System
