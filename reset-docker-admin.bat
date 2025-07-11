@echo off
REM Execute admin password reset inside the Docker container
ECHO ===================================
ECHO RedRat Proxy - Reset Admin Password
ECHO ===================================
ECHO.
ECHO This script will reset the admin password to 'admin123'
ECHO.

SET /P CONFIRM="Are you sure you want to proceed? (Y/N): "
IF /I "%CONFIRM%" NEQ "Y" (
    ECHO Operation cancelled.
    EXIT /B 0
)

ECHO.
ECHO Resetting admin password in Docker container...
ECHO.

REM Make the script executable and run it in the container
docker-compose exec web bash -c "chmod +x /app/docker-reset-admin.sh && /app/docker-reset-admin.sh"

ECHO.
ECHO If the command was successful, the admin password has been reset.
ECHO You can now log in with:
ECHO   Username: admin
ECHO   Password: admin123
ECHO.
ECHO If you received any errors, check that:
ECHO 1. The Docker container is running
ECHO 2. The database connection details are correct
ECHO 3. The bcrypt module is installed in the container
ECHO.
PAUSE
