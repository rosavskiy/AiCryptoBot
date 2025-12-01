# 🤖 Алгоритм работы бота

## 📋 Краткое описание

Бот работает **периодически** (по таймеру), а не по триггерам. Каждые 15 минут (настраивается) он:
1. Анализирует рынок
2. Собирает новости и sentiment
3. Делает ML предсказание
4. Принимает торговое решение
5. Проверяет открытые позиции

---

## ⏰ Основной цикл

```
┌─────────────────────────────────────────────┐
│   ГЛАВНЫЙ ЦИКЛ (каждые N минут)             │
└─────────────────────────────────────────────┘
                    ↓
    ┌──────────────────────────────────┐
    │  1. ПРОВЕРКА ПОЗИЦИЙ             │
    └──────────────────────────────────┘
    │  • Есть открытые позиции?
    │  • Take Profit достигнут?
    │  • Stop Loss сработал?
    │  • Время удержания > максимума?
    │  → Закрыть если нужно
                    ↓
    ┌──────────────────────────────────┐
    │  2. ПОЛУЧЕНИЕ ДАННЫХ             │
    └──────────────────────────────────┘
    │  • Цена BTC/USDT с биржи
    │  • OHLCV данные (500 свечей)
    │  • Volume, High, Low
                    ↓
    ┌──────────────────────────────────┐
    │  3. ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ       │
    └──────────────────────────────────┘
    │  • RSI (14 период)
    │  • MACD (12, 26, 9)
    │  • Bollinger Bands
    │  • ATR (14) - волатильность
    │  • SMA (50, 200)
                    ↓
    ┌──────────────────────────────────┐
    │  4. SENTIMENT АНАЛИЗ             │
    └──────────────────────────────────┘
    │  • Получить новости (CryptoPanic)
    │  • Анализ через TextBlob/FinBERT
    │  • Средний sentiment score
    │  • Кэш на 30 минут
                    ↓
    ┌──────────────────────────────────┐
    │  5. ML ПРЕДСКАЗАНИЕ              │
    └──────────────────────────────────┘
    │  LSTM модель:
    │    • Входы: цена, volume, индикаторы
    │    • Выход: вероятность роста
    │  
    │  Random Forest:
    │    • Классификация: BUY/SELL/HOLD
    │    • Feature importance
    │  
    │  Логистическая регрессия:
    │    • Дополнительное мнение
    │  
    │  ENSEMBLE (Голосование):
    │    • LSTM: 40% веса
    │    • RF: 40% веса
    │    • LR: 20% веса
    │    → Итоговый сигнал + Confidence
                    ↓
    ┌──────────────────────────────────┐
    │  6. ПРОВЕРКА УСЛОВИЙ             │
    └──────────────────────────────────┘
    │  ✓ ML Confidence > 70%?
    │  ✓ Sentiment > 0.3 (позитивный)?
    │  ✓ Risk exposure < max (50%)?
    │  ✓ Свободный капитал есть?
    │  ✓ Нет противоречий в индикаторах?
                    ↓
    ┌──────────────────────────────────┐
    │  7. ПРИНЯТИЕ РЕШЕНИЯ             │
    └──────────────────────────────────┘
    │  ДА → Открыть сделку
    │    • Рассчитать размер позиции
    │    • Установить Stop Loss / Take Profit
    │    • Выполнить ордер
    │  
    │  НЕТ → Пропустить цикл
    │    • Логировать причину
    │    • Подождать следующего интервала
                    ↓
    ┌──────────────────────────────────┐
    │  8. УПРАВЛЕНИЕ РИСКАМИ           │
    └──────────────────────────────────┘
    │  • Position sizing (1% капитала)
    │  • Stop Loss: ATR * 2
    │  • Take Profit: ATR * 3
    │  • Max 3 открытых позиции
    │  • Max 50% exposure
                    ↓
          ⏰ Sleep (15 минут)
                    ↓
              ПОВТОР ЦИКЛА
```

---

## 🎯 Детальный разбор каждого шага

### 1️⃣ Проверка позиций (Check Positions)

**Файл:** `src/trading/executor.py` → `check_positions()`

```python
def check_positions(self):
    for position in active_positions:
        current_price = get_current_price()
        
        # Take Profit?
        if current_price >= position.take_profit:
            close_position(position, reason="Take Profit")
        
        # Stop Loss?
        elif current_price <= position.stop_loss:
            close_position(position, reason="Stop Loss")
        
        # Максимальное время удержания?
        elif time_held > max_hold_time:
            close_position(position, reason="Max Hold Time")
```

