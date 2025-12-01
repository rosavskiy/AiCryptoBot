# 🎮 Запуск бота на Testnet (виртуальные деньги)

## ✅ У вас уже настроено!

Смотрю ваш `.env` файл - всё готово к запуску:

```env
BYBIT_API_KEY=KSKs02hz8WClcK7EMo
BYBIT_API_SECRET=104ooKKlsqrWqP1H9Nl8jMeIVv8wvHYM1D1Z
BYBIT_TESTNET=true  ← ВИРТУАЛЬНЫЕ ДЕНЬГИ
TRADE_MODE=paper
```

**Это означает:**
- ✅ Подключение к **Bybit Testnet** (не реальная биржа)
- ✅ Виртуальные деньги (~$100,000 USDT на тестовом счёте)
- ✅ Реальные рыночные данные
- ✅ Реальная торговля, но БЕЗ РИСКА

---

## 🚀 Как запустить бота на Testnet

### Шаг 1: Обучить модели

```bash
ssh root@85.209.134.246
cd /opt/aicryptobot
source venv/bin/activate

# Обучить ML модели на свежих данных
python scripts/train_ensemble.py
```

**Это займёт 5-10 минут.** Модели обучатся на последних 2000 свечах BTC/USDT.

---

### Шаг 2: Остановить демо-дашборд

```bash
# Остановить текущий демо-режим
systemctl stop aibot-dashboard
```

---

### Шаг 3: Запустить настоящего бота

```bash
cd /opt/aicryptobot
source venv/bin/activate

# Запустить бота в Testnet режиме с веб-дашбордом
nohup python main.py --mode live --web-dashboard > logs/bot_testnet.log 2>&1 &

# Сохранить PID для остановки позже
echo $! > /tmp/aibot.pid
```

**Или можно запустить в текущем терминале (чтобы видеть логи):**

```bash
python main.py --mode live --web-dashboard
```

---

### Шаг 4: Проверить что бот работает

```bash
# Посмотреть логи в реальном времени
tail -f logs/bot_testnet.log

# Или найти последний лог файл
tail -f logs/trading_*.log
```

**Должны увидеть:**

```
[INFO] AI Crypto Bot Starting...
[INFO] Mode: LIVE
[INFO] Exchange: Bybit Testnet
[INFO] Loading ML models...
[INFO] Models loaded successfully
[INFO] Starting web dashboard on http://0.0.0.0:5000
[INFO] Connecting to exchange...
[INFO] Connected to Bybit Testnet
[INFO] Balance: $100,000.00 USDT (testnet)
[INFO] Fetching market data for BTC/USDT...
[ML] Analyzing market conditions...
[ML] Prediction: BUY (confidence: 68%)
[SIGNAL] Signal strength: STRONG
[TRADE] Opening LONG position...
```

---

### Шаг 5: Открыть дашборд

Перейти на: **http://85.209.134.246**

**Теперь увидите:**
- 📊 Реальные графики P&L
- 🤖 ML предсказания
- 📰 Анализ новостей
- 💼 Открытые позиции (testnet)
- 📈 Статистика сделок

---

## 🔍 Что будет происходить

### Каждые 15 минут:

1. **Получение данных**
   ```
   [MARKET] Fetching BTC/USDT 15m candles
   [MARKET] Last price: $97,234.50
   ```

2. **ML анализ**
   ```
   [ML] RandomForest prediction: BUY (0.72)
   [ML] LSTM prediction: BUY (0.68)
   [ML] Ensemble decision: BUY (confidence: 70%)
   ```

3. **Анализ новостей**
   ```
   [NEWS] Fetched 15 articles
   [SENTIMENT] Average sentiment: +0.65 (POSITIVE)
   ```

4. **Генерация сигнала**
   ```
   [SIGNAL] ML: BUY (70%)
   [SIGNAL] Sentiment: POSITIVE (65%)
   [SIGNAL] Final signal: BUY
   ```

5. **Проверка рисков**
   ```
   [RISK] Position size: 0.005 BTC ($485)
   [RISK] Risk per trade: 1.0%
   [RISK] Max loss: $100
   [RISK] Stop Loss: $95,321 (-1.96%)
   [RISK] Take Profit: $100,856 (+3.73%)
   ```

6. **Открытие сделки** (если сигнал подтверждён)
   ```
   [TRADE] Opening LONG @ $97,234
   [TRADE] Size: 0.005 BTC
   [TRADE] SL: $95,321 | TP: $100,856
   [TRADE] ✅ Order filled
   ```

---

## 🎯 Преимущества Testnet

| Что? | Testnet | Paper Trading |
|------|---------|---------------|
| **Реальные цены** | ✅ Да | ✅ Да |
| **Реальное API** | ✅ Да | ❌ Нет (симуляция) |
| **Проскальзывание** | ✅ Реальное | ❌ Идеальное |
| **Задержки ордеров** | ✅ Реальные | ❌ Мгновенно |
| **Лимиты API** | ✅ Есть | ❌ Нет |
| **Риск денег** | ✅ НЕТ ($0) | ✅ НЕТ ($0) |

**Testnet = максимально близко к реальности БЕЗ РИСКА**

---

## ⚙️ Настройка параметров торговли

Отредактировать `config/settings.yaml`:

```yaml
# Размер риска
risk:
  risk_per_trade: 0.01  # 1% от баланса
  max_positions: 3      # Макс 3 позиции одновременно
  max_daily_loss: 0.02  # Стоп на день при -2%

# Торговая пара
symbols:
  - BTC/USDT
  - ETH/USDT  # Можно добавить больше

# Таймфрейм
timeframe:
  trading: 15m  # Анализировать каждые 15 минут

# ML уверенность
ml:
  confidence_threshold: 0.60  # Минимум 60% для входа
```

