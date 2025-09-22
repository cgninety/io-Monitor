from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
import json
import logging
from datetime import datetime

from gpio_monitor import GPIOMonitor
from system_info import SystemInfoCollector

class WebServer:
    """
    Flask web server with SocketIO for real-time GPIO monitoring dashboard.
    """
    
    def __init__(self, host='0.0.0.0', port=5000, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        
        # Setup logging first
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize Flask app and SocketIO
        self.app = Flask(__name__, 
                        template_folder='../templates',
                        static_folder='../static')
        self.app.config['SECRET_KEY'] = 'gpio_monitor_secret_key_2023'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", 
                               async_mode='eventlet')
        
        # Initialize monitoring services
        self.gpio_monitor = GPIOMonitor()
        self.system_info = SystemInfoCollector()
        
        # Set up immediate GPIO state change callback
        self.logger.info("Setting up GPIO state change callback...")
        self.gpio_monitor.set_state_change_callback(self._on_gpio_state_change)
        self.logger.info("GPIO callback set successfully")
        
        # Background update thread
        self.update_thread = None
        self.update_running = False
        
        # Setup routes and socket handlers
        self._setup_routes()
        self._setup_socket_handlers()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template('dashboard.html')
        
        @self.app.route('/api/gpio/status')
        def gpio_status():
            """Get current GPIO pin status."""
            return jsonify(self.gpio_monitor.get_pin_status())
        
        @self.app.route('/api/gpio/transitions')
        def gpio_transitions():
            """Get GPIO transition counts."""
            return jsonify(self.gpio_monitor.get_transition_summary())
        
        @self.app.route('/api/gpio/history/<int:pin>')
        def gpio_history(pin):
            """Get GPIO pin history."""
            hours = request.args.get('hours', default=1, type=int)
            history = self.gpio_monitor.get_pin_history(pin, hours)
            return jsonify(history)
        
        @self.app.route('/api/gpio/reset', methods=['POST'])
        def reset_counters():
            """Reset all GPIO counters."""
            self.gpio_monitor.reset_counters()
            return jsonify({'status': 'success', 'message': 'Counters reset'})
        
        @self.app.route('/api/system/info')
        def system_info():
            """Get comprehensive system information."""
            return jsonify(self.system_info.get_system_summary())
        
        @self.app.route('/api/system/lightweight')
        def system_lightweight():
            """Get lightweight system information."""
            return jsonify(self.system_info.get_lightweight_summary())
        
        @self.app.route('/api/config')
        def get_config():
            """Get current configuration."""
            return jsonify({
                'pins_monitored': self.gpio_monitor.pins_to_monitor,
                'update_interval': self.gpio_monitor.update_interval,
                'pin_labels': self.gpio_monitor.pin_labels
            })
        
        @self.app.route('/api/config', methods=['POST'])
        def update_config():
            """Update configuration."""
            try:
                config_data = request.get_json()
                
                # Update pin labels if provided
                if 'pin_labels' in config_data:
                    self.gpio_monitor.pin_labels.update(config_data['pin_labels'])
                
                # Note: Changing pins_to_monitor or update_interval requires restart
                return jsonify({'status': 'success', 'message': 'Configuration updated'})
            
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 400
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({'error': 'Not found'}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({'error': 'Internal server error'}), 500
    
    def _setup_socket_handlers(self):
        """Setup SocketIO event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            self.logger.info(f"Client connected: {request.sid}")
            
            # Send initial data
            emit('gpio_update', self.gpio_monitor.get_pin_status())
            emit('system_update', self.system_info.get_lightweight_summary())
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            self.logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('request_gpio_update')
        def handle_gpio_update_request():
            """Handle request for GPIO update."""
            emit('gpio_update', self.gpio_monitor.get_pin_status())
        
        @self.socketio.on('request_system_update')
        def handle_system_update_request():
            """Handle request for system update."""
            emit('system_update', self.system_info.get_lightweight_summary())
        
        @self.socketio.on('request_pin_history')
        def handle_pin_history_request(data):
            """Handle request for pin history."""
            pin = data.get('pin')
            hours = data.get('hours', 1)
            if pin is not None:
                history = self.gpio_monitor.get_pin_history(int(pin), hours)
                emit('pin_history', {'pin': pin, 'history': history})
        
        @self.socketio.on('reset_counters')
        def handle_reset_counters():
            """Handle counter reset request."""
            self.gpio_monitor.reset_counters()
            self.socketio.emit('counters_reset', namespace='/')
            self.socketio.emit('gpio_update', self.gpio_monitor.get_pin_status(), namespace='/')
    
    def _on_gpio_state_change(self, pin, new_state, old_state):
        """Callback function called immediately when a GPIO pin state changes."""
        try:
            self.logger.info(f"CALLBACK RECEIVED: Pin {pin} changed {old_state} -> {new_state}")
            
            # Send immediate update for the specific pin
            gpio_data = self.gpio_monitor.get_pin_status()
            
            # Use the server manager to emit to all clients
            self.socketio.server.emit('gpio_update', gpio_data, namespace='/')
            
            self.logger.info(f"SOCKETIO EMIT SENT: Immediate update for pin {pin}")
            
        except Exception as e:
            self.logger.error(f"Error sending immediate GPIO update: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _background_update_loop(self):
        """Background thread for sending periodic updates to connected clients."""
        gpio_update_counter = 0
        system_update_counter = 0
        
        self.logger.info("Background update loop started")
        
        while self.update_running:
            try:
                # Send GPIO updates every 100ms as backup (immediate updates handle real-time changes)
                if gpio_update_counter >= 1:  # 1 * 0.1s = 100ms
                    gpio_data = self.gpio_monitor.get_pin_status()
                    self.socketio.server.emit('gpio_update', gpio_data, namespace='/')
                    self.logger.debug("Background GPIO update sent")
                    gpio_update_counter = 0
                
                # Send system updates every 1 second
                if system_update_counter >= 10:  # 10 * 0.1s = 1s
                    system_data = self.system_info.get_lightweight_summary()
                    self.socketio.server.emit('system_update', system_data, namespace='/')
                    self.logger.debug("Background system update sent")
                    system_update_counter = 0
                
                gpio_update_counter += 1
                system_update_counter += 1
                
                time.sleep(0.1)  # 100ms update interval
                
            except Exception as e:
                self.logger.error(f"Error in background update loop: {e}")
                time.sleep(1)  # Wait before retrying
    
    def start_background_updates(self):
        """Start the background update thread."""
        if not self.update_running:
            self.update_running = True
            self.update_thread = threading.Thread(target=self._background_update_loop, daemon=True)
            self.update_thread.start()
            self.logger.info("Background updates started")
    
    def stop_background_updates(self):
        """Stop the background update thread."""
        self.update_running = False
        if self.update_thread:
            self.update_thread.join()
        self.logger.info("Background updates stopped")
    
    def start_monitoring(self):
        """Start GPIO monitoring."""
        self.gpio_monitor.start_monitoring()
        self.start_background_updates()
    
    def stop_monitoring(self):
        """Stop GPIO monitoring."""
        self.stop_background_updates()
        self.gpio_monitor.stop_monitoring()
    
    def run(self):
        """Run the web server."""
        try:
            self.start_monitoring()
            self.logger.info(f"Starting web server on {self.host}:{self.port}")
            self.socketio.run(self.app, 
                            host=self.host, 
                            port=self.port, 
                            debug=self.debug,
                            allow_unsafe_werkzeug=True)
        except KeyboardInterrupt:
            self.logger.info("Shutting down web server...")
        finally:
            self.stop_monitoring()

if __name__ == '__main__':
    server = WebServer(debug=True)
    server.run()