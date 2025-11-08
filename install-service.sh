#!/bin/bash
# LED Control Service Installation Script

set -e

echo "=========================================="
echo "LED Control Service Installation"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Detect installation directory
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installation directory: $INSTALL_DIR"

# Find ledcontrol executable
LEDCONTROL_PATH=$(which ledcontrol 2>/dev/null || echo "")
if [ -z "$LEDCONTROL_PATH" ]; then
    echo "Warning: 'ledcontrol' command not found, trying python module..."
    LEDCONTROL_PATH="$(which python3) -m ledcontrol.app"
fi
echo "LED Control command: $LEDCONTROL_PATH"

# Create service file with correct paths
SERVICE_FILE="/etc/systemd/system/ledcontrol.service"
echo ""
echo "Creating systemd service file..."

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=LED Control Server - WS2812B/SK6812 RGBW LED Controller
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$LEDCONTROL_PATH --led_count 144 --led_pixel_order GRBW
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "Service file created: $SERVICE_FILE"

# Reload systemd
echo ""
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "Enabling service to start on boot..."
systemctl enable ledcontrol.service

# Show status
echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Service commands:"
echo "  Start:   sudo systemctl start ledcontrol"
echo "  Stop:    sudo systemctl stop ledcontrol"
echo "  Restart: sudo systemctl restart ledcontrol"
echo "  Status:  sudo systemctl status ledcontrol"
echo "  Logs:    sudo journalctl -u ledcontrol -f"
echo ""
echo "The service will start automatically on boot."
echo ""
read -p "Do you want to start the service now? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    echo "Starting service..."
    systemctl start ledcontrol
    echo ""
    echo "Waiting for service to start..."
    sleep 2
    systemctl status ledcontrol --no-pager
    echo ""
    echo "Service started! Check logs with: sudo journalctl -u ledcontrol -f"
else
    echo "Service not started. Start manually with: sudo systemctl start ledcontrol"
fi
