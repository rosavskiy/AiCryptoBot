# 🚨 Проблема: Bybit Testnet заблокирован!

## Ошибка

```
403 Forbidden
The Amazon CloudFront distribution is configured to block access from your country.
```

**Причина:** Bybit Testnet использует AWS CloudFront, который блокирует доступ из некоторых стран (включая Россию).

---

## ✅ Решение: Переключиться на Binance Testnet

Binance Testnet **НЕ заблокирован** и работает отлично!

### Шаг 1: Получить API ключи Binance Testnet

1. Зайти на https://testnet.binance.vision/
2. Авторизоваться через GitHub
3. Создать API ключ
4. Скопировать **API Key** и **Secret Key**

### Шаг 2: Обновить конфигурацию

На VPS:

```bash
ssh root@85.209.134.246
cd /opt/aicryptobot
nano .env
```

**Изменить:**

```env
# Закомментировать Bybit
#BYBIT_API_KEY=KSKs02hz8WClcK7EMo
#BYBIT_API_SECRET=104ooKKlsqrWqP1H9Nl8jMeIVv8wvHYM1D1Z
#BYBIT_TESTNET=true

# Добавить Binance Testnet
BINANCE_TESTNET_API_KEY=ваш_ключ_от_testnet.binance.vision
BINANCE_TESTNET_API_SECRET=ваш_секрет_от_testnet.binance.vision
BINANCE_TESTNET=true
```

### Шаг 3: Обновить settings.yaml

```bash
nano config/settings.yaml
```

**Изменить:**

```yaml
exchange:
  name: binance  # было: bybit
  testnet: true
  rate_limit: true
```

### Шаг 4: Проверить подключение

```bash
python -c "
import ccxt
exchange = ccxt.binance({
    'apiKey': 'ваш_testnet_ключ',
    'secret': 'ваш_testnet_секрет',
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})
exchange.set_sandbox_mode(True)  # Testnet mode
print('Balance:', exchange.fetch_balance())
"
```

---

## 🔧 Альтернатива: VPN на VPS

Если хотите остаться на Bybit:

```bash
# Установить WireGuard VPN
apt update
apt install wireguard

# Или использовать HTTP прокси
apt install proxychains4
nano /etc/proxychains4.conf

# Добавить прокси-сервер:
# socks5 proxy_ip proxy_port

# Запускать бота через прокси:
proxychains4 python main.py
```

---

## 📊 Сравнение Binance vs Bybit Testnet

| Параметр | Binance Testnet | Bybit Testnet |
|----------|-----------------|---------------|
| **Доступность** | ✅ Не блокируется | ❌ Блокируется в РФ |
| **Регистрация** | GitHub OAuth | Email |
| **Баланс** | 1000 USDT | 100,000 USDT |
| **Spot** | ✅ Да | ❌ Нет |
| **Futures** | ✅ Да | ✅ Да |
| **API лимиты** | Строже | Мягче |
| **Стабильность** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**Рекомендация:** Используйте **Binance Testnet** для тестирования в России.

---

## 🚀 Быстрая настройка Binance Testnet

```bash
# 1. Получить ключи
# https://testnet.binance.vision/ → Generate API Key

# 2. Обновить .env
cat > .env << 'EOF'
BINANCE_TESTNET_API_KEY=ваш_ключ
BINANCE_TESTNET_API_SECRET=ваш_секрет
BINANCE_TESTNET=true
TRADE_MODE=testnet
EOF

# 3. Обновить settings.yaml
sed -i 's/name: bybit/name: binance/g' config/settings.yaml

# 4. Обучить модели
source venv/bin/activate
python scripts/train_ensemble.py

# 5. Запустить бота
python main.py --mode live --web-dashboard
```

---

## ✅ После переключения на Binance

Всё будет работать так же:
- ✅ Виртуальные деньги (~1000 USDT)
- ✅ Реальные рыночные данные
- ✅ ML модели
- ✅ Автоматическая торговля
- ✅ Веб-дашборд

**НО:**
- Доступ работает без VPN
- Никаких блокировок
- Стабильнее

---

## 📝 Следующие шаги

1. Получить ключи на https://testnet.binance.vision/
2. Обновить `.env` и `settings.yaml`
3. Обучить модели: `python scripts/train_ensemble.py`
4. Запустить бота: `python main.py --mode live --web-dashboard`

**Binance Testnet = лучший выбор для тестирования из России! 🇷🇺**
