#!/bin/bash
#
# AI Crypto Bot - Deployment Script
# ==================================
# Автоматическое обновление бота на VPS из GitHub
#
# Usage: bash deploy_from_git.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   AI CRYPTO BOT - DEPLOY FROM GITHUB${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Configuration
APP_DIR="/opt/aicryptobot"
REPO_URL="https://github.com/rosavskiy/AiCryptoBot.git"
BRANCH="main"

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

# Note: Can run as root on VPS

# Navigate to app directory
if [ ! -d "$APP_DIR" ]; then
    print_error "Directory $APP_DIR not found. Run setup_vps.sh first."
    exit 1
fi

cd $APP_DIR
print_info "Working directory: $APP_DIR"
echo ""

# Step 1: Stop service
print_info "Stopping aibot-dashboard service..."
systemctl stop aibot-dashboard 2>/dev/null || true
print_success "Service stopped"

# Step 2: Backup current .env (if exists)
if [ -f ".env" ]; then
    print_info "Backing up .env file..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    print_success ".env backed up"
fi

# Step 3: Pull latest code from GitHub
print_info "Pulling latest code from GitHub..."

if [ -d ".git" ]; then
    # Repository already cloned, just pull
    git fetch origin
    git reset --hard origin/$BRANCH
    print_success "Code updated (git pull)"
else
    # First time - clone repository
    print_info "Cloning repository..."
    cd ..
    rm -rf $APP_DIR
    git clone -b $BRANCH $REPO_URL $APP_DIR
    cd $APP_DIR
    print_success "Repository cloned"
fi

# Step 4: Restore .env
if [ -f ".env.backup."* ]; then
    LATEST_BACKUP=$(ls -t .env.backup.* | head -1)
    print_info "Restoring .env from backup..."
    cp $LATEST_BACKUP .env
    print_success ".env restored"
elif [ ! -f ".env" ]; then
    print_info "Creating .env from template..."
    cp .env.example .env
    echo ""
    print_error "IMPORTANT: Edit .env file with your API keys:"
    echo "    nano .env"
    echo ""
fi

# Step 5: Create necessary directories
print_info "Creating directories..."
mkdir -p logs data models config
print_success "Directories created"

# Step 6: Update Python dependencies
print_info "Updating Python dependencies..."
source venv/bin/activate 2>/dev/null || python3.11 -m venv venv && source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
print_success "Dependencies updated"

# Step 7: Check configuration
print_info "Checking configuration..."
if ! grep -q "BYBIT_API_KEY=your_api_key_here" .env; then
    print_success "API keys configured"
else
    print_error "WARNING: API keys not configured in .env"
    echo "    Edit: nano .env"
fi

# Step 8: Start service
print_info "Starting aibot-dashboard service..."
systemctl start aibot-dashboard
sleep 2
print_success "Service started"

# Step 9: Check status
print_info "Checking service status..."
if systemctl is-active --quiet aibot-dashboard; then
    print_success "Service is running"
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}   DEPLOYMENT SUCCESSFUL! 🎉${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo "Dashboard URL: http://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    echo "Useful commands:"
    echo "  Status:  systemctl status aibot-dashboard"
    echo "  Logs:    tail -f $APP_DIR/logs/dashboard.log"
    echo "  Restart: systemctl restart aibot-dashboard"
    echo ""
else
    print_error "Service failed to start"
    echo ""
    echo "Check logs:"
    echo "  journalctl -u aibot-dashboard -n 50"
    echo "  tail -f $APP_DIR/logs/dashboard.log"
    exit 1
fi

# Step 10: Show recent logs
echo "Recent logs:"
echo "-----------------------------------------------------------"
tail -n 10 $APP_DIR/logs/dashboard.log 2>/dev/null || echo "No logs yet"
echo "-----------------------------------------------------------"
echo ""
