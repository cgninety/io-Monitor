# GPIO Monitor

A comprehensive GPIO monitoring system for Raspberry Pi Zero 2W with a real-time web dashboard.

## Features

- **Real-time GPIO monitoring**: Track the state of all GPIO pins
- **Transition counting**: Count state changes for each pin
- **Duration tracking**: Monitor how long pins stay in HIGH state
- **System information**: Display Pi uptime, CPU speed, memory usage, and temperature
- **Live web dashboard**: Real-time updates without page refresh
- **Responsive design**: Works on desktop and mobile devices

## Hardware Requirements

- Raspberry Pi Zero 2W
- MicroSD card (8GB+)
- GPIO connections (optional for testing)

## Installation

1. **Clone or copy the project to your Raspberry Pi:**
   ```bash
   git clone https://github.com/cgninety/io-Monitor
   cd rpi-gpio-monitor
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure GPIO pins:**
   Edit `config/gpio_config.json` to specify which pins to monitor

4. **Run the application:**
   ```bash
   python3 src/main.py
   ```

5. **Access the dashboard:**
   Open your browser and navigate to `http://[pi-ip-address]:5000`

## Configuration

Edit `config/gpio_config.json` to customize:
- Which GPIO pins to monitor
- Update intervals
- Dashboard refresh rates
- Pin labels and descriptions

## Usage

The web dashboard provides:
- **GPIO Status Grid**: Visual representation of all monitored pins
- **Transition Counters**: Count of state changes per pin
- **Duration Charts**: Line graphs showing HIGH state duration over time
- **System Info Panel**: Real-time system statistics

## Architecture

- `src/gpio_monitor.py`: GPIO monitoring service
- `src/system_info.py`: System information collector
- `src/web_server.py`: Flask web server with SocketIO
- `src/main.py`: Main application entry point
- `templates/`: HTML templates
- `static/`: CSS, JavaScript, and assets
- `config/`: Configuration files

## License

MIT License