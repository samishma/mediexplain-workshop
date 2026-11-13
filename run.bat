@echo off
echo ========================================================
echo Starting MediExplain - Medical Document Understanding MVP
echo ========================================================
echo.
cd /d "%~dp0"
echo Initializing database and starting server on http://localhost:8080 ...
echo Open your web browser and navigate to: http://localhost:8080
echo.
python server.py
pause
