#!/usr/bin/env python3
"""
Setup script for the Web Scraper application.
This script will create a virtual environment and install all dependencies.
"""

import os
import sys
import subprocess
import platform

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_chrome():
    """Check if Chrome is installed."""
    system = platform.system().lower()
    
    if system == "windows":
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
    elif system == "darwin":  # macOS
        chrome_paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    else:  # Linux
        chrome_paths = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print("✅ Google Chrome is installed")
            return True
    
    print("⚠️  Google Chrome not found. Please install Chrome from https://www.google.com/chrome/")
    return False

def main():
    """Main setup function."""
    print("🚀 Web Scraper Setup Script")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check Chrome installation
    check_chrome()
    
    # Determine activation command based on OS
    system = platform.system().lower()
    if system == "windows":
        activate_cmd = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
    else:
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
    
    # Create virtual environment
    if not run_command("python -m venv venv", "Creating virtual environment"):
        sys.exit(1)
    
    # Upgrade pip
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        print("⚠️  Pip upgrade failed, continuing with installation...")
    
    # Install requirements
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing dependencies"):
        print("❌ Failed to install dependencies")
        print("Try running manually:")
        print(f"  {activate_cmd}")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    
    # Test installation
    print("\n🧪 Testing installation...")
    
    if not run_command("python test_imports.py", "Testing imports"):
        print("❌ Installation test failed")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print(f"1. Activate the virtual environment: {activate_cmd}")
    print("2. Run the scraper: python webscraper.py https://example.com")
    print("3. Or start the web app: python app.py")
    print("\nFor detailed instructions, see SETUP.md")

if __name__ == "__main__":
    main()
