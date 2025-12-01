# 🚀 Quick Deploy Guide

## Быстрый старт за 5 минут

### Вариант 1: Docker (проще всего)

```bash
# На VPS:
git clone https://github.com/yourusername/AiCryptoBot.git
cd AiCryptoBot
cp .env.example .env
nano .env  # Добавьте API ключи (см. API_KEYS.md)

# Запустите
docker-compose up -d

# Готово! Откройте http://your_vps_ip:5000
```

### Вариант 2: Автоустановка

```bash
# На VPS:
wget https://raw.githubusercontent.com/yourusername/AiCryptoBot/main/setup_vps.sh
chmod +x setup_vps.sh
./setup_vps.sh

# Следуйте инструкциям
```

---

## 📋 Что нужно перед деплоем?

1. **VPS сервер** (рекомендации):
   - Contabo Singapore - €6.99/мес (4 vCPU, 8GB)
   - Hetzner Germany - €9.5/мес (4 vCPU, 8GB)
   - DigitalOcean Singapore - $12/мес (2 vCPU, 2GB)

2. **API ключи** (ОБЯЗАТЕЛЬНО):
   - **Bybit API Key + Secret** (testnet для начала) - https://testnet.bybit.com
   - **CryptoPanic API** - https://cryptopanic.com/developers/api/ (бесплатно 750 req/день) ✅ У вас есть
   
3. **API ключи** (опционально):
   - **Telegram Bot Token** - создать через @BotFather
   - **NewsAPI Key** - https://newsapi.org/ (для дополнительных новостей)

4. **Домен** (опционально, для SSL):
   - Любой домен с A-записью на IP вашего VPS

**📘 Подробная инструкция по получению ключей:** [API_KEYS.md](API_KEYS.md)

---

## 🎯 Что получите после деплоя?

✅ Web dashboard на http://your_vps_ip:5000
✅ Торговый бот с ML моделями
✅ Real-time мониторинг сделок
✅ Автоматический перезапуск при сбоях
✅ Логирование всех операций

---

## 📚 Полная документация

См. [DEPLOYMENT.md](docs/DEPLOYMENT.md) для детальных инструкций.

## 🆘 Нужна помощь?

- Проверьте логи: `docker-compose logs -f`
- Или: `tail -f /opt/aicryptobot/logs/dashboard.log`
- Troubleshooting в [DEPLOYMENT.md](docs/DEPLOYMENT.md#troubleshooting)
