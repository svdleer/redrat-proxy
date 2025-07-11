@echo off
REM Script to set up and activate Python virtual environment for RedRat project

echo Setting up Python virtual environment...

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating new virtual environment...
    python -m venv venv
    echo Virtual environment created!
)

REM Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Virtual environment is ready!
echo To manually activate the environment, run: venv\Scripts\activate
echo.
