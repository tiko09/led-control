#!/bin/bash

# LED Control Service Installation Script
# This script creates and enables a systemd service for LED Control

echo "Installing LED Control as systemd service..."

# Create the service file
sudo tee /etc/systemd/system/ledcontrol.service > /dev/null <<EOF
[Unit]
Description=LED Control Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$(pwd)
ExecStart=$(which python3) -m ledcontrol.app --led_count 144 --led_pixel_order GRBW
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF

echo "Service file created at /etc/systemd/system/ledcontrol.service"

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service to start on boot
echo "Enabling service to start on boot..."
sudo systemctl enable ledcontrol

# Start the service
echo "Starting LED Control service..."
sudo systemctl start ledcontrol

# Wait a moment for service to start
sleep 2

# Show status
echo ""
echo "======================================"
echo "Service Status:"
echo "======================================"
sudo systemctl status ledcontrol --no-pager

echo ""
echo "======================================"
echo "Installation complete!"
echo "======================================"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status ledcontrol   - Check service status"
echo "  sudo systemctl stop ledcontrol     - Stop service"
echo "  sudo systemctl start ledcontrol    - Start service"
echo "  sudo systemctl restart ledcontrol  - Restart service"
echo "  sudo journalctl -u ledcontrol -f   - View logs (live)"
echo "  sudo systemctl disable ledcontrol  - Disable autostart"
echo ""
