@echo off
echo ===================================
echo  MalgeunTube Server Starting...
echo ===================================
echo.

cd /d %~dp0
call venv\Scripts\activate.bat

echo Starting Flask server...
python app.py

echo.
echo Server stopped.
pause

