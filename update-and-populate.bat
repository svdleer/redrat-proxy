@echo off
REM Script to update the database schema and create test data without rebuilding the container

echo Copying updated schema file to container...
docker cp mysql_schema.sql redrat-proxy:/app/mysql_schema.sql

echo Updating database schema...
docker exec redrat-proxy python3 -c "from app.mysql_db import db; db.init_db(force_recreate=True)"

echo Creating test data...
docker exec redrat-proxy python3 /app/create_test_data.py

echo Done! You can now access the dashboard with test data.
pause
