# 🐳 Docker Deployment Guide

## Quick Start

### 1. Build the image

```bash
docker build -t crypto-bot:latest .
```

### 2. Run with docker-compose

```bash
docker-compose up -d
```

---

## Configuration

Edit `.env` and `config/settings.yaml` before building.

### Environment Variables

```env
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret
BYBIT_TESTNET=true
```

---

## Useful Commands

```bash
# View logs
docker-compose logs -f bot

# Restart
docker-compose restart bot

# Stop
docker-compose down

# Rebuild
docker-compose up -d --build
```

---

## Volumes

Data is persisted in:
- `./data` - Database and results
- `./logs` - Application logs
- `./models` - ML models
