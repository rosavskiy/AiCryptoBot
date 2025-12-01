#!/bin/bash
#
# Create systemd service for AI Crypto Bot
# =========================================
#

set -e

APP_DIR="/opt/aicryptobot"

echo "Creating systemd service..."

# Create service file
cat > /etc/systemd/system/aibot-dashboard.service <<EOF
[Unit]
Description=AI Crypto Bot Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python run_dashboard.py
Restart=always
RestartSec=10
StandardOutput=append:$APP_DIR/logs/dashboard.log
StandardError=append:$APP_DIR/logs/dashboard_error.log

[Install]
WantedBy=multi-user.target
EOF

# Create logs directory
mkdir -p $APP_DIR/logs

# Reload systemd
systemctl daemon-reload

echo "✓ Service created successfully!"
echo ""
echo "To start the service:"
echo "  systemctl start aibot-dashboard"
echo ""
echo "To enable auto-start:"
echo "  systemctl enable aibot-dashboard"
echo ""
echo "To check status:"
echo "  systemctl status aibot-dashboard"
echo ""
