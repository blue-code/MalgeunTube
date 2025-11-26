@echo off
echo ========================================
echo    MalgeunTube Setup
echo ========================================
echo. 

echo [1/4] Creating virtual environment...
python -m venv venv
echo Done! 
echo.

echo [2/4] Activating virtual environment... 
call venv\Scripts\activate.bat
echo Done! 
echo.

echo [3/4] Installing dependencies...
pip install Flask yt-dlp
echo Done!
echo. 

echo [4/4] Creating directories...
if not exist "static\css" mkdir static\css
if not exist "static\js" mkdir static\js
if not exist "templates" mkdir templates
if not exist "data" mkdir data
echo Done!
echo. 

echo ========================================
echo    Setup Complete!
echo ========================================
echo. 
echo To run: run.bat
echo. 
pause