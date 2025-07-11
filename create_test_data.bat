@echo off
REM Script to create test data in the Docker container for the dashboard

echo Creating test data for the RedRat dashboard...
docker exec redrat-proxy python3 /app/create_test_data.py

if %ERRORLEVEL% EQU 0 (
  echo Test data created successfully!
  echo You can now view the dashboard with sample data.
) else (
  echo Failed to create test data.
  echo Check that the Docker container is running and the database is accessible.
)

pause