**Логи:**
```
[CHECK] Checking 2 active positions...
[POSITION] BTC/USDT LONG: Entry=95000, Current=96500, P&L=+1.58%
[CLOSE] Take Profit reached! Closing BTC/USDT LONG
```

---

### 2️⃣ Получение рыночных данных

**Файл:** `src/data/market_fetcher.py` → `fetch_ohlcv()`

```python
def fetch_ohlcv(symbol='BTC/USDT', timeframe='15m', limit=500):
    # Получить с биржи через CCXT
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit)
    
    # Преобразовать в DataFrame
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Добавить индикаторы
    df['rsi'] = calculate_rsi(df['close'])
    df['macd'] = calculate_macd(df['close'])
    df['bb_upper'], df['bb_lower'] = calculate_bollinger(df['close'])
    
    return df
```

**Логи:**
```
[DATA] Fetching BTC/USDT market data...
[DATA] Retrieved 500 candles (15m timeframe)
[DATA] Current price: $96,450.00
```

---

### 3️⃣ Технические индикаторы

**Файл:** `src/data/market_fetcher.py` → `add_technical_indicators()`

**Индикаторы:**
- **RSI** (Relative Strength Index): перекупленность/перепроданность
  - RSI > 70 → Перекупленность (возможно падение)
  - RSI < 30 → Перепроданность (возможен рост)

- **MACD** (Moving Average Convergence Divergence): тренд
  - MACD > Signal → Bullish (рост)
  - MACD < Signal → Bearish (падение)

- **Bollinger Bands**: волатильность и границы цены
  - Цена у верхней полосы → Перекупленность
  - Цена у нижней полосы → Перепроданность

- **ATR** (Average True Range): волатильность для Stop Loss/Take Profit

**Логи:**
```
[INDICATORS] RSI=45.2 (neutral)
[INDICATORS] MACD=positive (bullish)
[INDICATORS] BB: price near lower band (oversold signal)
[INDICATORS] ATR=$1,250 (moderate volatility)
```

---

### 4️⃣ Sentiment анализ новостей

**Файл:** `src/sentiment/news_analyzer.py` → `get_sentiment()`

```python
def get_sentiment(symbol='BTC', hours_back=24):
    # Получить новости с CryptoPanic
    news = fetch_cryptopanic(symbol, filter='hot')
    
    # Анализ каждой новости
    sentiments = []
    for article in news:
        score = analyze_text(article.title)  # TextBlob или FinBERT
        sentiments.append(score)
    
    # Средний sentiment
    avg_sentiment = sum(sentiments) / len(sentiments)
    
    # Категория
    if avg_sentiment > 0.3:
        label = "Positive"
    elif avg_sentiment < -0.3:
        label = "Negative"
    else:
        label = "Neutral"
    
    return avg_sentiment, label
```

**Логи:**
```
[NEWS] Fetching news for BTC...
[NEWS] Fetched 15 articles from CryptoPanic
[NEWS] 📰 "Bitcoin reaches new all-time high" (sentiment: 0.85)
[NEWS] 📰 "ETF approval expected soon" (sentiment: 0.72)
[NEWS] 📊 Average sentiment: 0.62 (Positive)
```

---

### 5️⃣ ML Предсказание (Ensemble)

**Файл:** `src/ml/predictor.py` → `predict()`

**3 модели голосуют:**

1. **LSTM** (Long Short-Term Memory):
   - Анализирует временные ряды
   - Входы: последние 60 свечей (цена, volume, индикаторы)
   - Выход: вероятность роста (0-1)

2. **Random Forest**:
   - Классификация на основе признаков
   - Входы: RSI, MACD, BB, sentiment, volume
   - Выход: BUY/SELL/HOLD + вероятность

3. **Логистическая регрессия**:
   - Быстрая линейная модель
   - Входы: те же признаки
   - Выход: вероятность BUY

**Ensemble (Голосование):**
```python
lstm_prediction = 0.78  # 78% вероятность роста
rf_prediction = 'BUY' (confidence=0.85)
lr_prediction = 0.72

# Взвешенное голосование
final_score = (lstm_prediction * 0.4) + 
              (rf_confidence * 0.4) + 
              (lr_prediction * 0.2)
            = 0.796 (79.6%)

if final_score > 0.7:
    signal = 'BUY'
else:
    signal = 'HOLD'
```

