#!/bin/bash

# Raspberry Pi GPIO Monitor Installation Script
# This script installs and configures the GPIO monitoring system

set -e

echo "=================================================="
echo "Raspberry Pi GPIO Monitor Installation Script"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as a regular user."
   exit 1
fi

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    print_warning "This doesn't appear to be a Raspberry Pi. Some features may not work correctly."
fi

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip if not already installed
print_status "Installing Python dependencies..."
sudo apt install -y python3 python3-pip python3-venv git

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv gpio_monitor_env
source gpio_monitor_env/bin/activate

# Install Python packages
print_status "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create systemd service file
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/gpio-monitor.service > /dev/null << EOF
[Unit]
Description=Raspberry Pi GPIO Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/gpio_monitor_env/bin
ExecStart=$(pwd)/gpio_monitor_env/bin/python src/main.py --host 0.0.0.0 --port 5000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
print_status "Creating log directory..."
mkdir -p logs
chmod 755 logs

# Set proper permissions
print_status "Setting file permissions..."
chmod +x src/main.py

# Reload systemd and enable service
print_status "Enabling GPIO monitor service..."
sudo systemctl daemon-reload
sudo systemctl enable gpio-monitor.service

# Create startup script
print_status "Creating convenience scripts..."
cat > start_monitor.sh << 'EOF'
#!/bin/bash
source gpio_monitor_env/bin/activate
python src/main.py "$@"
EOF
chmod +x start_monitor.sh

cat > stop_monitor.sh << 'EOF'
#!/bin/bash
sudo systemctl stop gpio-monitor.service
EOF
chmod +x stop_monitor.sh

cat > status_monitor.sh << 'EOF'
#!/bin/bash
sudo systemctl status gpio-monitor.service
EOF
chmod +x status_monitor.sh

# Create configuration backup
print_status "Creating configuration backup..."
cp config/gpio_config.json config/gpio_config.json.backup

print_success "Installation completed successfully!"
echo ""
echo "=================================================="
echo "Usage Instructions:"
echo "=================================================="
echo ""
echo "1. Start the service:"
echo "   sudo systemctl start gpio-monitor.service"
echo ""
echo "2. Stop the service:"
echo "   sudo systemctl stop gpio-monitor.service"
echo ""
echo "3. Check service status:"
echo "   sudo systemctl status gpio-monitor.service"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u gpio-monitor.service -f"
echo ""
echo "5. Manual start (for testing):"
echo "   ./start_monitor.sh"
echo ""
echo "6. Access the web dashboard:"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo "   or"
echo "   http://localhost:5000"
echo ""
echo "Configuration file: config/gpio_config.json"
echo ""
print_warning "Remember to configure GPIO pins in config/gpio_config.json before starting!"
echo ""
echo "Would you like to start the service now? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    print_status "Starting GPIO monitor service..."
    sudo systemctl start gpio-monitor.service
    sleep 2
    if sudo systemctl is-active --quiet gpio-monitor.service; then
        print_success "Service started successfully!"
        print_status "Access the dashboard at: http://$(hostname -I | awk '{print $1}'):5000"
    else
        print_error "Failed to start service. Check logs with: sudo journalctl -u gpio-monitor.service"
    fi
fi