**После изменения:**
```bash
# Перезапустить бота
pkill -f main.py
python main.py --mode live --web-dashboard
```

---

## 🛠️ Управление ботом

### Запустить бота:
```bash
cd /opt/aicryptobot
source venv/bin/activate
nohup python main.py --mode live --web-dashboard > logs/bot.log 2>&1 &
echo $! > /tmp/aibot.pid
```

### Остановить бота:
```bash
# Вариант 1: По PID
kill $(cat /tmp/aibot.pid)

# Вариант 2: Найти процесс
pkill -f main.py

# Вариант 3: Через systemd (если настроен)
systemctl stop aibot-trading
```

### Посмотреть логи:
```bash
# Реального времени
tail -f logs/trading_*.log

# Последние 100 строк
tail -100 logs/trading_*.log

# Фильтр только сделок
tail -f logs/trading_*.log | grep TRADE
```

### Проверить баланс на Testnet:
```bash
python -c "
from src.exchange.bybit_client import BybitClient
client = BybitClient()
balance = client.get_balance()
print(f'Testnet Balance: {balance}')
"
```

---

## 📊 Мониторинг через дашборд

После запуска откройте: **http://85.209.134.246**

**Вкладка "Обзор":**
- Баланс (testnet USDT)
- P&L график
- Открытые позиции
- Win Rate

**Вкладка "Новости":**
- Последние новости
- Sentiment анализ
- График sentiment

**Вкладка "Логи":**
- ML предсказания
- Торговые сигналы
- Открытие/закрытие позиций
- Ошибки (если есть)

---

## 🔧 Автоматический запуск через systemd

Создать service файл:

```bash
sudo nano /etc/systemd/system/aibot-trading.service
```

```ini
[Unit]
Description=AI Crypto Bot Trading (Testnet)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aicryptobot
Environment="PATH=/opt/aicryptobot/venv/bin"
ExecStart=/opt/aicryptobot/venv/bin/python main.py --mode live --web-dashboard
Restart=always
RestartSec=10
StandardOutput=append:/opt/aicryptobot/logs/bot.log
StandardError=append:/opt/aicryptobot/logs/bot_error.log

[Install]
WantedBy=multi-user.target
```

**Активировать:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable aibot-trading
sudo systemctl start aibot-trading

# Проверить
sudo systemctl status aibot-trading
```

---

## ⚠️ Важные замечания

### 1. Testnet сбрасывается периодически

Bybit Testnet может сбросить баланс или позиции. Это нормально.

**Решение:** Просто перезапустить бота, баланс восстановится.

---

### 2. Testnet API может быть медленнее

Иногда testnet отвечает медленно или падает.

**Не паникуйте!** Это тестовый сервер, в mainnet такого нет.

---

### 3. Первые сделки могут быть через 15-30 минут

Бот ждёт уверенного сигнала (confidence > 60%).

**Наберитесь терпения!** Если рынок спокойный, сигналов может не быть.

---

### 4. Win Rate ~55-60% это ХОРОШО

Не ждите 90% побед. В крипто трейдинге:
- **55%+ win rate** = отлично
- **Sharpe ratio > 1.0** = профитно
- **Max drawdown < 15%** = безопасно

---

## 🎯 Ожидаемые результаты (30 дней testnet)

**Хорошо:**
- Total Trades: 20-40
- Win Rate: 55-65%
- Total P&L: +5% до +15%
- Sharpe Ratio: 1.0-2.0
- Max Drawdown: 5-10%

**Отлично:**
- Win Rate: 65%+
- Total P&L: +15%+
- Sharpe > 2.0
- Max DD < 5%

**Плохо (нужно переобучить):**
- Win Rate < 50%
- Total P&L: отрицательный
- Max DD > 20%

---

## 🚀 Быстрый старт (копируй-вставляй)

```bash
# 1. Подключиться
ssh root@85.209.134.246

# 2. Остановить демо
systemctl stop aibot-dashboard

# 3. Обучить модели
cd /opt/aicryptobot
source venv/bin/activate
python scripts/train_ensemble.py

# 4. Запустить бота
nohup python main.py --mode live --web-dashboard > logs/bot.log 2>&1 &
echo $! > /tmp/aibot.pid

# 5. Смотреть логи
tail -f logs/bot.log

# 6. Открыть браузер
# http://85.209.134.246
```

**Готово! Бот торгует на Testnet 🎉**

---

## 📞 Проблемы?

### Бот не запускается:
```bash
# Проверить ошибки
cat logs/bot.log | grep ERROR
```

### Нет сигналов 30 минут:
```bash
# Проверить что ML модели загружены
cat logs/bot.log | grep "Models loaded"

# Проверить confidence
cat logs/bot.log | grep "confidence"
```

### API ошибки:
```bash
# Проверить ключи
cat .env | grep BYBIT

# Тест подключения
python -c "from src.exchange.bybit_client import BybitClient; BybitClient().get_balance()"
```

---

## 🎓 После 1-2 недель Testnet

Если результаты хорошие:
1. ✅ Win Rate > 55%
2. ✅ Sharpe > 1.0
3. ✅ Стабильная работа

**Можно переходить на Mainnet:**
```bash
# В .env изменить:
BYBIT_TESTNET=false
BYBIT_API_KEY=ваш_mainnet_ключ
BYBIT_API_SECRET=ваш_mainnet_секрет
```

**НО!** Рекомендую начать с **минимального депозита** ($100-500).

---

**Удачной торговли на Testnet! 🚀**
