@echo off
REM RedRat Proxy Utility Script
echo ===================================
echo RedRat Proxy Maintenance Utilities
echo ===================================

:MENU
echo.
echo 1. Reset Admin Password
echo 2. Run Housekeeping (clean up unused files)
echo 3. Run Login Diagnostic
echo 4. Update Logo to PNG
echo 0. Exit
echo.

set /p choice="Enter your choice (0-4): "

if "%choice%"=="1" (
    echo Running admin password reset...
    echo.
    python reset_admin_password.py
    goto CONTINUE
)

if "%choice%"=="2" (
    echo Running housekeeping...
    echo.
    python housekeeping.py
    goto CONTINUE
)

if "%choice%"=="3" (
    echo Running login diagnostic...
    echo.
    python login_diagnostic.py
    goto CONTINUE
)

if "%choice%"=="4" (
    echo This will convert the SVG logo to PNG format
    echo Running conversion script...
    python convert_logo.py
    goto CONTINUE
)

if "%choice%"=="0" (
    echo Exiting...
    goto END
)

echo Invalid choice! Please try again.
goto MENU

:CONTINUE
echo.
echo Press any key to return to the menu...
pause >nul
goto MENU

:END
