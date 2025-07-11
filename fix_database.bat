@echo off
REM Database troubleshooting script
ECHO ===================================
ECHO RedRat Proxy - Database Troubleshooter
ECHO ===================================
ECHO.

:MENU
ECHO Choose an option:
ECHO 1. Run database diagnostic
ECHO 2. Reset admin password only
ECHO 3. Rebuild and restart Docker container
ECHO 4. Full reset (drop and recreate database)
ECHO 0. Exit
ECHO.

SET /P CHOICE="Enter your choice (0-4): "

IF "%CHOICE%"=="1" (
    ECHO.
    ECHO Running database diagnostic...
    ECHO.
    
    REM Try to run directly first
    python db_diagnostic.py
    IF %ERRORLEVEL% NEQ 0 (
        ECHO.
        ECHO Direct execution failed. Trying with Docker...
        ECHO.
        docker-compose exec web python db_diagnostic.py
    )
    
    GOTO CONTINUE
)

IF "%CHOICE%"=="2" (
    ECHO.
    ECHO Resetting admin password...
    ECHO.
    
    REM Try to run directly first
    python reset_admin_password.py
    IF %ERRORLEVEL% NEQ 0 (
        ECHO.
        ECHO Direct execution failed. Trying with Docker...
        ECHO.
        docker-compose exec web python reset_admin_password.py
    )
    
    GOTO CONTINUE
)

IF "%CHOICE%"=="3" (
    ECHO.
    ECHO Rebuilding and restarting Docker container...
    ECHO.
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    
    ECHO.
    ECHO Container is starting up...
    ECHO Use docker-compose logs -f to monitor startup
    
    GOTO CONTINUE
)

IF "%CHOICE%"=="4" (
    ECHO.
    ECHO WARNING: This will PERMANENTLY DELETE your database and recreate it.
    ECHO All data will be lost!
    ECHO.
    SET /P CONFIRM="Are you SURE you want to continue? (yes/no): "
    
    IF /I "%CONFIRM%"=="yes" (
        ECHO.
        ECHO Dropping and recreating database...
        ECHO.
        
        REM Get MySQL connection parameters from environment or default values
        SET MYSQL_HOST=localhost
        IF DEFINED MYSQL_HOST_ENV SET MYSQL_HOST=%MYSQL_HOST_ENV%
        
        SET MYSQL_USER=redrat
        IF DEFINED MYSQL_USER_ENV SET MYSQL_USER=%MYSQL_USER_ENV%
        
        SET MYSQL_PASSWORD=redratpass
        IF DEFINED MYSQL_PASSWORD_ENV SET MYSQL_PASSWORD=%MYSQL_PASSWORD_ENV%
        
        SET MYSQL_DB=redrat_proxy
        IF DEFINED MYSQL_DB_ENV SET MYSQL_DB=%MYSQL_DB_ENV%
        
        ECHO Using MySQL settings:
        ECHO Host: %MYSQL_HOST%
        ECHO User: %MYSQL_USER%
        ECHO Database: %MYSQL_DB%
        ECHO.
        
        REM Try to use MySQL client if available, otherwise use Python
        WHERE mysql >nul 2>&1
        IF %ERRORLEVEL% EQU 0 (
            ECHO Using MySQL client...
            mysql -h %MYSQL_HOST% -u %MYSQL_USER% -p%MYSQL_PASSWORD% -e "DROP DATABASE IF EXISTS %MYSQL_DB%; CREATE DATABASE %MYSQL_DB%;"
            mysql -h %MYSQL_HOST% -u %MYSQL_USER% -p%MYSQL_PASSWORD% %MYSQL_DB% < mysql_schema.sql
        ) ELSE (
            ECHO MySQL client not found, using Python instead...
            python -c "import mysql.connector; conn = mysql.connector.connect(host='%MYSQL_HOST%', user='%MYSQL_USER%', password='%MYSQL_PASSWORD%'); cursor = conn.cursor(); cursor.execute('DROP DATABASE IF EXISTS %MYSQL_DB%'); cursor.execute('CREATE DATABASE %MYSQL_DB%'); conn.commit(); cursor.close(); conn.close(); print('Database dropped and recreated')"
            
            ECHO Importing schema with Python...
            python -c "import mysql.connector; import os; conn = mysql.connector.connect(host='%MYSQL_HOST%', user='%MYSQL_USER%', password='%MYSQL_PASSWORD%', database='%MYSQL_DB%'); cursor = conn.cursor(); schema = open('mysql_schema.sql', 'r').read(); statements = [s for s in schema.split(';') if s.strip()]; [cursor.execute(stmt) for stmt in statements if not (stmt.strip().startswith('CREATE DATABASE') or stmt.strip().startswith('USE'))]; conn.commit(); cursor.close(); conn.close(); print('Schema imported successfully')"
        )
        
        ECHO.
        ECHO Database has been reset. Restarting Docker container...
        docker-compose restart web
        
    ) ELSE (
        ECHO Database reset cancelled.
    )
    
    GOTO CONTINUE
)

IF "%CHOICE%"=="0" (
    EXIT /B 0
)

ECHO Invalid choice. Please try again.
GOTO MENU

:CONTINUE
ECHO.
ECHO Operation completed.
ECHO.
SET /P CONTINUE="Return to menu? (Y/N): "
IF /I "%CONTINUE%"=="Y" GOTO MENU
EXIT /B 0
