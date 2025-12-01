#!/bin/bash
#
# Quick Deploy Script
# ===================
# Quick deployment to VPS using rsync
#

set -e

# Configuration
VPS_USER="your_user"
VPS_HOST="your_vps_ip"
VPS_PATH="/opt/aicryptobot"
EXCLUDE_FILE=".deployignore"

echo "============================================================"
echo "   AI CRYPTO BOT - QUICK DEPLOY"
echo "============================================================"
echo ""

# Check if .deployignore exists
if [ ! -f "$EXCLUDE_FILE" ]; then
    echo "Creating .deployignore..."
    cat > $EXCLUDE_FILE <<EOF
.git/
.vscode/
.idea/
__pycache__/
*.pyc
venv/
logs/
data/
models/
.env
.env.local
*.log
.DS_Store
EOF
fi

echo "Deploying to $VPS_USER@$VPS_HOST:$VPS_PATH"
echo ""

# Sync files
rsync -avz --progress \
    --exclude-from="$EXCLUDE_FILE" \
    --delete \
    ./ $VPS_USER@$VPS_HOST:$VPS_PATH/

echo ""
echo "Files synced successfully!"
echo ""

# Restart services on VPS
echo "Restarting services..."
ssh $VPS_USER@$VPS_HOST <<'EOF'
    cd /opt/aicryptobot
    sudo systemctl restart aibot-dashboard
    sudo systemctl status aibot-dashboard --no-pager
EOF

echo ""
echo "============================================================"
echo "   DEPLOYMENT COMPLETE!"
echo "============================================================"
echo ""
echo "Dashboard: http://$VPS_HOST:5000"
echo ""
