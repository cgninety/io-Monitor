import time
import threading
import json
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("RPi.GPIO not available - running in simulation mode")

class GPIOMonitor:
    """
    GPIO monitoring service that tracks pin states, transitions, and timing data.
    """
    
    def __init__(self, config_file='config/gpio_config.json'):
        self.config = self._load_config(config_file)
        self.pins_to_monitor = self.config.get('pins_to_monitor', list(range(2, 28)))
        self.update_interval = self.config.get('update_interval', 0.1)
        self.history_duration = self.config.get('history_duration_minutes', 60)
        
        # Pin state tracking
        self.pin_states = {}
        self.pin_labels = self.config.get('pin_labels', {})
        self.transition_counts = defaultdict(int)
        self.last_transition_time = {}
        self.high_duration_history = defaultdict(lambda: deque(maxlen=1000))
        self.current_high_start = {}
        
        # Thread control
        self.monitoring = False
        self.monitor_thread = None
        
        # Setup GPIO if available
        if GPIO_AVAILABLE:
            self._setup_gpio()
        else:
            self._setup_simulation()
            
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_file):
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default configuration
            return {
                'pins_to_monitor': list(range(2, 28)),
                'update_interval': 0.1,
                'history_duration_minutes': 60,
                'pin_labels': {}
            }
    
    def _setup_gpio(self):
        """Initialize GPIO pins for monitoring."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        for pin in self.pins_to_monitor:
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                self.pin_states[pin] = GPIO.input(pin)
                self.last_transition_time[pin] = datetime.now()
            except Exception as e:
                self.logger.warning(f"Failed to setup GPIO pin {pin}: {e}")
                if pin in self.pins_to_monitor:
                    self.pins_to_monitor.remove(pin)
    
    def _setup_simulation(self):
        """Setup simulation mode for testing without GPIO."""
        import random
        for pin in self.pins_to_monitor:
            self.pin_states[pin] = random.choice([0, 1])
            self.last_transition_time[pin] = datetime.now()
    
    def start_monitoring(self):
        """Start the GPIO monitoring thread."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("GPIO monitoring started")
    
    def stop_monitoring(self):
        """Stop the GPIO monitoring thread."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        
        self.logger.info("GPIO monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            current_time = datetime.now()
            
            for pin in self.pins_to_monitor:
                old_state = self.pin_states.get(pin, 0)
                
                if GPIO_AVAILABLE:
                    try:
                        new_state = GPIO.input(pin)
                    except Exception as e:
                        self.logger.error(f"Error reading pin {pin}: {e}")
                        continue
                else:
                    # Simulation mode - occasionally flip states
                    import random
                    if random.random() < 0.01:  # 1% chance to flip
                        new_state = 1 - old_state
                    else:
                        new_state = old_state
                
                # Check for state transition
                if new_state != old_state:
                    self.pin_states[pin] = new_state
                    self.transition_counts[pin] += 1
                    self.last_transition_time[pin] = current_time
                    
                    # Handle HIGH state duration tracking
                    if old_state == 1 and new_state == 0:  # Falling edge
                        if pin in self.current_high_start:
                            duration = (current_time - self.current_high_start[pin]).total_seconds()
                            self.high_duration_history[pin].append({
                                'timestamp': current_time.isoformat(),
                                'duration': duration
                            })
                            del self.current_high_start[pin]
                    
                    elif old_state == 0 and new_state == 1:  # Rising edge
                        self.current_high_start[pin] = current_time
                    
                    self.logger.debug(f"Pin {pin} changed from {old_state} to {new_state}")
            
            time.sleep(self.update_interval)
    
    def get_pin_status(self):
        """Get current status of all monitored pins."""
        current_time = datetime.now()
        status = {}
        
        for pin in self.pins_to_monitor:
            current_high_duration = 0
            if pin in self.current_high_start and self.pin_states.get(pin) == 1:
                current_high_duration = (current_time - self.current_high_start[pin]).total_seconds()
            
            status[str(pin)] = {
                'state': self.pin_states.get(pin, 0),
                'label': self.pin_labels.get(str(pin), f"GPIO {pin}"),
                'transitions': self.transition_counts[pin],
                'last_transition': self.last_transition_time.get(pin, current_time).isoformat(),
                'current_high_duration': current_high_duration,
                'high_duration_history': list(self.high_duration_history[pin])[-50:]  # Last 50 entries
            }
        
        return status
    
    def get_transition_summary(self):
        """Get transition count summary for all pins."""
        return dict(self.transition_counts)
    
    def reset_counters(self):
        """Reset all transition counters."""
        self.transition_counts.clear()
        for pin in self.pins_to_monitor:
            self.high_duration_history[pin].clear()
        self.logger.info("All counters reset")
    
    def get_pin_history(self, pin, hours=1):
        """Get historical data for a specific pin."""
        if pin not in self.high_duration_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        history = []
        
        for entry in self.high_duration_history[pin]:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time >= cutoff_time:
                history.append(entry)
        
        return history