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
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

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
        self.max_lines = 10
    
    def write(self, message):
        """Write message to console and emit via WebSocket"""
        if message.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message.strip()}"
            
            self.output_lines.append(formatted_message)
            
            # Keep only last 10 lines
            if len(self.output_lines) > self.max_lines:
                self.output_lines.pop(0)
            
            # Emit to all connected clients
            socketio.emit('console_update', {
                'message': formatted_message,
                'lines': self.output_lines.copy()
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

@app.route('/api/start_scraping', methods=['POST'])
def start_scraping():
    global scraping_status
    
    if scraping_status['is_running']:
        return jsonify({'error': 'Scraping is already in progress'}), 400
    
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
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
    
    # Start scraping in a separate thread
    thread = threading.Thread(target=run_scraper, args=(url,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Scraping started', 'url': url})

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
    
    return send_file(
        scraping_status['results_file'],
        as_attachment=True,
        download_name=f"scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

def run_scraper(url):
    """Run the web scraper in a separate thread"""
    global scraping_status
    
    try:
        print(f"🚀 Starting to scrape: {url}")
        
        # Create scraper instance
        scraper = WebScraper(url, max_pages=50, delay=2.0)
        
        # Set up cancellation checking
        def check_cancellation():
            return scraping_status.get('cancelled', False)
        
        scraper.check_cancellation = check_cancellation
        
        # Start heartbeat thread to keep connection alive
        heartbeat_thread = threading.Thread(target=send_heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()
        
        # Override the scraper's print function to use our console output
        original_print = print
        def custom_print(*args, **kwargs):
            message = ' '.join(str(arg) for arg in args)
            console_output.write(message)
            console_output.write('\n')
            
            # Add to console output list and emit to frontend
            scraping_status['console_output'].append(message)
            if len(scraping_status['console_output']) > 10:
                scraping_status['console_output'] = scraping_status['console_output'][-10:]
            
            # Emit console update to frontend
            socketio.emit('console_update', {
                'lines': scraping_status['console_output']
            })
        
        # Temporarily replace print
        import builtins
        builtins.print = custom_print
        
        # Run the scraper with cancellation check
        results = scraper.scrape_website()
        
        # Check if scraping was cancelled
        if scraping_status.get('cancelled', False):
            print("🛑 Scraping was cancelled by user")
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
        
        print(f"✅ Scraping completed! Found {len(results.get('items', []))} items")
        print(f"📁 Results saved to: {filename}")
        print("🎉 Ready for download!")
        
        # Emit completion event
        socketio.emit('scraping_complete', {
            'total_items': len(results.get('items', [])),
            'filename': filename
        })
        
    except Exception as e:
        # Restore original print
        import builtins
        builtins.print = original_print
        
        print(f"❌ Error during scraping: {str(e)}")
        
        # Update status
        scraping_status.update({
            'is_running': False,
            'progress': 0
        })
        
        # Emit error event
        socketio.emit('scraping_error', {
            'error': str(e)
        })

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

if __name__ == '__main__':
    # Create scraped_results directory
    os.makedirs('scraped_results', exist_ok=True)
    
    print("🌐 WebScraper is starting up...")
    print("📡 Server will be available at: http://localhost:8080")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
