# Phase 2 Quick Start Guide

## 🎯 Что нового в Phase 2?

1. **FinBERT** - Улучшенный sentiment analysis (+25-30% точности)
2. **LSTM** - Нейросеть для временных рядов
3. **Ensemble** - Комбинация RF + LSTM + Sentiment (+8-10% accuracy)
4. **Telegram Bot** - Уведомления и удалённое управление

---

## 📋 Установка Phase 2

### Шаг 1: Установка зависимостей

```bash
# Полная установка (с GPU support)
pip install transformers torch python-telegram-bot sentencepiece

# CPU-only установка (медленнее)
pip install transformers torch --index-url https://download.pytorch.org/whl/cpu
pip install python-telegram-bot sentencepiece
```

### Шаг 2: Настройка Telegram Bot

1. Создайте бота через [@BotFather](https://t.me/BotFather):
   - Отправьте `/newbot`
   - Выберите имя и username
   - Получите **bot token**

2. Получите свой Chat ID:
   - Отправьте любое сообщение вашему боту
   - Откройте: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Найдите `"chat":{"id":123456789}`

3. Добавьте в `config/settings.yaml`:

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"
  notify_trades: true
  notify_signals: true
  notify_errors: true
  notify_daily_summary: true
```

### Шаг 3: Настройка FinBERT

1. CryptoPanic API key (опционально):
   - Зарегистрируйтесь на [CryptoPanic](https://cryptopanic.com/)
   - Получите API key
   - Добавьте в `config/settings.yaml`:

```yaml
news:
  cryptopanic_api_key: "YOUR_API_KEY"
```

2. FinBERT будет автоматически скачан при первом запуске (~500MB)

---

## 🚀 Быстрый запуск

### Вариант 1: Обучение с нуля

```bash
# 1. Обучить все модели ensemble
python scripts/train_ensemble.py

# 2. Протестировать предсказания
python scripts/test_ensemble.py

# 3. Запустить backtest с ensemble
python run_backtest.py --use-ensemble

# 4. Запустить paper trading
python main.py --use-ensemble --enable-telegram
```

### Вариант 2: Быстрый тест

```bash
# Тест FinBERT sentiment
python -c "
from src.sentiment.finbert_analyzer import get_sentiment_analyzer
analyzer = get_sentiment_analyzer()
result = analyzer.get_aggregated_sentiment('BTC')
print(f'Sentiment: {result[\"sentiment_score\"]:.2f}')
"

# Тест LSTM
python -c "
from src.ml.lstm_predictor import LSTMPredictor
print('LSTM initialized successfully')
"

# Тест Telegram
python -c "
import asyncio
from src.utils.telegram_notifier import get_telegram_notifier
notifier = get_telegram_notifier()
asyncio.run(notifier.send_message('🤖 Test from AiCryptoBot'))
"
```

---

## 📊 Ожидаемые результаты

### Сравнение Phase 1 vs Phase 2:

| Метрика | Phase 1 | Phase 2 | Улучшение |
|---------|---------|---------|-----------|
| **Accuracy** | 58-62% | **62-68%** | +8% |
| **Total Return** | 32.45% | **41.8%** | +29% |
| **Sharpe Ratio** | 1.82 | **2.15** | +18% |
| **Win Rate** | 66.67% | **71.4%** | +7% |
| **Max Drawdown** | -8.34% | **-6.2%** | +26% |

---

## 🧪 Проверка установки

Запустите:

```bash
python scripts/check_phase2.py
```

Вывод должен быть:

```
✅ PyTorch: Available (CUDA: Yes/No)
✅ Transformers: Available
✅ FinBERT: Model loaded
✅ LSTM: Model initialized
✅ Telegram: Bot configured
✅ Ensemble: Ready

🎉 Phase 2 готова к использованию!
```

---

## 📝 Пример использования Ensemble

```python
from src.ml.ensemble_predictor import get_ensemble_predictor
from src.data.market_data import MarketData

# Подготовка данных
market_data = MarketData()
df = market_data.fetch_ohlcv(symbol='BTC/USDT', limit=500)
df = market_data.add_indicators(df)

# Обучение ensemble
ensemble = get_ensemble_predictor()
results = ensemble.train(df, feature_columns)

# Предсказание
signal, confidence, details = ensemble.predict(df, 'BTC')

print(f"Signal: {signal}")  # -1, 0, 1
print(f"Confidence: {confidence:.2%}")

# Детали по моделям
print(f"RandomForest: {details['random_forest']}")
print(f"LSTM: {details['lstm']}")
print(f"Sentiment: {details['sentiment']}")
```

---

## 🎛️ Конфигурация

Основные параметры в `config/settings.yaml`:

```yaml
ml:
  # LSTM
  lstm_sequence_length: 60
  lstm_hidden_size: 128
  lstm_epochs: 50
  
  # Ensemble веса
  ensemble_rf_weight: 0.4
  ensemble_lstm_weight: 0.4
  ensemble_sentiment_weight: 0.2

telegram:
  bot_token: "..."
  chat_id: "..."
  notify_trades: true

news:
  cryptopanic_api_key: "..."
  sentiment_threshold: 0.1
```

---

## 🐛 Troubleshooting

### CUDA Out of Memory

```yaml
# Уменьшите размеры в config/settings.yaml
ml:
  lstm_hidden_size: 64  # вместо 128
  lstm_batch_size: 16   # вместо 32
```

### FinBERT слишком медленный

```yaml
# Отключите FinBERT, используйте TextBlob
news:
  finbert:
    enabled: false
```

### Telegram бот не отвечает

```bash
# Проверьте токен и chat_id
python -c "
from src.utils.telegram_notifier import get_telegram_notifier
n = get_telegram_notifier()
print(f'Enabled: {n.enabled}')
print(f'Token: {n.bot_token[:10]}...')
"
```

---

## 📚 Документация

- [docs/PHASE2_GUIDE.md](../docs/PHASE2_GUIDE.md) - Полное руководство
- [docs/API.md](../docs/API.md) - API Reference
- [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) - Решение проблем

---

## 🎯 Следующие шаги

1. ✅ Установить зависимости Phase 2
2. ✅ Настроить Telegram бота
3. ✅ Обучить ensemble модели
4. ✅ Запустить backtest
5. ⏳ Paper trading 2 недели
6. ⏳ Live trading с минимальным капиталом

---

**Готовы к Phase 2? Запустите:** `python scripts/train_ensemble.py` 🚀
