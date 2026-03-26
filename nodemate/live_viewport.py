"""
Live Viewport Server - Remote Window Monitoring
Lightweight Flask server for live window viewing.
"""

from __future__ import annotations

import threading
import time
import io
import base64
from typing import Optional, Dict, Any
import logging
from flask import Flask, Response, request, jsonify
from PIL import ImageGrab
import win32gui
import win32con

logger = logging.getLogger(__name__)


class LiveViewportServer:
    """Lightweight Flask server for live window viewing."""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = Flask(__name__)
        self.app.config['JSON_AS_ASCII'] = False
        
        # Store registered windows
        self.registered_windows: Dict[str, Dict] = {}
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"LiveViewportServer initialized on port {port}")
    
    def _setup_routes(self) -> None:
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            return self._get_main_page()
        
        @self.app.route('/screenshot')
        def screenshot():
            """Get current screenshot of window."""
            window_name = request.args.get('window', '')
            return self._get_screenshot(window_name)
        
        @self.app.route('/click', methods=['POST'])
        def click():
            """Execute surgical click on window."""
            data = request.get_json()
            return self._execute_click(data)
        
        @self.app.route('/windows')
        def windows():
            """Get list of available windows."""
            return jsonify(self._get_available_windows())
        
        @self.app.route('/register', methods=['POST'])
        def register():
            """Register a window for monitoring."""
            data = request.get_json()
            return self._register_window(data)
    
    def _get_main_page(self) -> str:
        """Get main HTML page."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Node-Mate Live Viewport</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .controls { display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }
        .window-select { padding: 10px; background: #2d2d2d; border: none; color: #fff; border-radius: 5px; }
        .screenshot-container { text-align: center; margin: 20px 0; }
        .screenshot { max-width: 100%; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        .click-area { position: absolute; border: 2px solid #ff0000; background: rgba(255,0,0,0.2); cursor: crosshair; }
        .info { background: #2d2d2d; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        .refresh-btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ Node-Mate Live Viewport</h1>
            <p>Real-time window monitoring and surgical control</p>
        </div>
        
        <div class="controls">
            <select id="windowSelect" class="window-select" onchange="changeWindow()">
                <option value="">Select Window</option>
            </select>
            <button class="refresh-btn" onclick="refreshScreenshot()">🔄 Refresh</button>
            <button class="refresh-btn" onclick="toggleAutoRefresh()">⏱️ Auto Refresh</button>
        </div>
        
        <div class="info">
            <strong>Instructions:</strong> Click anywhere on the screenshot to execute surgical click on the actual window.
        </div>
        
        <div class="screenshot-container">
            <div id="screenshotWrapper" style="position: relative; display: inline-block;">
                <img id="screenshot" class="screenshot" src="" alt="Select a window">
                <div id="clickArea" class="click-area" style="display: none;"></div>
            </div>
        </div>
        
        <div class="info">
            <p><strong>Last Update:</strong> <span id="lastUpdate">Never</span></p>
            <p><strong>Auto Refresh:</strong> <span id="autoStatus">Off</span></p>
        </div>
    </div>

    <script>
        let autoRefresh = null;
        let currentWindow = '';
        
        function loadWindows() {
            fetch('/windows')
                .then(response => response.json())
                .then(windows => {
                    const select = document.getElementById('windowSelect');
                    select.innerHTML = '<option value="">Select Window</option>';
                    windows.forEach(window => {
                        select.innerHTML += `<option value="${window.name}">${window.name}</option>`;
                    });
                });
        }
        
        function changeWindow() {
            currentWindow = document.getElementById('windowSelect').value;
            if (currentWindow) {
                loadScreenshot();
            }
        }
        
        function loadScreenshot() {
            if (!currentWindow) return;
            
            fetch(`/screenshot?window=${encodeURIComponent(currentWindow)}`)
                .then(response => response.blob())
                .then(blob => {
                    const url = URL.createObjectURL(blob);
                    document.getElementById('screenshot').src = url;
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                });
        }
        
        function refreshScreenshot() {
            loadScreenshot();
        }
        
        function toggleAutoRefresh() {
            if (autoRefresh) {
                clearInterval(autoRefresh);
                autoRefresh = null;
                document.getElementById('autoStatus').textContent = 'Off';
            } else {
                autoRefresh = setInterval(loadScreenshot, 2000); // Refresh every 2 seconds
                document.getElementById('autoStatus').textContent = 'On (2s)';
                loadScreenshot();
            }
        }
        
        function setupClickHandler() {
            const wrapper = document.getElementById('screenshotWrapper');
            const clickArea = document.getElementById('clickArea');
            const screenshot = document.getElementById('screenshot');
            
            wrapper.addEventListener('click', function(e) {
                if (!currentWindow) return;
                
                const rect = screenshot.getBoundingClientRect();
                const x = ((e.clientX - rect.left) / rect.width) * 100;
                const y = ((e.clientY - rect.top) / rect.height) * 100;
                
                // Show click indicator
                clickArea.style.left = (e.clientX - rect.left - 25) + 'px';
                clickArea.style.top = (e.clientY - rect.top - 25) + 'px';
                clickArea.style.display = 'block';
                
                // Send click to server
                fetch('/click', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        window: currentWindow,
                        x_percent: x,
                        y_percent: y
                    })
                });
                
                // Hide click indicator after 500ms
                setTimeout(() => {
                    clickArea.style.display = 'none';
                }, 500);
            });
        }
        
        // Initialize
        loadWindows();
        setupClickHandler();
    </script>
</body>
</html>
        """
    
    def _get_screenshot(self, window_name: str) -> Response:
        """Get screenshot of specified window (0% GPU)."""
        try:
            if not window_name or window_name not in self.registered_windows:
                return Response("Window not found", status=404)
            
            window_info = self.registered_windows[window_name]
            hwnd = window_info['hwnd']
            
            from nodemate.win32_util import capture_hidden_window
            screenshot = capture_hidden_window(hwnd)
            
            if not screenshot:
                return Response("Capture failed", status=500)
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            screenshot.convert("RGB").save(img_buffer, format='JPEG', quality=85)
            img_bytes = img_buffer.getvalue()
            
            return Response(img_bytes, mimetype='image/jpeg')
            
        except Exception as e:
            logger.error(f"Screenshot error for {window_name}: {e}")
            return Response(f"Screenshot failed: {e}", status=500)
    
    def _execute_click(self, data: Dict[str, Any]) -> Response:
        """Execute surgical click using ClientToScreen math."""
        try:
            window_name = data.get('window')
            if not window_name or window_name not in self.registered_windows:
                return Response("Window not found", status=404)
            
            window_info = self.registered_windows[window_name]
            hwnd = window_info['hwnd']
            
            # Client dimensions
            _, _, width, height = win32gui.GetClientRect(hwnd)
            
            # Calculate client coordinates from percentages
            cx = int((data.get('x_percent', 0) / 100) * width)
            cy = int((data.get('y_percent', 0) / 100) * height)
            
            # Use ClientToScreen to mirror the touch precisely
            sx, sy = win32gui.ClientToScreen(hwnd, (cx, cy))
            
            # Execute click using win32api
            import win32api
            import win32con
            
            # Restore cursor to the screen point
            win32api.SetCursorPos((sx, sy))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0)
            
            logger.info(f"Surgical click on {window_name} at Client({cx}, {cy}) -> Screen({sx}, {sy})")
            
            return jsonify({"success": True, "coordinates": {"cx": cx, "cy": cy, "sx": sx, "sy": sy}})
            
        except Exception as e:
            logger.error(f"Click execution failed: {e}")
            return Response(f"Click failed: {e}", status=500)
    
    def _get_available_windows(self) -> list:
        """Get list of available windows."""
        windows = []
        for name, info in self.registered_windows.items():
            windows.append({
                "name": name,
                "title": info.get("title", name),
                "visible": win32gui.IsWindowVisible(info.get("hwnd", 0))
            })
        return windows
    
    def _register_window(self, data: Dict[str, Any]) -> Response:
        """Register a window for monitoring."""
        try:
            window_name = data.get('name')
            hwnd = data.get('hwnd')
            title = data.get('title', window_name)
            
            self.registered_windows[window_name] = {
                'hwnd': hwnd,
                'title': title,
                'registered_at': datetime.now().isoformat()
            }
            
            logger.info(f"Window registered: {window_name}")
            return jsonify({"success": True})
            
        except Exception as e:
            logger.error(f"Window registration failed: {e}")
            return Response(f"Registration failed: {e}", status=500)
    
    def start_server(self) -> None:
        """Start the Flask server in a separate thread."""
        def run_server():
            self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        logger.info(f"Live viewport server started on http://localhost:{self.port}")
    
    def stop_server(self) -> None:
        """Stop the Flask server."""
        # Note: Flask doesn't have clean shutdown, but thread is daemon
        logger.info("Live viewport server stopped")
