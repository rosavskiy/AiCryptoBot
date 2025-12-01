# 🚀 VPS Deployment Guide

## Recommended VPS Providers

1. **DigitalOcean** - $6/month
2. **Vultr** - $5/month
3. **AWS EC2** - t3.micro
4. **Linode** - $5/month

## Requirements

- **OS**: Ubuntu 22.04 LTS
- **RAM**: 1GB minimum (2GB recommended)
- **CPU**: 1 vCPU
- **Storage**: 25GB SSD

---

## Step-by-Step Setup

### 1. Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.9 python3-pip git sqlite3

# Create bot user
sudo adduser --disabled-password --gecos "" botuser
sudo usermod -aG sudo botuser
```

### 2. Clone Repository

```bash
sudo su - botuser
git clone https://github.com/rosavskiy/AiCryptoBot.git
cd AiCryptoBot
```

### 3. Setup Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Bot

```bash
# Copy environment template
cp .env.example .env

# Edit with your keys
nano .env
```

### 5. Create Systemd Service

Create `/etc/systemd/system/crypto-bot.service`:

```ini
[Unit]
Description=AI Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/AiCryptoBot
Environment="PATH=/home/botuser/AiCryptoBot/venv/bin"
ExecStart=/home/botuser/AiCryptoBot/venv/bin/python run_bot.py
Restart=always
RestartSec=10
StandardOutput=append:/home/botuser/AiCryptoBot/logs/bot.log
StandardError=append:/home/botuser/AiCryptoBot/logs/error.log

[Install]
WantedBy=multi-user.target
```

### 6. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable crypto-bot
sudo systemctl start crypto-bot
sudo systemctl status crypto-bot
```

---

## Monitoring

### View logs in real-time

```bash
tail -f ~/AiCryptoBot/logs/bot.log
```

### Check service status

```bash
systemctl status crypto-bot
```

### Restart service

```bash
sudo systemctl restart crypto-bot
```

---

## Security Best Practices

1. **Firewall Setup**:
```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

2. **SSH Key Authentication**:
```bash
# On local machine
ssh-copy-id botuser@your-server-ip

# On server, disable password auth
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd
```

3. **Auto-updates**:
```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

4. **Fail2Ban** (optional):
```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

---

## Backup Strategy

### Automated Daily Backup

Create `/home/botuser/backup.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
cd /home/botuser/AiCryptoBot
tar -czf backups/backup_$DATE.tar.gz data/ logs/ models/
find backups/ -name "*.tar.gz" -mtime +7 -delete
```

Add to crontab:
```bash
crontab -e
# Add: 0 2 * * * /home/botuser/backup.sh
```

---

## Updating Bot

```bash
cd ~/AiCryptoBot
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crypto-bot
```

---

## Troubleshooting

### Bot not starting

```bash
# Check logs
journalctl -u crypto-bot -n 50

# Test manually
cd ~/AiCryptoBot
source venv/bin/activate
python run_bot.py
```

### High memory usage

```bash
# Monitor resources
htop

# Check bot memory
ps aux | grep python
```

### Database locked

```bash
cd ~/AiCryptoBot/data
sqlite3 trading.db "PRAGMA integrity_check;"
```

---

## Performance Optimization

### 1. Swap File (for low RAM VPS)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2. Logrotate

Create `/etc/logrotate.d/crypto-bot`:

```
/home/botuser/AiCryptoBot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 botuser botuser
}
```

---

## Cost Estimation

| Provider | Plan | Price/mo |
|----------|------|----------|
| DigitalOcean | 1GB RAM | $6 |
| Vultr | 1GB RAM | $5 |
| AWS EC2 | t3.micro | ~$8 |
| Linode | Nanode 1GB | $5 |

**Total monthly cost**: $5-10
