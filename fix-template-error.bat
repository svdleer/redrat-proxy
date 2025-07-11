@echo off
REM Script to fix the template error without rebuilding the container

echo Copying updated base.html to container...
docker cp app\templates\base.html redrat-proxy:/app/app/templates/base.html

echo Copying updated app.py to container...
docker cp app\app.py redrat-proxy:/app/app/app.py

echo Restarting the application...
docker exec redrat-proxy pkill -f "python app.py"
docker exec -d redrat-proxy bash -c "cd /app && python app.py"

echo Done! The template error should be fixed.
echo You may need to wait a few seconds for the application to restart.

pause
