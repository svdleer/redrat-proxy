@echo off
REM Comprehensive cleanup script for RedRat project
ECHO ===================================
ECHO RedRat Proxy - Advanced Cleanup
ECHO ===================================
ECHO.

REM Set this to 1 to actually delete files, 0 for dry run
SET DELETE_FILES=1

ECHO Scanning for unused script files...
ECHO.

SET FOUND_FILES=0

REM Development scripts
IF EXIST setup_venv.sh (
    ECHO Found: setup_venv.sh (Development setup script)
    SET FOUND_FILES=1
    IF %DELETE_FILES%==1 (
        DEL setup_venv.sh
        ECHO - Deleted setup_venv.sh
    )
)

IF EXIST run_dev.sh (
    ECHO Found: run_dev.sh (Development run script)
    SET FOUND_FILES=1
    IF %DELETE_FILES%==1 (
        DEL run_dev.sh
        ECHO - Deleted run_dev.sh
    )
)

REM Empty or redundant build scripts
IF EXIST build_css.bat (
    ECHO Found: build_css.bat (Empty/unused build script)
    SET FOUND_FILES=1
    IF %DELETE_FILES%==1 (
        DEL build_css.bat
        ECHO - Deleted build_css.bat
    )
)

IF EXIST build_css.sh (
    ECHO Found: build_css.sh (Empty/unused build script)
    SET FOUND_FILES=1
    IF %DELETE_FILES%==1 (
        DEL build_css.sh
        ECHO - Deleted build_css.sh
    )
)

REM Redundant admin reset script
IF EXIST reset_admin.py (
    ECHO Found: reset_admin.py (Redundant admin reset script)
    SET FOUND_FILES=1
    IF %DELETE_FILES%==1 (
        DEL reset_admin.py
        ECHO - Deleted reset_admin.py
    )
)

REM Obsolete DB utilities
IF EXIST check_db_health.py (
    ECHO Found: check_db_health.py (Obsolete DB utility)
    SET FOUND_FILES=1
    IF %DELETE_FILES%==1 (
        DEL check_db_health.py
        ECHO - Deleted check_db_health.py
    )
)

REM Redundant setup scripts
IF EXIST init_db_manual.sh (
    ECHO Found: init_db_manual.sh (Redundant DB init script)
    SET FOUND_FILES=1
    IF %DELETE_FILES%==1 (
        DEL init_db_manual.sh
        ECHO - Deleted init_db_manual.sh
    )
)

IF EXIST make_executable.sh (
    ECHO Found: make_executable.sh (One-time utility)
    SET FOUND_FILES=1
    IF %DELETE_FILES%==1 (
        DEL make_executable.sh
        ECHO - Deleted make_executable.sh
    )
)

IF EXIST wait-for-it.sh (
    ECHO Found: wait-for-it.sh (Redundant utility)
    SET FOUND_FILES=1
    IF %DELETE_FILES%==1 (
        DEL wait-for-it.sh
        ECHO - Deleted wait-for-it.sh
    )
)

REM Other potential unnecessary files
SET FILES_TO_CHECK=pytest.ini tailwind.config.js postcss.config.js package.json

FOR %%F IN (%FILES_TO_CHECK%) DO (
    IF EXIST %%F (
        ECHO Found: %%F (Potentially unnecessary file)
        SET FOUND_FILES=1
        IF %DELETE_FILES%==1 (
            DEL %%F
            ECHO - Deleted %%F
        )
    )
)

IF %FOUND_FILES%==0 (
    ECHO No unused files found.
)

ECHO.
IF %DELETE_FILES%==1 (
    ECHO ===================================
    ECHO Cleanup complete!
    ECHO ===================================
) ELSE (
    ECHO ===================================
    ECHO Dry run completed. No files were deleted.
    ECHO ===================================
)
