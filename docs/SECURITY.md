# ========================================
# SECURITY BEST PRACTICES
# ========================================

## 🔐 API Keys Security

### Critical Rules:
1. **Never commit `.env` to Git**
   - Already in `.gitignore`
   - Double-check before pushing

2. **Separate Testnet and Mainnet Keys**
   - Use different API keys
   - Never mix environments

3. **Limit API Permissions**
   - ✅ Enable: Trading, Read Position
   - ❌ Disable: Withdraw, Transfer
   - Set IP whitelist on exchange

4. **Rotate Keys Regularly**
   - Change API keys monthly
   - Immediately after any breach

---

## 🛡️ Server Security

### 1. SSH Hardening

```bash
# Disable root login
sudo nano /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no

# Use SSH keys only
ssh-copy-id user@server
```

### 2. Firewall Setup

```bash
# Allow only SSH
sudo ufw allow 22/tcp
sudo ufw enable
sudo ufw status
```

### 3. Fail2Ban

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

---

## 💾 Data Protection

### 1. Database Encryption (Optional)

```bash
# Encrypt SQLite database
sqlcipher data/trading.db
```

### 2. Backup Strategy

```bash
# Daily encrypted backups
tar -czf backup.tar.gz data/ | gpg -c > backup.tar.gz.gpg
```

### 3. Secure Deletion

```bash
# Securely delete old logs
shred -vfz -n 3 old_logs.log
```

---

## 🚨 Risk Limits

### Hard Limits in Code

Set maximum loss limits in `config/settings.yaml`:

```yaml
risk_management:
  max_daily_loss: 200      # Max $200 loss per day
  max_total_loss: 1000     # Max $1000 total loss
  emergency_stop: true     # Auto-stop on limit
```

### Circuit Breaker

Bot auto-stops if:
- Daily loss > `max_daily_loss`
- Total drawdown > `max_total_drawdown`
- API errors > 10 consecutive

---

## 📊 Monitoring

### 1. Log Analysis

```bash
# Check for suspicious activity
grep -i "unauthorized\|failed\|error" logs/bot.log
```

### 2. Alert Setup

Configure Telegram alerts for:
- Large losses (> 2%)
- API errors
- Unexpected behavior

---

## ⚠️ Pre-Live Checklist

Before trading with real money:

- [ ] Tested on Testnet for 2+ weeks
- [ ] Backtest profitable for 3+ months
- [ ] All API permissions reviewed
- [ ] IP whitelist configured
- [ ] Emergency stop limits set
- [ ] Monitoring alerts active
- [ ] Backup strategy in place
- [ ] Only using risk capital

---

## 🆘 Emergency Procedures

### If Bot Behaves Unexpectedly:

1. **Immediate Stop**:
```bash
sudo systemctl stop crypto-bot
```

2. **Close All Positions** (manually on exchange)

3. **Check Logs**:
```bash
tail -100 logs/bot.log
```

4. **Disable API Keys** on exchange

5. **Investigate** before restarting

---

## 📞 Security Contacts

- **Bybit Support**: https://www.bybit.com/en-US/help-center
- **Report Issues**: GitHub Issues

---

## 🔍 Audit Log

Maintain audit log of:
- All configuration changes
- API key rotations
- Unusual trading activity
- System updates

---

## ⚖️ Legal Disclaimer

- Trading involves significant risk
- Use only what you can afford to lose
- No guarantees of profit
- Author not liable for losses
- Comply with local regulations

---

**Remember: Security is a continuous process, not a one-time setup!**