**Логи:**
```
[ML] 🧠 LSTM prediction: 0.78 (bullish)
[ML] 🌲 Random Forest: BUY (confidence: 0.85)
[ML] 📊 Logistic Regression: 0.72 (positive)
[ML] 🎯 ENSEMBLE: BUY signal (confidence: 79.6%)
```

---

### 6️⃣ Проверка условий

**Файл:** `src/trading/executor.py` → `generate_signal()`

```python
def generate_signal(analysis):
    # Условие 1: ML Confidence
    if analysis['ml_confidence'] < 0.7:
        return False, "ML confidence too low", None
    
    # Условие 2: Sentiment
    if analysis['sentiment_score'] < 0.3:
        return False, "Negative sentiment", None
    
    # Условие 3: Risk Management
    if risk_manager.total_exposure > 0.5:
        return False, "Max exposure reached", None
    
    # Условие 4: Свободный капитал
    if risk_manager.available_capital < min_trade_size:
        return False, "Insufficient capital", None
    
    # Условие 5: Технические индикаторы не противоречат
    if analysis['rsi'] > 80:
        return False, "RSI overbought", None
    
    # ✅ ВСЕ УСЛОВИЯ ВЫПОЛНЕНЫ
    direction = 'LONG' if analysis['ml_signal'] == 'BUY' else 'SHORT'
    return True, "All conditions met", direction
```

**Логи:**
```
[SIGNAL] Checking trading conditions...
[SIGNAL] ✓ ML confidence: 79.6% (>70%)
[SIGNAL] ✓ Sentiment: 0.62 (>0.3)
[SIGNAL] ✓ Risk exposure: 25% (<50%)
[SIGNAL] ✓ Available capital: $7,500
[SIGNAL] ✓ RSI: 45.2 (not overbought)
[SIGNAL] ✅ ALL CONDITIONS MET → TRADE
```

---

### 7️⃣ Выполнение сделки

**Файл:** `src/trading/executor.py` → `execute_trade()`

```python
def execute_trade(analysis, direction, dry_run=False):
    # Рассчитать размер позиции
    risk_amount = capital * risk_per_trade  # 1% капитала
    position_size = calculate_position_size(risk_amount, analysis['atr'])
    
    # Stop Loss / Take Profit
    if direction == 'LONG':
        entry_price = analysis['price']
        stop_loss = entry_price - (analysis['atr'] * 2)
        take_profit = entry_price + (analysis['atr'] * 3)
    
    # Dry run или реальный ордер
    if dry_run:
        # Симуляция
        position = create_simulated_position(...)
    else:
        # Реальный ордер на бирже
        order = exchange.create_market_order(
            symbol=symbol,
            side='buy',
            amount=position_size
        )
    
    # Логирование
    log_trade(position)
    
    return position
```

**Логи:**
```
[TRADE] 🎯 Opening LONG position: BTC/USDT
[TRADE] Entry: $96,450
[TRADE] Size: 0.078 BTC ($7,500)
[TRADE] Stop Loss: $93,950 (-2.59%)
[TRADE] Take Profit: $100,200 (+3.89%)
[TRADE] Risk: $100 (1% of capital)
[TRADE] ✅ Order executed successfully
```

---

### 8️⃣ Цикл продолжается

```python
def run_trading_loop(interval_seconds=900):  # 15 минут
    while True:
        # Весь цикл выше
        check_positions()
        analyze_market()
        get_sentiment()
        ml_prediction()
        check_conditions()
        execute_if_needed()
        
        # Подождать следующего интервала
        time.sleep(interval_seconds)
```

**Логи:**
```
[LOOP] Iteration #45 completed
[LOOP] Next check in 15 minutes (16:45:00)
[LOOP] ⏰ Sleeping...
```

---

## 📊 Как отследить работу бота

### 1️⃣ Через Dashboard (Web UI)

**URL:** http://85.209.134.246

**Вкладка "Обзор":**
- ✅ Статус бота: Running/Stopped
- ✅ Время работы: Uptime
- ✅ P&L: Общий результат
- ✅ Открытые позиции: Список активных сделок
- ✅ История сделок: Последние 10 сделок
- ✅ График P&L: Динамика прибыли

