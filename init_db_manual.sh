#!/bin/bash
# Database initialization script
# This can be run manually if needed outside of Docker

# Source environment variables if .env file exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Use environment variables or default values
MYSQL_HOST=${MYSQL_HOST:-"mysql"}
MYSQL_PORT=${MYSQL_PORT:-"3306"}
MYSQL_USER=${MYSQL_USER:-"redrat"}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-"redratpass"}
MYSQL_DB=${MYSQL_DB:-"redrat_proxy"}

echo "Initializing database: $MYSQL_DB on $MYSQL_HOST:$MYSQL_PORT"
echo "Using user: $MYSQL_USER"

# Create database if it doesn't exist
mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p"$MYSQL_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS $MYSQL_DB;"

# Apply schema
if [ $? -eq 0 ]; then
    echo "Database created or already exists. Applying schema..."
    mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p"$MYSQL_PASSWORD" $MYSQL_DB < mysql_schema.sql
    
    if [ $? -eq 0 ]; then
        echo "Schema applied successfully!"
    else
        echo "Error applying schema. Check errors above."
        exit 1
    fi
else
    echo "Error creating database. Check connection parameters."
    exit 1
fi

echo "Database initialization completed."
