#!/bin/bash
#
# AI Crypto Bot - VPS Setup Script (ROOT VERSION)
# =================================================
# Simplified setup for root user
#
# Usage: bash setup_vps_root.sh
#

set -e

echo "============================================================"
echo "   AI CRYPTO BOT - VPS SETUP (ROOT)"
echo "============================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Update system
print_info "Updating system packages..."
apt-get update
apt-get upgrade -y
print_success "System updated"

# Add Python PPA
print_info "Adding Python PPA..."
add-apt-repository ppa:deadsnakes/ppa -y
apt-get update
print_success "PPA added"

# Install dependencies
print_info "Installing system dependencies..."
apt-get install -y \
    software-properties-common \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
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
    ufw \
    unzip
print_success "Dependencies installed"

# Setup firewall
print_info "Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw allow 5000/tcp
ufw --force enable
print_success "Firewall configured"

# Create app directory
APP_DIR="/opt/aicryptobot"
print_info "Creating application directory..."
mkdir -p $APP_DIR
print_success "Directory created: $APP_DIR"

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}   SETUP COMPLETE!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Clone repository:"
echo "   cd $APP_DIR"
echo "   git clone https://github.com/rosavskiy/AiCryptoBot.git ."
echo ""
echo "2. Setup Python environment:"
echo "   cd $APP_DIR"
echo "   python3.11 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo ""
echo "3. Configure .env:"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "4. Create systemd service:"
echo "   bash create_service.sh"
echo ""
echo "5. Start bot:"
echo "   systemctl start aibot-dashboard"
echo "   systemctl enable aibot-dashboard"
echo ""
echo "============================================================"
echo ""
