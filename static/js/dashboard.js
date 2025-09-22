// Dashboard JavaScript for Raspberry Pi GPIO Monitor
class GPIODashboard {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.chart = null;
        this.currentPinData = {};
        
        this.init();
    }
    
    init() {
        this.initializeSocket();
        this.setupEventListeners();
        this.initializeChart();
        this.setupAutoRefresh();
    }
    
    setupAutoRefresh() {
        // Refresh the entire page every 10 seconds
        setInterval(() => {
            console.log('Auto-refreshing page...');
            window.location.reload();
        }, 10000); // 10 seconds = 10000 milliseconds
    }
    
    initializeSocket() {
        // Initialize Socket.IO connection with optimized settings
        this.socket = io({
            transports: ['websocket', 'polling'],
            upgrade: true,
            rememberUpgrade: true,
            timeout: 5000,
            forceNew: true
        });
        
        // Connection event handlers
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus(false);
        });
        
        // Data event handlers with immediate processing
        this.socket.on('gpio_update', (data) => {
            console.log('GPIO UPDATE RECEIVED:', new Date().toLocaleTimeString(), data);
            // Process immediately without any delays
            this.updateGPIOStatus(data);
        });
        
        this.socket.on('system_update', (data) => {
            console.log('SYSTEM UPDATE RECEIVED:', new Date().toLocaleTimeString());
            this.updateSystemInfo(data);
        });
        
        this.socket.on('pin_history', (data) => {
            this.updateChart(data.pin, data.history);
        });
        
        this.socket.on('counters_reset', () => {
            this.showNotification('Counters have been reset', 'success');
        });
        
        // Handle connection errors
        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.updateConnectionStatus(false);
        });
    }
    
    setupEventListeners() {
        // Reset counters button
        document.getElementById('resetCounters').addEventListener('click', () => {
            if (confirm('Are you sure you want to reset all counters?')) {
                this.socket.emit('reset_counters');
            }
        });
        
        // Chart controls
        document.getElementById('chartPinSelect').addEventListener('change', (e) => {
            if (e.target.value) {
                this.requestPinHistory(e.target.value);
            }
        });
        
        document.getElementById('chartTimeRange').addEventListener('change', (e) => {
            const selectedPin = document.getElementById('chartPinSelect').value;
            if (selectedPin) {
                this.requestPinHistory(selectedPin);
            }
        });
    }
    
    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusElement = document.getElementById('connectionStatus');
        const indicator = statusElement.querySelector('.status-indicator');
        const text = statusElement.querySelector('.status-text');
        
        if (connected) {
            indicator.className = 'status-indicator online';
            text.textContent = 'Connected';
        } else {
            indicator.className = 'status-indicator offline';
            text.textContent = 'Disconnected';
        }
    }
    
    updateGPIOStatus(data) {
        console.log('UPDATING GPIO STATUS:', new Date().toLocaleTimeString());
        this.currentPinData = data;
        this.renderGPIOGridOptimized(data);
        this.renderCountersGrid(data);
        this.updateChartPinSelect(data);
        console.log('GPIO STATUS UPDATE COMPLETE');
    }
    
    renderGPIOGridOptimized(data) {
        const grid = document.getElementById('gpioGrid');
        
        // Sort pins numerically
        const sortedPins = Object.keys(data).sort((a, b) => parseInt(a) - parseInt(b));
        
        // If grid is empty, create all elements
        if (grid.children.length === 0) {
            sortedPins.forEach(pin => {
                const pinData = data[pin];
                const pinElement = this.createPinElement(pin, pinData);
                grid.appendChild(pinElement);
            });
        } else {
            // Update existing elements
            sortedPins.forEach((pin, index) => {
                const pinData = data[pin];
                const existingElement = grid.children[index];
                
                if (existingElement) {
                    this.updatePinElement(existingElement, pin, pinData);
                } else {
                    // Create new element if it doesn't exist
                    const pinElement = this.createPinElement(pin, pinData);
                    grid.appendChild(pinElement);
                }
            });
        }
    }
    
    renderGPIOGrid(data) {
        const grid = document.getElementById('gpioGrid');
        grid.innerHTML = '';
        
        // Sort pins numerically
        const sortedPins = Object.keys(data).sort((a, b) => parseInt(a) - parseInt(b));
        
        sortedPins.forEach(pin => {
            const pinData = data[pin];
            const pinElement = this.createPinElement(pin, pinData);
            grid.appendChild(pinElement);
        });
    }
    
    createPinElement(pin, pinData) {
        const div = document.createElement('div');
        div.className = `gpio-pin state-${pinData.state ? 'high' : 'low'}`;
        div.title = `${pinData.label} - Transitions: ${pinData.transitions}`;
        
        const currentDuration = pinData.current_high_duration;
        const durationText = currentDuration > 0 ? this.formatDuration(currentDuration) : '';
        
        div.innerHTML = `
            <div class="pin-number">GPIO ${pin}</div>
            <div class="pin-label">${pinData.label}</div>
            ${durationText ? `<div class="pin-duration">${durationText}</div>` : ''}
        `;
        
        // Add click handler for chart
        div.addEventListener('click', () => {
            document.getElementById('chartPinSelect').value = pin;
            this.requestPinHistory(pin);
        });
        
        return div;
    }
    
    updatePinElement(element, pin, pinData) {
        // Update class for state change with immediate visual feedback
        const newClassName = `gpio-pin state-${pinData.state ? 'high' : 'low'}`;
        if (element.className !== newClassName) {
            console.log(`PIN ${pin} STATE CHANGE: ${element.className} -> ${newClassName}`);
            element.className = newClassName;
            // Add a quick flash effect for state changes
            element.style.transform = 'scale(1.1)';
            setTimeout(() => {
                element.style.transform = 'scale(1)';
            }, 100);
        }
        
        // Update title
        element.title = `${pinData.label} - Transitions: ${pinData.transitions}`;
        
        // Update content
        const currentDuration = pinData.current_high_duration;
        const durationText = currentDuration > 0 ? this.formatDuration(currentDuration) : '';
        
        element.innerHTML = `
            <div class="pin-number">GPIO ${pin}</div>
            <div class="pin-label">${pinData.label}</div>
            ${durationText ? `<div class="pin-duration">${durationText}</div>` : ''}
        `;
    }
    
    renderCountersGrid(data) {
        const grid = document.getElementById('countersGrid');
        grid.innerHTML = '';
        
        // Sort pins numerically
        const sortedPins = Object.keys(data).sort((a, b) => parseInt(a) - parseInt(b));
        
        sortedPins.forEach(pin => {
            const pinData = data[pin];
            if (pinData.transitions > 0) {
                const counterElement = this.createCounterElement(pin, pinData);
                grid.appendChild(counterElement);
            }
        });
        
        // Show message if no transitions
        if (grid.children.length === 0) {
            const message = document.createElement('div');
            message.style.gridColumn = '1 / -1';
            message.style.textAlign = 'center';
            message.style.color = '#6c757d';
            message.style.fontStyle = 'italic';
            message.textContent = 'No pin transitions recorded yet';
            grid.appendChild(message);
        }
    }
    
    createCounterElement(pin, pinData) {
        const div = document.createElement('div');
        div.className = 'counter-card';
        div.title = `Last transition: ${this.formatTimestamp(pinData.last_transition)}`;
        
        div.innerHTML = `
            <div class="counter-pin">GPIO ${pin}</div>
            <div class="counter-value">${pinData.transitions}</div>
        `;
        
        div.addEventListener('click', () => {
            document.getElementById('chartPinSelect').value = pin;
            this.requestPinHistory(pin);
        });
        
        return div;
    }
    
    updateChartPinSelect(data) {
        const select = document.getElementById('chartPinSelect');
        const currentValue = select.value;
        
        // Clear existing options except the first one
        select.innerHTML = '<option value="">Select a pin to view chart</option>';
        
        // Add options for pins with history
        const sortedPins = Object.keys(data).sort((a, b) => parseInt(a) - parseInt(b));
        sortedPins.forEach(pin => {
            const pinData = data[pin];
            if (pinData.high_duration_history && pinData.high_duration_history.length > 0) {
                const option = document.createElement('option');
                option.value = pin;
                option.textContent = `GPIO ${pin} - ${pinData.label}`;
                select.appendChild(option);
            }
        });
        
        // Restore previous selection if still valid
        if (currentValue && select.querySelector(`option[value="${currentValue}"]`)) {
            select.value = currentValue;
        }
    }
    
    updateSystemInfo(data) {
        // Update CPU usage
        const cpuUsage = document.getElementById('cpuUsage');
        if (data.cpu_usage !== undefined) {
            cpuUsage.textContent = `${data.cpu_usage.toFixed(1)}%`;
        }
        
        // Update CPU temperature
        const cpuTemp = document.getElementById('cpuTemp');
        if (data.cpu_temp !== undefined && data.cpu_temp !== null) {
            cpuTemp.textContent = `${data.cpu_temp.toFixed(1)}°C`;
        } else {
            cpuTemp.textContent = 'N/A';
        }
        
        // Update memory usage
        const memoryUsage = document.getElementById('memoryUsage');
        const memoryProgress = document.getElementById('memoryProgress');
        if (data.memory_percent !== undefined) {
            memoryUsage.textContent = `${data.memory_percent.toFixed(1)}%`;
            memoryProgress.style.width = `${data.memory_percent}%`;
        }
        
        // Update uptime
        const uptime = document.getElementById('uptime');
        if (data.uptime_seconds !== undefined) {
            uptime.textContent = this.formatUptime(data.uptime_seconds);
        }
        
        // Update last update time
        const lastUpdate = document.getElementById('lastUpdate');
        lastUpdate.textContent = new Date().toLocaleTimeString();
    }
    
    requestPinHistory(pin) {
        const timeRange = document.getElementById('chartTimeRange').value;
        this.socket.emit('request_pin_history', {
            pin: parseInt(pin),
            hours: parseInt(timeRange)
        });
    }
    
    initializeChart() {
        const ctx = document.getElementById('durationChart').getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'HIGH Duration (seconds)',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Duration (seconds)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true
                    },
                    title: {
                        display: true,
                        text: 'Pin HIGH State Duration Over Time'
                    }
                }
            }
        });
    }
    
    updateChart(pin, history) {
        if (!this.chart || !history.length) {
            return;
        }
        
        const labels = history.map(entry => new Date(entry.timestamp));
        const data = history.map(entry => entry.duration);
        
        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = data;
        this.chart.data.datasets[0].label = `GPIO ${pin} HIGH Duration (seconds)`;
        this.chart.options.plugins.title.text = `GPIO ${pin} - HIGH State Duration Over Time`;
        
        this.chart.update();
    }
    
    formatDuration(seconds) {
        if (seconds < 1) {
            return `${(seconds * 1000).toFixed(0)}ms`;
        } else if (seconds < 60) {
            return `${seconds.toFixed(1)}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.floor(seconds % 60);
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const remainingMinutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${remainingMinutes}m`;
        }
    }
    
    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        const parts = [];
        if (days > 0) parts.push(`${days}d`);
        if (hours > 0) parts.push(`${hours}h`);
        if (minutes > 0) parts.push(`${minutes}m`);
        
        return parts.join(' ') || '< 1m';
    }
    
    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }
    
    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            color: white;
            z-index: 1000;
            transition: opacity 0.3s ease;
        `;
        
        switch (type) {
            case 'success':
                notification.style.backgroundColor = '#27ae60';
                break;
            case 'error':
                notification.style.backgroundColor = '#e74c3c';
                break;
            default:
                notification.style.backgroundColor = '#3498db';
        }
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new GPIODashboard();
});