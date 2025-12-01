#!/bin/bash
# Quick deployment script for Netherlands VPS

echo "🇳🇱 Deploying AI Crypto Bot to Netherlands VPS"
echo "=============================================="

# Update system
echo "📦 Updating system..."
apt update && apt upgrade -y

# Install Python 3.11+
echo "🐍 Installing Python..."
apt install -y python3 python3-pip python3-venv git nginx

# Create bot directory
echo "📁 Creating directory..."
cd /opt
git clone https://github.com/rosavskiy/AiCryptoBot.git aicryptobot
cd aicryptobot

# Create virtual environment
echo "🔧 Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
echo "⚙️ Configuring..."
cp .env.example .env

# Create necessary directories
mkdir -p logs models data

# Setup systemd service
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/aibot-dashboard.service << 'EOF'
[Unit]
Description=AI Crypto Bot Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aicryptobot
Environment="PATH=/opt/aicryptobot/venv/bin"
ExecStart=/opt/aicryptobot/venv/bin/python run_dashboard.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Setup nginx
echo "🌐 Configuring nginx..."
cat > /etc/nginx/sites-available/aibot << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/aibot /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Enable and start service
systemctl daemon-reload
systemctl enable aibot-dashboard
systemctl start aibot-dashboard

echo ""
echo "✅ Deployment completed!"
echo ""
echo "📝 Next steps:"
echo "   1. Edit /opt/aicryptobot/.env with your API keys"
echo "   2. nano /opt/aicryptobot/.env"
echo "   3. Add: BINANCE_TESTNET_API_KEY=your_key"
echo "   4. Add: BINANCE_TESTNET_API_SECRET=your_secret"
echo "   5. systemctl restart aibot-dashboard"
echo ""
echo "🌐 Dashboard will be available at: http://YOUR_IP"
echo ""
