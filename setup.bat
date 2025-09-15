@echo off
echo 🚀 Web Scraper Setup for Windows
echo ================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python is installed

REM Create virtual environment
echo 🔄 Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ❌ Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment and install dependencies
echo 🔄 Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Setup completed successfully!
echo.
echo Next steps:
echo 1. Run: venv\Scripts\activate.bat
echo 2. Run: python webscraper.py https://example.com
echo 3. Or run: python app.py
echo.
pause
