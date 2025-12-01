#!/bin/bash
#
# AI Crypto Bot - VPS Setup Script
# ===================================
# Automated setup for Ubuntu 22.04 LTS
#
# Usage: bash setup_vps.sh
#

set -e

echo "============================================================"
echo "   AI CRYPTO BOT - VPS SETUP"
echo "============================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should NOT be run as root${NC}"
   echo "Please run as normal user with sudo privileges"
   exit 1
fi

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Update system
print_info "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y
print_success "System updated"

# Install dependencies
print_info "Installing system dependencies..."
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    nginx \
    certbot \
    python3-certbot-nginx \
    htop \
    ufw
print_success "Dependencies installed"

# Setup firewall
print_info "Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw --force enable
print_success "Firewall configured"

# Create app directory
APP_DIR="/opt/aicryptobot"
print_info "Creating application directory..."
sudo mkdir -p $APP_DIR
sudo chown -R $USER:$USER $APP_DIR
print_success "Directory created: $APP_DIR"

# Clone or copy repository
if [ ! -d "$APP_DIR/.git" ]; then
    print_info "Cloning repository..."
    cd $APP_DIR
    # If using git:
    # git clone https://github.com/yourusername/AiCryptoBot.git .
    echo "Please manually copy your code to $APP_DIR"
    print_success "Repository setup"
fi

cd $APP_DIR

# Create virtual environment
print_info "Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate
print_success "Virtual environment created"

# Install Python packages
print_info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
print_success "Python packages installed"

# Create necessary directories
print_info "Creating directories..."
mkdir -p logs data models config
print_success "Directories created"

# Copy environment file
if [ ! -f ".env" ]; then
    print_info "Creating .env file..."
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}IMPORTANT:${NC} Edit .env file with your API keys:"
    echo "    nano .env"
    echo ""
fi

# Create systemd service
print_info "Creating systemd service..."
sudo tee /etc/systemd/system/aibot.service > /dev/null <<EOF
[Unit]
Description=AI Crypto Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python main.py --enable-web
Restart=always
RestartSec=10
StandardOutput=append:$APP_DIR/logs/bot.log
StandardError=append:$APP_DIR/logs/bot_error.log

[Install]
WantedBy=multi-user.target
EOF
print_success "Systemd service created"

# Create dashboard service
print_info "Creating dashboard service..."
sudo tee /etc/systemd/system/aibot-dashboard.service > /dev/null <<EOF
[Unit]
Description=AI Crypto Bot Dashboard
After=network.target

[Service]
Type=simple
User=$USER
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
print_success "Dashboard service created"

# Reload systemd
print_info "Reloading systemd..."
sudo systemctl daemon-reload
print_success "Systemd reloaded"

# Configure Nginx
print_info "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/aibot > /dev/null <<'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN_HERE;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    # WebSocket support
    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/aibot /etc/nginx/sites-enabled/
sudo nginx -t
print_success "Nginx configured"

# Print next steps
echo ""
echo "============================================================"
echo "   SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit configuration:"
echo "   nano $APP_DIR/.env"
echo "   nano $APP_DIR/config/settings.yaml"
echo ""
echo "2. Train ML models (optional):"
echo "   cd $APP_DIR"
echo "   source venv/bin/activate"
echo "   python scripts/train_ensemble.py"
echo ""
echo "3. Start services:"
echo "   sudo systemctl start aibot-dashboard"
echo "   sudo systemctl enable aibot-dashboard"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status aibot-dashboard"
echo "   tail -f $APP_DIR/logs/dashboard.log"
echo ""
echo "5. Setup SSL (replace YOUR_DOMAIN):"
echo "   sudo certbot --nginx -d YOUR_DOMAIN"
echo ""
echo "6. Access dashboard:"
echo "   http://YOUR_SERVER_IP:5000"
echo ""
echo "============================================================"
echo ""
