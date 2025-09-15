#!/bin/bash

echo "🚀 Web Scraper Setup for macOS/Linux"
echo "===================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python from https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python 3 is installed"

# Create virtual environment
echo "🔄 Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment and install dependencies
echo "🔄 Installing dependencies..."
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Run: source venv/bin/activate"
echo "2. Run: python webscraper.py https://example.com"
echo "3. Or run: python app.py"
echo ""
