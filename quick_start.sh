#!/bin/bash

# Quick start script for testing without installation
# Activates virtual environment and starts the monitor

set -e

echo "Starting Raspberry Pi GPIO Monitor..."

# Check if virtual environment exists
if [ ! -d "gpio_monitor_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv gpio_monitor_env
    source gpio_monitor_env/bin/activate
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source gpio_monitor_env/bin/activate
fi

# Start the monitor
echo "Starting GPIO monitor on http://localhost:5000"
echo "Press Ctrl+C to stop"
python src/main.py --debug "$@"