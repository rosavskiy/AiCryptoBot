# 🐛 Troubleshooting Guide

Common issues and solutions for AiCryptoBot.

---

## 🔴 Installation Issues

### Problem: `pip install` fails

**Solution:**
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v

# If specific package fails (e.g., pandas-ta)
pip install pandas-ta --no-cache-dir
```

### Problem: Python version mismatch

**Error:** `Python 3.8 required, you have 3.7`

**Solution:**
```bash
# Check version
python --version

# Install Python 3.9+
# Windows: Download from python.org
# Linux: sudo apt install python3.9
```

---

## 🔴 Configuration Issues

### Problem: `.env` file not loaded

**Symptoms:** `KeyError: 'BYBIT_API_KEY'`

**Solution:**
```bash
# Check file exists
ls .env

# Verify format (no quotes)
BYBIT_API_KEY=your_key_here

# Not: BYBIT_API_KEY="your_key_here"
```

### Problem: `settings.yaml` parse error

**Error:** `yaml.scanner.ScannerError`

**Solution:**
```yaml
# Check indentation (use spaces, not tabs)
# Bad:
ml:
	model_type: random_forest

# Good:
ml:
  model_type: random_forest
```

---

## 🔴 API Connection Issues

### Problem: Bybit API authentication failed

**Error:** `ccxt.AuthenticationError: Invalid API key`

**Solutions:**

1. **Check API key format:**
```env
# Should be alphanumeric, no spaces
BYBIT_API_KEY=abc123def456
BYBIT_API_SECRET=xyz789uvw012
```

2. **Verify Testnet mode:**
```env
# For Testnet keys
BYBIT_TESTNET=true

# For Mainnet keys  
BYBIT_TESTNET=false
```

3. **Check IP whitelist** on Bybit dashboard

### Problem: Rate limit exceeded

**Error:** `ccxt.RateLimitExceeded`

**Solution:**
```python
# In settings.yaml, increase delay
api:
  bybit:
    rate_limit: 120  # Reduce from 120 to 60
```

### Problem: API connection timeout

**Error:** `requests.exceptions.ConnectionError`

**Solutions:**
1. Check internet connection
2. Verify exchange is not under maintenance
3. Try different endpoint:
```bash
ping api-testnet.bybit.com
```

---

## 🔴 Data Issues

### Problem: Not enough historical data

**Error:** `Insufficient data: need 1000, got 500`

**Solution:**
```yaml
# In settings.yaml
timeframe:
  lookback_bars: 500  # Reduce from 1000
```

### Problem: Missing indicators (NaN values)

**Solution:**
```python
# Indicators need warmup period
# RSI(14) needs 14+ candles
# SMA(200) needs 200+ candles

# Increase data fetch
total_candles: 1500  # From 1000
```

---

## 🔴 ML Model Issues

### Problem: Model accuracy very low

**Symptoms:** Accuracy < 55%

**Solutions:**

1. **More training data:**
```python
# Fetch more historical data
train_size: 800  # From 400
```

2. **Feature engineering:**
```yaml
# Add more features
ml:
  features:
    - RSI
    - ATR
    - volume
    - SMA_50
    - SMA_200
    - MACD
    - MACD_signal
    - BB_upper
    - BB_lower
    - volume_sma_ratio
    - EMA_12    # Add more
    - ADX       # Add more
```

3. **Hyperparameter tuning:**
```yaml
ml:
  n_estimators: 200  # From 100
  max_depth: 20      # From 15
```

### Problem: Model overfitting

**Symptoms:** Train accuracy 95%, Test accuracy 50%

**Solutions:**

1. **Reduce model complexity:**
```yaml
ml:
  max_depth: 10      # Limit tree depth
  min_samples_split: 20  # Increase
```

2. **More regularization:**
```yaml
ml:
  min_samples_leaf: 5  # From 1
```

### Problem: "Model not trained" error

**Solution:**
```bash
# Train model first
python train_model.py --symbol BTC/USDT

# Verify model exists
ls models/btc_model.pkl
```

---

## 🔴 Trading Issues

### Problem: No trades executed

**Possible causes:**

1. **ML confidence too low:**
```yaml
# Lower threshold
ml:
  buy_threshold: 55  # From 60
```

2. **Sentiment filter blocking:**
```yaml
# Disable sentiment
sentiment:
  enabled: false
```

3. **Risk limits hit:**
```bash
# Check logs
grep "Risk limit" logs/bot.log
```

### Problem: Positions not closing

**Solution:**
```bash
# Manually close on exchange
# Then restart bot
sudo systemctl restart crypto-bot
```

### Problem: Stop-loss not triggered

**Possible cause:** Bot stopped

**Solution:**
```bash
# Check if running
systemctl status crypto-bot

