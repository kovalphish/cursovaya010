@echo off
echo ==========================================
echo   Setup and Run Flask Application
echo ==========================================
echo.

REM Find Python installation
echo Searching for Python...
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo Python found!
    set PYTHON_CMD=python
) else (
    echo Trying py...
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        echo py found!
        set PYTHON_CMD=py
    ) else (
        echo.
        echo ERROR: Python not found in PATH!
        echo Please install Python from https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
)

echo.
echo Python version:
%PYTHON_CMD% --version

echo.
echo Creating virtual environment...
%PYTHON_CMD% -m venv venv

echo.
echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Installing Flask...
pip install flask

echo.
echo Initializing database...
%PYTHON_CMD% -c "import sqlite3; conn = sqlite3.connect('database.db'); cursor = conn.cursor(); cursor.execute('CREATE TABLE IF NOT EXISTS Fines (id INTEGER PRIMARY KEY AUTOINCREMENT, CarNumber TEXT NOT NULL, Violation TEXT, Amount REAL, VioTime TEXT, Location TEXT)'); conn.commit(); conn.close(); print('Database initialized!')"

echo.
echo ==========================================
echo   Starting Flask Application
echo ==========================================
echo   Open your browser to: http://127.0.0.1:5000
echo   Press Ctrl+C to stop the server
echo ==========================================
echo.

%PYTHON_CMD% app.py

pause