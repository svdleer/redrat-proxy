# RedRat Proxy - Complete Installation Guide

This comprehensive guide walks you through installing and configuring the RedRat Proxy application using Docker. Whether you're setting up for development or production, this guide has you covered.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start (Recommended)](#quick-start-recommended)
4. [Manual Installation](#manual-installation)
5. [Configuration](#configuration)
6. [Database Setup](#database-setup)
7. [SSL/TLS Setup](#ssltls-setup)
8. [Production Deployment](#production-deployment)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

## Overview

RedRat Proxy is a Flask-based web application that provides:
- Web-based remote control management
- Device scheduling and automation
- RedRat hardware integration
- Admin dashboard with device management
- RESTful API for programmatic access

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 1 vCPU
- RAM: 512 MB
- Storage: 2 GB
- Network: 1 Mbps

**Recommended:**
- CPU: 2 vCPU
- RAM: 1 GB
- Storage: 10 GB
- Network: 10 Mbps

### Required Software

1. **Docker** (version 20.10 or higher)
2. **Docker Compose** (version 2.0 or higher)
3. **MySQL Server** (8.0 or higher)
4. **Git** (for cloning the repository)

### Install Docker

**Ubuntu/Debian:**
```bash
# Update package index
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again, then verify
docker --version
docker-compose --version
```

**CentOS/RHEL:**
```bash
# Install Docker
sudo yum install -y docker docker-compose

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

**macOS:**
```bash
# Install Docker Desktop
brew install --cask docker
# Or download from https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker-compose --version
```

**Windows:**
1. Download Docker Desktop from https://www.docker.com/products/docker-desktop
2. Install and restart your computer
3. Open PowerShell/Command Prompt and verify:
   ```
   docker --version
   docker-compose --version
   ```

## Quick Start (Recommended)

The fastest way to get RedRat Proxy running is using our automated setup script:

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd redrat-proxy
```

### 2. Run Quick Setup

```bash
# Make setup script executable
chmod +x docker-setup.sh

# Run automated setup
./docker-setup.sh
```

The setup script will:
- Check system requirements
- Create necessary directories
- Configure environment variables
- Set up database connection
- Build and start the application

### 3. Access the Application

Once setup is complete:
- **URL:** http://localhost:5000
- **Default Login:** admin / admin
- **Admin Panel:** http://localhost:5000/admin

**⚠️ Change the default password immediately after first login!**

### 4. Using Makefile Commands

After initial setup, use these convenient commands:

```bash
# View all available commands
make help

# Common operations
make up        # Start application
make down      # Stop application
make restart   # Restart application
make logs      # View logs
make shell     # Access container shell
make backup    # Backup database
```

## Manual Installation

If you prefer manual setup or the quick setup doesn't work for your environment:

### 1. Clone and Prepare

```bash
git clone <your-repository-url>
cd redrat-proxy

# Create data directories
mkdir -p data/uploads data/remote_images
chmod 755 data/
chmod 777 data/uploads data/remote_images
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required .env configuration:**
```env
# MySQL Configuration
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3306
MYSQL_DB=redrat_proxy
MYSQL_USER=redrat
MYSQL_PASSWORD=your_secure_password

# App Configuration
SECRET_KEY=your_super_secret_key_change_this_in_production
UPLOAD_FOLDER=app/static/uploads
LOG_LEVEL=INFO

# RedRat Configuration
REDRAT_XMLRPC_URL=http://your-redrat-ip:40000/RPC2

# Web Configuration
SERVER_NAME=localhost:5000
APPLICATION_ROOT=/
PREFERRED_URL_SCHEME=http
```

### 3. Build and Start

```bash
# Build Docker image
docker-compose build

# Start application
docker-compose up -d

# Verify it's running
docker-compose ps
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MYSQL_HOST` | MySQL server hostname | `host.docker.internal` | Yes |
| `MYSQL_PORT` | MySQL server port | `3306` | Yes |
| `MYSQL_DB` | Database name | `redrat_proxy` | Yes |
| `MYSQL_USER` | Database username | `redrat` | Yes |
| `MYSQL_PASSWORD` | Database password | - | Yes |
| `SECRET_KEY` | Flask secret key | - | Yes |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `REDRAT_XMLRPC_URL` | RedRat device URL | - | Yes |
| `SERVER_NAME` | Server hostname | `localhost:5000` | No |

### Generate Secure Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate MySQL password
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### Directory Structure

```
redrat-proxy/
├── app/                    # Application code
├── data/                   # Persistent data
│   ├── uploads/           # File uploads
│   └── remote_images/     # Remote control images
├── docker-compose.yml     # Docker configuration
├── Dockerfile            # Docker image definition
├── .env                  # Environment variables
├── mysql_schema.sql      # Database schema
└── requirements.txt      # Python dependencies
```

## Database Setup

### Option 1: Host MySQL (Recommended)

**Install MySQL:**
```bash
# Ubuntu/Debian
sudo apt-get install mysql-server

# CentOS/RHEL
sudo yum install mysql-server

# macOS
brew install mysql

# Start MySQL service
sudo systemctl start mysql    # Linux
brew services start mysql     # macOS
```

**Create Database:**
```sql
-- Connect as root
mysql -u root -p

-- Create database
CREATE DATABASE redrat_proxy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'redrat'@'localhost' IDENTIFIED BY 'your_secure_password';
CREATE USER 'redrat'@'%' IDENTIFIED BY 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON redrat_proxy.* TO 'redrat'@'localhost';
GRANT ALL PRIVILEGES ON redrat_proxy.* TO 'redrat'@'%';
FLUSH PRIVILEGES;
EXIT;
```

**Import Schema:**
```bash
mysql -u redrat -p redrat_proxy < mysql_schema.sql
```

### Option 2: Docker MySQL

Add MySQL service to `docker-compose.yml`:
```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: redrat_proxy
      MYSQL_USER: redrat
      MYSQL_PASSWORD: your_secure_password
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql_schema.sql:/docker-entrypoint-initdb.d/mysql_schema.sql
    ports:
      - "3306:3306"

volumes:
  mysql_data:
```

### Verify Database Setup

```bash
# Test connection
docker-compose exec web python -c "
from app.database import db
try:
    with db.get_connection() as conn:
        print('✅ Database connection successful')
        cursor = conn.cursor()
        cursor.execute('SHOW TABLES')
        tables = cursor.fetchall()
        print(f'Tables found: {len(tables)}')
        for table in tables:
            print(f'  - {table[0]}')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

## SSL/TLS Setup

### Generate Self-Signed Certificate (Development)

```bash
# Create SSL directory
mkdir -p ssl

# Generate certificate
openssl req -x509 -newkey rsa:4096 -keyout ssl/private.key -out ssl/certificate.crt -days 365 -nodes -subj "/CN=localhost"

# Set permissions
chmod 600 ssl/private.key
chmod 644 ssl/certificate.crt
```

### Production Certificate

For production, use certificates from a trusted CA:

```bash
# Let's Encrypt example
sudo apt-get install certbot
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/certificate.crt
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/private.key
```

### Configure HTTPS

Update `docker-compose.yml` for HTTPS:
```yaml
services:
  web:
    ports:
      - "443:5000"
    environment:
      - PREFERRED_URL_SCHEME=https
    volumes:
      - ./ssl:/app/ssl
```

## Production Deployment

### 1. Security Hardening

**Update default credentials:**
```bash
# Access container
docker-compose exec web bash

# Run password reset
python -c "
from app.auth import reset_admin_password
reset_admin_password('your_new_secure_password')
print('Admin password updated')
"
```

**Secure environment file:**
```bash
# Set restrictive permissions
chmod 600 .env
sudo chown root:root .env
```

### 2. Reverse Proxy Setup

**Apache Configuration:**
```apache
<VirtualHost *:443>
    ServerName your-domain.com
    
    SSLEngine on
    SSLCertificateFile /path/to/certificate.crt
    SSLCertificateKeyFile /path/to/private.key
    
    ProxyPreserveHost On
    ProxyRequests Off
    
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
    
    # Security headers
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options DENY
    Header always set X-XSS-Protection "1; mode=block"
    
    ErrorLog ${APACHE_LOG_DIR}/redrat_error.log
    CustomLog ${APACHE_LOG_DIR}/redrat_access.log combined
</VirtualHost>
```

**Nginx Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
```

### 3. Production Docker Compose

Use production configuration:
```bash
# Start with production settings
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or use make command
make prod-up
```

### 4. Monitoring and Logging

**Add health checks:**
```yaml
services:
  web:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Configure log rotation:**
```yaml
services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs web

# Check port usage
sudo netstat -tulpn | grep 5000

# Rebuild image
docker-compose build --no-cache
```

**Database connection errors:**
```bash
# Test MySQL connection
mysql -h localhost -u redrat -p redrat_proxy

# Check environment variables
docker-compose exec web env | grep MYSQL

# Test from container
docker-compose exec web python -c "
import mysql.connector
import os
try:
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB')
    )
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

**Permission errors:**
```bash
# Fix directory permissions
sudo chown -R $USER:$USER data/
chmod 755 data/
chmod 777 data/uploads data/remote_images
```

### Debug Mode

Enable debug logging:
```bash
# Update .env
echo "LOG_LEVEL=DEBUG" >> .env

# Restart container
docker-compose restart web

# View debug logs
docker-compose logs -f web
```

### Performance Issues

**Monitor resources:**
```bash
# Check container stats
docker stats

# Check system resources
htop
df -h
```

**Optimize Docker:**
```bash
# Clean up unused Docker resources
docker system prune -a

# Remove unused volumes
docker volume prune
```

## Maintenance

### Regular Tasks

**Database backup:**
```bash
# Create backup
make backup

# Or manual backup
mysqldump -u redrat -p redrat_proxy > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Update application:**
```bash
# Update code
git pull origin main

# Rebuild and restart
make update
```

**Check logs:**
```bash
# View recent logs
make logs

# Check for errors
docker-compose logs web | grep -i error
```

### Automated Maintenance

**Create maintenance script:**
```bash
cat > maintenance.sh << 'EOF'
#!/bin/bash
# Daily maintenance script

# Backup database
make backup

# Clean Docker resources
docker system prune -f

# Update application
git pull origin main
make update

# Check health
curl -f http://localhost:5000/health || echo "Health check failed"
EOF

chmod +x maintenance.sh

# Add to crontab
echo "0 2 * * * /path/to/maintenance.sh" | crontab -
```

## Support and Resources

### Documentation
- [Docker Setup Guide](DOCKER_SETUP.md)
- [Troubleshooting Guide](DOCKER_TROUBLESHOOTING.md)
- [Scheduler Documentation](SCHEDULER_README.md)

### Useful Commands
```bash
# View all Make commands
make help

# Quick status check
make status

# Access container shell
make shell

# View real-time logs
make logs

# Restart services
make restart

# Clean everything
make clean
```

### Health Check Endpoint

The application provides a health check endpoint:
```bash
curl http://localhost:5000/health
```

Response:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "1.0.0",
    "database": "connected"
}
```

## Conclusion

You now have a fully functional RedRat Proxy installation! The application provides:

- **Web Interface:** User-friendly dashboard for device management
- **API Access:** RESTful API for programmatic control
- **Device Management:** Add, configure, and control RedRat devices
- **Scheduling:** Automated task execution
- **Admin Panel:** User management and system configuration

For additional help, check the troubleshooting guide or review the application logs.

**Next Steps:**
1. Change default admin password
2. Add your RedRat devices
3. Configure scheduling as needed
4. Set up SSL for production use
5. Configure backup strategy

Happy controlling! 🎮