# Check logs
tail -f logs/bot.log
```

---

## 🔴 Backtesting Issues

### Problem: Backtest takes too long

**Solution:**
```yaml
# Reduce data size
backtesting:
  data:
    total_candles: 500  # From 1000
```

### Problem: Unrealistic results

**Symptoms:** 90% win rate, 500% return

**Causes:**
1. **Data leakage** - Check Walk-Forward implementation
2. **Overfitting** - Reduce model complexity
3. **Survivorship bias** - Test on multiple periods

**Solution:**
```bash
# Run on different time periods
python run_backtest.py --start 2024-01-01 --end 2024-06-01
python run_backtest.py --start 2024-06-01 --end 2024-12-01
```

---

## 🔴 Database Issues

### Problem: Database locked

**Error:** `sqlite3.OperationalError: database is locked`

**Solution:**
```bash
# Close all connections
pkill -f run_bot.py

# Check database integrity
sqlite3 data/trading.db "PRAGMA integrity_check;"

# If corrupt, restore from backup
cp backups/trading_backup.db data/trading.db
```

### Problem: Database file not found

**Solution:**
```bash
# Create directory
mkdir -p data

# Bot will create DB on first run
python run_bot.py
```

---

## 🔴 Memory Issues

### Problem: Bot uses too much RAM

**Symptoms:** VPS freezes, OOM errors

**Solutions:**

1. **Add swap file:**
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

2. **Reduce data retention:**
```yaml
# In settings.yaml
timeframe:
  lookback_bars: 500  # From 1000
```

3. **Clear old logs:**
```bash
# Setup logrotate
sudo nano /etc/logrotate.d/crypto-bot
```

---

## 🔴 Logging Issues

### Problem: No logs generated

**Solution:**
```bash
# Check directory exists
mkdir -p logs

# Check permissions
chmod 755 logs

# Verify logging config
grep -i log config/settings.yaml
```

### Problem: Log file too large

**Solution:**
```bash
# Manual cleanup
truncate -s 0 logs/bot.log

# Setup logrotate (see above)
```

---

## 🔴 Deployment Issues

### Problem: Systemd service fails to start

**Error:** `Failed to start crypto-bot.service`

**Solution:**
```bash
# Check service status
sudo systemctl status crypto-bot

# View detailed logs
sudo journalctl -u crypto-bot -n 50

# Common fix: wrong Python path
# Edit service file
sudo nano /etc/systemd/system/crypto-bot.service
# Fix ExecStart path

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart crypto-bot
```

### Problem: Docker container crashes

**Solution:**
```bash
# View container logs
docker logs crypto-bot

# Check resource limits
docker stats crypto-bot

# Rebuild with fixes
docker-compose down
docker-compose up -d --build
```

---

## 🔴 Performance Issues

### Problem: Bot is slow

**Solutions:**

1. **Optimize data fetching:**
```python
# Cache OHLCV data
# Fetch once, reuse multiple times
```

2. **Reduce ML complexity:**
```yaml
ml:
  n_estimators: 50  # From 100
```

3. **Disable sentiment:**
```yaml
sentiment:
  enabled: false
```

---

## 🆘 Emergency Procedures

### Complete Reset

```bash
# 1. Stop bot
sudo systemctl stop crypto-bot

# 2. Backup data
cp -r data data_backup_$(date +%Y%m%d)

# 3. Clear caches
rm -rf __pycache__
find . -name "*.pyc" -delete

# 4. Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# 5. Reset database (WARNING: loses trade history)
rm data/trading.db

# 6. Restart
sudo systemctl start crypto-bot
```

---

## 📞 Getting Help

If issue persists:

1. **Check logs** thoroughly:
```bash
tail -200 logs/bot.log | grep ERROR
```

2. **Enable debug mode:**
```yaml
logging:
  level: DEBUG
```

3. **Report issue** on GitHub with:
   - Error message
   - Relevant logs
   - Configuration (without API keys!)
   - Steps to reproduce

---

## 🔍 Diagnostic Commands

```bash
# System info
python --version
pip list | grep -E "ccxt|pandas|sklearn"

# Bot health
systemctl status crypto-bot
ps aux | grep python

# Database check
sqlite3 data/trading.db "SELECT COUNT(*) FROM trades;"

# API connectivity
curl https://api-testnet.bybit.com/v5/market/time
```

---

**Remember:** Always test fixes on Testnet before Mainnet!
