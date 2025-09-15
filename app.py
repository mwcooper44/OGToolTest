# Try to import gevent, but don't fail if it's not available
try:
    from gevent import monkey
    monkey.patch_all()
    print("✅ Gevent monkey patching enabled")
except ImportError:
    print("⚠️  Gevent not available, using default async mode")

from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import threading
import time
import os
import json
from datetime import datetime
from webscraper import WebScraper
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Try to use gevent if available, otherwise use threading
try:
    import gevent
    async_mode = 'gevent'
    print("✅ Using gevent async mode")
except ImportError:
    async_mode = 'threading'
    print("⚠️  Using threading async mode (gevent not available)")

socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# Global variables to track scraping status
scraping_status = {
    'is_running': False,
    'current_url': '',
    'progress': 0,
    'total_pages': 0,
    'console_output': [],
    'results_file': None,
    'cancelled': False
}

class ConsoleOutput:
    """Custom console output handler that sends updates via WebSocket"""
    def __init__(self):
        self.output_lines = []
        self.max_lines = 100  # Increased from 10 to 100 for scrollable console
    
    def write(self, message):
        """Write message to console and emit via WebSocket"""
        if message.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message.strip()}"
            
            self.output_lines.append(formatted_message)
            
            # Keep only last 100 lines
            if len(self.output_lines) > self.max_lines:
                self.output_lines.pop(0)
            
            # Emit real-time update to all connected clients
            socketio.emit('console_update', {
                'message': formatted_message,
                'lines': self.output_lines.copy(),
                'is_realtime': True
            })
    
    def flush(self):
        pass

# Redirect stdout to our custom console output
import sys
console_output = ConsoleOutput()
sys.stdout = console_output

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start_scraping')
def handle_start_scraping(data):
    """Handle scraping request via WebSocket"""
    global scraping_status
    sid = request.sid
    
    if scraping_status['is_running']:
        emit('error', {'message': 'Scraping is already in progress'})
        return
    
    url = data.get('url', '').strip()
    if not url:
        emit('error', {'message': 'URL is required'})
        return
    
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Reset status
    scraping_status.update({
        'is_running': True,
        'current_url': url,
        'progress': 0,
        'total_pages': 0,
        'console_output': [],
        'results_file': None,
        'cancelled': False
    })
    
    # Start scraping in background task
    socketio.start_background_task(run_scraper_background, sid, url)
    emit('scraping_started', {'message': 'Scraping started', 'url': url})

@app.route('/api/status')
def get_status():
    return jsonify(scraping_status)

@app.route('/api/cancel', methods=['POST'])
def cancel_scraping():
    """Cancel the current scraping operation"""
    global scraping_status
    
    if scraping_status['is_running']:
        scraping_status['is_running'] = False
        scraping_status['cancelled'] = True
        print("🛑 Scraping cancelled by user")
        
        # Emit cancellation event
        socketio.emit('scraping_cancelled', {
            'message': 'Scraping has been cancelled'
        })
        
        return jsonify({'message': 'Scraping cancelled'})
    else:
        return jsonify({'message': 'No active scraping to cancel'}), 400

@app.route('/api/download')
def download_results():
    if not scraping_status['results_file'] or not os.path.exists(scraping_status['results_file']):
        return jsonify({'error': 'No results available for download'}), 404
    
    # Extract domain from the current URL for download filename
    current_url = scraping_status.get('current_url', '')
    if current_url:
        domain = current_url.replace('https://', '').replace('http://', '').split('/')[0]
        download_name = f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    else:
        download_name = f"scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return send_file(
        scraping_status['results_file'],
        as_attachment=True,
        download_name=download_name
    )

def run_scraper_background(sid, url):
    """Run the web scraper in a background task with real-time WebSocket updates"""
    global scraping_status
    
    with app.app_context():
        try:
            # Emit start message
            socketio.emit('log_message', {'data': f"🚀 Starting to scrape: {url}"}, to=sid)
            
            # Create scraper instance
            scraper = WebScraper(url, max_pages=50, delay=2.0)
            
            # Set up cancellation checking
            def check_cancellation():
                return scraping_status.get('cancelled', False)
            
            scraper.check_cancellation = check_cancellation
            
            # Override the scraper's print function to emit real-time messages
            original_print = print
            def custom_print(*args, **kwargs):
                message = ' '.join(str(arg) for arg in args)
                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted_message = f"[{timestamp}] {message.strip()}"
                
                # Emit immediately to the specific client
                socketio.emit('log_message', {'data': formatted_message}, to=sid)
            
            # Temporarily replace print
            import builtins
            builtins.print = custom_print
            
            # Run the scraper with cancellation check
            results = scraper.scrape_website()
            
            # Check if scraping was cancelled
            if scraping_status.get('cancelled', False):
                socketio.emit('log_message', {'data': "🛑 Scraping was cancelled by user"}, to=sid)
                return
            
            # Restore original print
            builtins.print = original_print
            
            # Save results to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            domain = url.replace('https://', '').replace('http://', '').split('/')[0]
            filename = f"{domain}_{timestamp}.json"
            filepath = os.path.join('scraped_results', filename)
            
            # Create directory if it doesn't exist
            os.makedirs('scraped_results', exist_ok=True)
            
            # Save results
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            # Update status
            scraping_status.update({
                'is_running': False,
                'progress': 100,
                'results_file': filepath,
                'total_pages': len(results.get('items', []))
            })
            
            # Emit completion messages
            socketio.emit('log_message', {'data': f"✅ Scraping completed! Found {len(results.get('items', []))} items"}, to=sid)
            socketio.emit('log_message', {'data': f"📁 Results saved to: {filename}"}, to=sid)
            socketio.emit('log_message', {'data': "🎉 Ready for download!"}, to=sid)
            
            # Emit completion event
            socketio.emit('scraping_complete', {
                'total_items': len(results.get('items', [])),
                'filename': filename
            }, to=sid)
            
        except Exception as e:
            # Restore original print
            import builtins
            builtins.print = original_print
            
            # Emit error message
            socketio.emit('log_message', {'data': f"❌ Error during scraping: {str(e)}"}, to=sid)
            
            # Update status
            scraping_status.update({
                'is_running': False,
                'progress': 0
            })
            
            # Emit error event
            socketio.emit('scraping_error', {
                'error': str(e)
            }, to=sid)

def send_heartbeat():
    """Send periodic heartbeat to keep WebSocket connection alive"""
    while scraping_status['is_running']:
        try:
            socketio.emit('heartbeat', {'timestamp': datetime.now().isoformat()})
            time.sleep(10)  # Send heartbeat every 10 seconds
        except:
            break

@socketio.on('connect')
def handle_connect():
    emit('console_update', {
        'lines': console_output.output_lines.copy()
    })

@socketio.on('disconnect')
def handle_disconnect():
    pass

@socketio.on('heartbeat_response')
def handle_heartbeat_response():
    """Handle heartbeat response from client"""
    pass

@socketio.on('test')
def handle_test(data):
    """Handle test message from client"""
    print(f"Received test message: {data}")
    socketio.emit('test_response', {'message': 'Test successful!'})

if __name__ == '__main__':
    # Create scraped_results directory
    os.makedirs('scraped_results', exist_ok=True)
    
    print("🌐 WebScraper is starting up...")
    print("📡 Server will be available at: http://localhost:8080")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
