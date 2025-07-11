@echo off
REM Script to import remotes.xml into the database in Docker container

echo Copying remotes.xml to container...
docker cp remotes.xml redrat-proxy:/app/remotes.xml

echo Copying import script to container...
docker cp import_remotes.py redrat-proxy:/app/import_remotes.py

echo Importing remotes into database...
docker exec redrat-proxy python3 /app/import_remotes.py

echo Done! Remote data imported to database.
pause
