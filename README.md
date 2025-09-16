# Web Scraper

Web scraper to be used in my consulting club project this semester. (AI Marketing tool)

## Quick Start

### Option 1: Automated Setup (Recommended)

**Windows:**
```bash
# Double-click setup.bat or run in command prompt
setup.bat
```

**macOS/Linux:**
```bash
# Run the setup script
./setup.sh
```

### Option 2: Manual Setup

1. **Prerequisites:**
   - Python 3.8 or higher
   - Google Chrome browser

2. **Install Dependencies:**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Run the Application:**
   ```bash
   python app.py
   ```

4. **Open in Browser:**
   Navigate to `http://localhost:8080`

## Usage

### Web Interface
1. Enter a website URL in the input field
2. Click "Start Scraping" or press Enter
3. Watch real-time console output
4. Download the JSON results when complete

### Command Line
```bash
# Scrape a website directly
python webscraper.py https://example.com

# Results will be saved as a JSON file
```

## Features

- **Static HTML scraping**: Fast scraping for simple websites
- **JavaScript rendering**: Uses Selenium for dynamic content
- **Rate limiting**: Respects website rate limits
- **User-Agent rotation**: Avoids detection
- **Web interface**: Easy-to-use browser interface
- **Real-time updates**: Live progress updates via WebSocket
- **Export options**: JSON output with structured data

## Troubleshooting

If you encounter issues, see the detailed [SETUP.md](SETUP.md) guide for comprehensive troubleshooting steps.

## File Structure
```
├── app.py                 # Flask web application
├── webscraper.py         # Main scraper logic
├── requirements.txt      # Python dependencies
├── setup.py             # Automated setup script
├── setup.bat            # Windows setup script
├── setup.sh             # macOS/Linux setup script
├── SETUP.md             # Detailed setup guide
├── templates/
│   └── index.html       # Web interface template
├── static/              # CSS/JS files
└── scraped_results/     # Output directory for results
```

