@echo off
rem Install NPM dependencies
echo Installing NPM dependencies...
call npm install

rem Build the Tailwind CSS
echo Building Tailwind CSS...
call npm run build:css

echo Tailwind CSS built successfully!
