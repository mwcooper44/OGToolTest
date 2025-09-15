# Web Scraper Setup Guide

This guide will help you set up the web scraper application on any machine.

## Prerequisites

### 1. Python Installation
- **Python 3.8 or higher** is required
- Download from [python.org](https://www.python.org/downloads/)
- Make sure to check "Add Python to PATH" during installation

### 2. Google Chrome Browser
- Download and install [Google Chrome](https://www.google.com/chrome/)
- The scraper uses Chrome for JavaScript-heavy websites
- ChromeDriver will be automatically downloaded by the application

## Installation Steps

### 1. Clone or Download the Project
```bash
# If using git
git clone <repository-url>
cd OGToolTest

# Or download and extract the ZIP file
```

### 2. Create a Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install required packages
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
# Test the web scraper
python webscraper.py https://example.com

# Test the Flask app
python app.py
```

## Running the Application

### Option 1: Command Line Scraper
```bash
# Activate virtual environment first
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Run scraper on a specific URL
python webscraper.py https://quill.co

# The results will be saved as a JSON file
```

### Option 2: Web Interface
```bash
# Activate virtual environment first
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Start the Flask web server
python app.py

# Open your browser and go to:
# http://localhost:8080
```

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError" or "No module named 'requests'"
**Solution:** Make sure you're in the virtual environment and have installed the requirements:
```bash
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

#### 2. "ChromeDriver not found" or Selenium errors
**Solution:** The application will automatically download ChromeDriver, but if it fails:
- Make sure Google Chrome is installed
- Check your internet connection
- Try running the scraper again (it will retry the download)

#### 3. "Permission denied" errors on macOS/Linux
**Solution:** The application will automatically fix ChromeDriver permissions, but if it fails:
```bash
# Find the ChromeDriver location
find ~/.wdm -name "chromedriver" -type f

# Make it executable (replace with actual path)
chmod +x ~/.wdm/drivers/chromedriver/mac64/*/chromedriver-mac-arm64/chromedriver
```

#### 4. "gevent" installation fails
**Solution:** This is common on some systems. Try:
```bash
# Install gevent separately
pip install gevent==24.2.1

# If that fails, try without gevent (app will still work)
pip install flask-socketio
```

#### 5. Port already in use (Flask app)
**Solution:** The default port 5000 might be in use:
```bash
# Kill any process using port 5000
# On macOS/Linux:
lsof -ti:5000 | xargs kill -9

# On Windows:
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F
```

### System-Specific Notes

#### Windows
- Make sure Python is added to your PATH
- Use `venv\Scripts\activate` to activate virtual environment
- If you get SSL errors, try: `pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt`

#### macOS
- You might need to install Xcode command line tools: `xcode-select --install`
- If you get permission errors, use `pip install --user` instead

#### Linux (Ubuntu/Debian)
- Install required system packages:
```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv build-essential
```

## File Structure
```
OGToolTest/
├── app.py                 # Flask web application
├── webscraper.py         # Main scraper logic
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html       # Web interface template
├── static/              # CSS/JS files
├── scraped_results/     # Output directory for results
└── venv/               # Virtual environment (created during setup)
```

## Features
- **Static HTML scraping**: Fast scraping for simple websites
- **JavaScript rendering**: Uses Selenium for dynamic content
- **Rate limiting**: Respects website rate limits
- **User-Agent rotation**: Avoids detection
- **Web interface**: Easy-to-use browser interface
- **Real-time updates**: Live progress updates via WebSocket
- **Export options**: JSON output with structured data

## Usage Examples

### Scrape a simple website:
```bash
python webscraper.py https://example.com
```

### Scrape a JavaScript-heavy site:
```bash
python webscraper.py https://quill.co
```

### Use the web interface:
1. Run `python app.py`
2. Open http://localhost:5000
3. Enter URL and click "Start Scraping"
4. Watch real-time progress
5. Download results when complete

## Support
If you encounter issues not covered in this guide:
1. Check that all prerequisites are installed
2. Ensure you're using the virtual environment
3. Try running the scraper with a simple URL first (like example.com)
4. Check the console output for specific error messages