**Вкладка "Новости":**
- ✅ Sentiment chart: График настроения рынка
- ✅ Последние новости: Что бот анализирует
- ✅ Sentiment summary: Positive/Neutral/Negative

**Вкладка "Логи":**
- ✅ Все действия бота в реальном времени
- ✅ Фильтры: Новости / ML / Сделки / Ошибки
- ✅ Кнопка "Загрузить историю": Посмотреть что было раньше

---

### 2️⃣ Через логи (SSH на VPS)

```bash
# Подключиться к VPS
ssh root@85.209.134.246

# Логи в реальном времени
journalctl -u aibot-dashboard -f

# Последние 100 строк
journalctl -u aibot-dashboard -n 100

# Только сделки
journalctl -u aibot-dashboard | grep TRADE

# Только ML предсказания
journalctl -u aibot-dashboard | grep ML

# Только новости
journalctl -u aibot-dashboard | grep NEWS

# Только ошибки
journalctl -u aibot-dashboard -p err
```

**Что искать в логах:**

```
✅ ХОРОШИЕ ПРИЗНАКИ:
[LOOP] Iteration #X - Бот работает
[DATA] Fetching market data... - Получает данные
[ML] ENSEMBLE: confidence X% - Делает предсказания
[NEWS] Fetched X articles - Анализирует новости
[SIGNAL] ALL CONDITIONS MET - Нашел возможность
[TRADE] Order executed - Открыл сделку
[CLOSE] Take Profit reached - Закрыл в прибыли

❌ ПЛОХИЕ ПРИЗНАКИ:
[ERROR] Failed to fetch data - Проблемы с биржей
[ERROR] ML model not found - Нет модели
[WARNING] API rate limit - Превышен лимит запросов
[SIGNAL] ML confidence too low - Нет уверенности
[CLOSE] Stop Loss triggered - Закрыл в убытке
```

---

### 3️⃣ Через файловые логи

```bash
# На VPS
tail -f /opt/aicryptobot/logs/dashboard.log

# Последние 500 строк
tail -n 500 /opt/aicryptobot/logs/dashboard.log

# Поиск по дате
grep "2025-12-01 15:" /opt/aicryptobot/logs/dashboard.log

# Экспорт в файл
tail -n 5000 /opt/aicryptobot/logs/dashboard.log > my_analysis.txt
```

---

### 4️⃣ Через базу данных

```bash
# На VPS
cd /opt/aicryptobot
sqlite3 data/trading.db

# SQL запросы:
SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM positions WHERE status='open';
SELECT AVG(pnl_pct) FROM trades WHERE status='closed';
SELECT COUNT(*) as wins FROM trades WHERE pnl_pct > 0;
```

---

## 🔍 Типичный рабочий цикл (пример)

### Цикл #1 (15:00):
```
[15:00:00] [LOOP] Iteration #42
[15:00:01] [CHECK] Checking 1 active position
[15:00:01] [POSITION] BTC/USDT LONG: P&L=+1.2% (holding)
[15:00:02] [DATA] Fetching BTC/USDT data...
[15:00:03] [DATA] Price: $96,450
[15:00:05] [INDICATORS] RSI=45.2, MACD=positive
[15:00:08] [NEWS] Fetching news...
[15:00:10] [NEWS] Fetched 12 articles
[15:00:11] [NEWS] Sentiment: 0.62 (Positive)
[15:00:15] [ML] LSTM: 0.78, RF: BUY(0.85), LR: 0.72
[15:00:16] [ML] ENSEMBLE: BUY (79.6%)
[15:00:17] [SIGNAL] Checking conditions...
[15:00:17] [SIGNAL] ML confidence too low for new trade (need >80% with open position)
[15:00:17] [SIGNAL] NO TRADE - Risk management
[15:00:18] [PORTFOLIO] Capital: $10,120 | Positions: 1/3 | Exposure: 25%
[15:00:18] [LOOP] Next check: 15:15:00
```

