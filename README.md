# RedRat Proxy

A modern web dashboard for the RedRat IrNetBox - infrared remote control system.

## Features

- 🔒 Secure login system
- 📱 Responsive UI built with Tailwind CSS
- 🎮 Manage remote controls
- 📊 Command history tracking
- 🔍 IRDB file management
- 👥 User management with admin controls

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

4. Initialize the database
   ```
   # On Windows
   mysql -u username -p < mysql_schema.sql
   
   # On Linux/Mac
   chmod +x init_db.sh
   ./init_db.sh
   ```

5. Start the application
   ```
   python -m app.app
   ```

6. Visit `http://localhost:5000/login` in your browser

## Development

### Tailwind CSS Development

To watch for changes in CSS files during development:

```
npm run dev:css
```

### Docker Deployment

1. Configure environment variables
   Create a `.env` file in the project root with your MySQL connection details:
   ```
   MYSQL_USER=your_mysql_user
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_DB=redrat
   ```

2. Start the container
   ```
   docker-compose up -d
   ```

This will start the Flask application in a container. The application will:
- Connect to MySQL running on your host machine
- Expose port 5000 on localhost, which your host's reverse proxy can forward to

### Reverse Proxy Configuration

The application is designed to work behind a reverse proxy. An example Apache configuration is provided in the `apache/redrat.conf` file, which you can use as a reference for setting up your reverse proxy on the Docker host.

## License

[MIT](LICENSE)
