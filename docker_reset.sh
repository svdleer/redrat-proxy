#!/bin/bash

# Docker-specific service reset script
# Run this on the production server after deployment

echo "🐳 Docker RedRat Service Reset"
echo "============================="

# Check if Docker Compose is running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Docker containers are not running"
    echo "Please start with: docker-compose up -d"
    exit 1
fi

echo "🔄 Resetting RedRat service cache in Docker container..."

# Reset service cache inside the container
docker-compose exec web python reset_service_cache.py

if [ $? -eq 0 ]; then
    echo "✅ Service cache reset successfully"
else
    echo "❌ Failed to reset service cache"
    exit 1
fi

echo ""
echo "🔍 Checking container logs..."
docker-compose logs --tail=20 web

echo ""
echo "✅ Reset complete!"
echo "Try executing a command through the web interface to test the fix."