### Цикл #2 (15:15):
```
[15:15:00] [LOOP] Iteration #43
[15:15:01] [CHECK] Checking 1 active position
[15:15:01] [POSITION] BTC/USDT LONG: Entry=$95,000, Current=$97,850
[15:15:02] [CLOSE] 🎉 Take Profit reached! Closing position
[15:15:03] [TRADE] ✅ CLOSED: +$228 (+3.0%)
[15:15:05] [DATA] Fetching ETH/USDT data...
[15:15:06] [DATA] Price: $3,650
[15:15:08] [INDICATORS] RSI=32.1 (oversold!)
[15:15:12] [NEWS] Sentiment: 0.45 (Positive)
[15:15:17] [ML] ENSEMBLE: BUY (82.3%)
[15:15:18] [SIGNAL] ✅ ALL CONDITIONS MET
[15:15:19] [TRADE] 🎯 Opening LONG: ETH/USDT @ $3,650
[15:15:20] [TRADE] ✅ Order executed
[15:15:21] [PORTFOLIO] Capital: $10,348 | Positions: 1/3 | Exposure: 20%
```

---

## ⚙️ Настройки (что можно менять)

### В `.env`:
```env
# Интервал проверки
DEFAULT_TIMEFRAME=15m  # 1m, 5m, 15m, 1h

# Risk management
RISK_PER_TRADE=0.01  # 1% капитала на сделку
MAX_OPEN_POSITIONS=3
MAX_TOTAL_EXPOSURE=0.5  # 50% капитала

# ML пороги
ML_CONFIDENCE_THRESHOLD=0.7  # 70% уверенности
SENTIMENT_THRESHOLD=0.3  # Позитивный sentiment

# Новости
NEWS_UPDATE_INTERVAL_MINUTES=15  # Частота обновления
```

### В `config.yaml`:
```yaml
symbols:
  - BTC/USDT
  - ETH/USDT

risk:
  stop_loss_atr_multiplier: 2  # SL = ATR * 2
  take_profit_atr_multiplier: 3  # TP = ATR * 3
  max_hold_time_hours: 48  # Макс. время удержания

ml:
  ensemble_weights:
    lstm: 0.4  # 40% веса
    random_forest: 0.4
    logistic_regression: 0.2
```

---

## 🎯 Итоговая схема мониторинга

```
┌──────────────────────────────────────────────┐
│         КАК ПОНЯТЬ ЧТО БОТ РАБОТАЕТ         │
└──────────────────────────────────────────────┘

1. Dashboard (http://85.209.134.246)
   └─ Статус: "Running" ✅
   └─ Uptime: растет ⏱️
   └─ Логи: обновляются 📝

2. Системные логи (VPS)
   └─ journalctl -f | grep "LOOP"
   └─ Каждые 15 мин: Iteration #X ✅

3. Файловые логи
   └─ tail -f logs/dashboard.log
   └─ Видны: DATA, ML, NEWS, TRADE ✅

4. База данных
   └─ SELECT COUNT(*) FROM trades
   └─ Количество сделок растет 📊

5. Позиции на бирже
   └─ Зайти на Bybit/Binance
   └─ Проверить открытые ордера 💰
```

---

## ✅ Контрольный список "Бот работает нормально"

- ✅ Статус "Running" в dashboard
- ✅ Логи пишутся каждые 15 минут
- ✅ Видны [LOOP] Iteration #X
- ✅ Видны [DATA] Fetching... 
- ✅ Видны [ML] predictions
- ✅ Видны [NEWS] sentiment updates
- ✅ Portfolio metrics обновляются
- ✅ База данных пополняется (если были сделки)
- ✅ Нет повторяющихся [ERROR]
- ✅ Uptime растет

---

## 🚨 Признаки проблем

- ❌ Статус "Stopped"
- ❌ Логи не пишутся > 20 минут
- ❌ Повторяющиеся [ERROR] 
- ❌ [ERROR] Failed to fetch data
- ❌ [ERROR] Exchange API error
- ❌ [WARNING] Rate limit exceeded
- ❌ Uptime = 0 (служба упала)

---

## 🎉 Итог

Бот работает **автоматически по таймеру**, каждые N минут:
1. ✅ Анализирует рынок
2. ✅ Собирает новости
3. ✅ Делает ML предсказание  
4. ✅ Проверяет условия
5. ✅ Открывает/закрывает сделки
6. ✅ Всё логирует

**Отследить работу:**
- Dashboard: http://85.209.134.246
- Логи: `journalctl -u aibot-dashboard -f`
- БД: `sqlite3 data/trading.db`

**Бот НЕ ждет триггеров** - он работает периодически! 🤖⏰
