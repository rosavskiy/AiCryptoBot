#!/bin/bash

# Скрипт для обновления бота на VPS

set -e  # Exit on error

echo "=== Updating AiCryptoBot on VPS ==="

# Pull latest code
echo "Pulling latest code..."
cd ~/AiCryptoBot
git pull origin main

# Restart service
echo "Restarting aibot-dashboard service..."
sudo systemctl restart aibot-dashboard

# Show status
echo "Service status:"
sudo systemctl status aibot-dashboard --no-pager

# Show last 30 lines of logs
echo ""
echo "Recent logs:"
sudo journalctl -u aibot-dashboard -n 30 --no-pager

echo ""
echo "=== Update complete ==="
echo "Dashboard: http://144.124.254.110:5000"
