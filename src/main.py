#!/usr/bin/env python3
"""
Main entry point for the Raspberry Pi GPIO Monitor.

This application monitors GPIO pins on a Raspberry Pi and provides
a real-time web dashboard for viewing pin states, transition counts,
and system information.
"""

import sys
import os
import argparse
import signal
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from web_server import WebServer

def setup_logging(log_level='INFO'):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('gpio_monitor.log')
        ]
    )

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logging.info("Received shutdown signal, stopping...")
    sys.exit(0)

def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description='Raspberry Pi GPIO Monitor')
    parser.add_argument('--host', default='0.0.0.0', 
                       help='Host to bind the web server to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to bind the web server to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Set logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting Raspberry Pi GPIO Monitor")
    logger.info(f"Web interface will be available at http://{args.host}:{args.port}")
    
    try:
        # Create and start the web server
        server = WebServer(host=args.host, port=args.port, debug=args.debug)
        server.run()
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
    
    logger.info("GPIO Monitor stopped")

if __name__ == '__main__':
    main()