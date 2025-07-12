@echo off
REM Cleanup script to remove unused files from RedRat project
ECHO ===================================
ECHO RedRat Proxy - Cleanup Script
ECHO ===================================
ECHO.
ECHO This script will remove unused files from the project.
ECHO The following files will be deleted:
ECHO.
ECHO 1. reset_admin.py (redundant, use reset_admin_password.py instead)
ECHO 2. check_db_health.py (functionality now in login_diagnostic.py)
ECHO 3. build_css.bat and build_css.sh (empty/unused files)
ECHO 4. init_db_manual.sh (integrated into Docker workflow)
ECHO 5. make_executable.sh (one-time utility)
ECHO 6. wait-for-it.sh (superseded by Docker health checks)
ECHO.

SET /P CONFIRM=Are you sure you want to delete these files? (Y/N): 
IF /I "%CONFIRM%" NEQ "Y" GOTO END

ECHO.
ECHO Deleting files...

IF EXIST reset_admin.py (
    DEL reset_admin.py
    ECHO - Deleted reset_admin.py
) ELSE (
    ECHO - reset_admin.py not found, skipping
)

IF EXIST check_db_health.py (
    DEL check_db_health.py
    ECHO - Deleted check_db_health.py
) ELSE (
    ECHO - check_db_health.py not found, skipping
)

IF EXIST build_css.bat (
    DEL build_css.bat
    ECHO - Deleted build_css.bat
) ELSE (
    ECHO - build_css.bat not found, skipping
)

IF EXIST build_css.sh (
    DEL build_css.sh
    ECHO - Deleted build_css.sh
) ELSE (
    ECHO - build_css.sh not found, skipping
)

IF EXIST init_db_manual.sh (
    DEL init_db_manual.sh
    ECHO - Deleted init_db_manual.sh
) ELSE (
    ECHO - init_db_manual.sh not found, skipping
)

IF EXIST make_executable.sh (
    DEL make_executable.sh
    ECHO - Deleted make_executable.sh
) ELSE (
    ECHO - make_executable.sh not found, skipping
)

IF EXIST wait-for-it.sh (
    DEL wait-for-it.sh
    ECHO - Deleted wait-for-it.sh
) ELSE (
    ECHO - wait-for-it.sh not found, skipping
)

ECHO.
ECHO ===================================
ECHO Cleanup complete!
ECHO ===================================

:END
