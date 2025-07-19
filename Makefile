# Makefile for RedRat Proxy Docker Management
# Production-only commands for Docker operations

.PHONY: help build up down restart logs shell clean setup backup

# Default target
help:
	@echo "RedRat Proxy Docker Management"
	@echo "=============================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup     - Quick setup with guided configuration"
	@echo "  make build     - Build Docker image"
	@echo "  make rebuild   - Rebuild Docker image (no cache)"
	@echo ""
	@echo "Production Commands:"
	@echo "  make up        - Start production containers"
	@echo "  make up-fg     - Start production containers (foreground)"
	@echo "  make down      - Stop production containers"
	@echo "  make restart   - Restart production containers"
	@echo "  make logs      - View production logs"
	@echo "  make shell     - Access container shell"
	@echo "  make status    - Show container status"
	@echo ""
	@echo "Maintenance Commands:"
	@echo "  make clean     - Remove containers, images, and volumes"
	@echo "  make clean-all - Deep clean (removes images too)"
	@echo "  make fix-config - Fix ContainerConfig errors"
	@echo "  make test-app  - Test Flask app import"
	@echo "  make verify    - Verify setup and test system"
	@echo "  make backup    - Backup database"
	@echo "  make restore   - Restore database from backup"
	@echo "  make reset     - Reset admin password"
	@echo "  make update    - Update and rebuild application"
	@echo ""

# Quick setup
setup:
	@echo "🚀 Starting RedRat Proxy setup..."
	@bash docker-setup.sh

# Build Docker image
build:
	@echo "🔨 Building Docker image..."
	docker-compose build

# Force rebuild (no cache)
rebuild:
	@echo "🔨 Rebuilding Docker image (no cache)..."
	docker-compose build --no-cache

# Start production containers
up:
	@echo "🚀 Starting production containers..."
	docker-compose up -d
	@echo "✅ Production application started at http://localhost:5000"

# Start containers in foreground
up-fg:
	@echo "🚀 Starting production containers (foreground)..."
	docker-compose up

# Stop containers
down:
	@echo "🛑 Stopping production containers..."
	docker-compose down

# Restart containers
restart:
	@echo "🔄 Restarting production containers..."
	docker-compose restart

# View logs
logs:
	@echo "📋 Viewing production logs..."
	docker-compose logs -f web

# Test Flask app import
test-app:
	@echo "🧪 Testing Flask app import..."
	docker-compose exec web python /app/test_app_import.py

# Verify setup
verify:
	@echo "🔍 Verifying setup..."
	@chmod +x verify_setup.sh
	@./verify_setup.sh

# Access container shell
shell:
	@echo "🐚 Accessing container shell..."
	docker-compose exec web bash

# Show container status
status:
	@echo "📊 Container status:"
	docker-compose ps

# Clean up
clean:
	@echo "🧹 Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup completed"

# Deep clean (removes images too)
clean-all:
	@echo "🧹 Deep cleaning Docker resources..."
	docker-compose down -v --rmi all
	docker system prune -af
	@echo "✅ Deep cleanup completed"

# Fix ContainerConfig errors
fix-config:
	@echo "🔧 Fixing ContainerConfig errors..."
	docker-compose down
	docker system prune -f
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✅ ContainerConfig error fixed"

# Database backup
backup:
	@echo "💾 Creating database backup..."
	@if [ -f .env ]; then \
		export $$(cat .env | grep -v '^#' | xargs); \
		mkdir -p backups; \
		BACKUP_FILE="backups/redrat_proxy_$$(date +%Y%m%d_%H%M%S).sql"; \
		mysqldump -h $${MYSQL_HOST:-localhost} -u $${MYSQL_USER:-redrat} -p$${MYSQL_PASSWORD:-redratpass} $${MYSQL_DB:-redrat_proxy} > $$BACKUP_FILE; \
		gzip $$BACKUP_FILE; \
		echo "✅ Backup created: $$BACKUP_FILE.gz"; \
	else \
		echo "❌ .env file not found"; \
	fi

# Database restore
restore:
	@echo "🔄 Restoring database from backup..."
	@read -p "Enter backup file path: " BACKUP_FILE; \
	if [ -f "$$BACKUP_FILE" ]; then \
		export $$(cat .env | grep -v '^#' | xargs); \
		if [[ $$BACKUP_FILE == *.gz ]]; then \
			gunzip -c $$BACKUP_FILE | mysql -h $${MYSQL_HOST:-localhost} -u $${MYSQL_USER:-redrat} -p$${MYSQL_PASSWORD:-redratpass} $${MYSQL_DB:-redrat_proxy}; \
		else \
			mysql -h $${MYSQL_HOST:-localhost} -u $${MYSQL_USER:-redrat} -p$${MYSQL_PASSWORD:-redratpass} $${MYSQL_DB:-redrat_proxy} < $$BACKUP_FILE; \
		fi; \
		echo "✅ Database restored successfully"; \
	else \
		echo "❌ Backup file not found"; \
	fi

# Reset admin password
reset:
	@echo "🔑 Resetting admin password..."
	docker-compose exec web python docker-reset-admin.sh

# Run tests
test:
	@echo "🧪 Running application tests..."
	docker-compose exec web python -m pytest tests/ -v

# Update application
update:
	@echo "🔄 Updating application..."
	git pull origin main
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✅ Application updated successfully"

# Check application health
health:
	@echo "🏥 Checking application health..."
	@curl -f http://localhost:5000/ > /dev/null 2>&1 && echo "✅ Application is healthy" || echo "❌ Application is not responding"

# Monitor logs in real-time
monitor:
	@echo "📊 Monitoring application logs..."
	docker-compose logs -f --tail=100 web

# Show application info
info:
	@echo "ℹ️  Application Information:"
	@echo "  Project: RedRat Proxy (Production)"
	@echo "  URL: http://localhost:5000"
	@echo "  Docker Compose Version: $$(docker-compose version --short)"
	@echo "  Docker Version: $$(docker version --format '{{.Client.Version}}')"
	@echo ""
	@echo "📁 Directory Structure:"
	@echo "  Config: .env"
	@echo "  Data: ./data/"
	@echo "  Logs: ./logs/ (and docker-compose logs)"
	@echo "  Backups: ./backups/"
