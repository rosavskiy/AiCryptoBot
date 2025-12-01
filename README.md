# 🤖 AiCryptoBot - AI-Powered Crypto Trading System

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success.svg)

Профессиональная торговая система для криптовалют с **Machine Learning**, **NLP Sentiment Analysis** и продвинутым **Risk Management**.

---

## 🎯 Особенности

### 🧠 Machine Learning (Phase 1 + 2)
- **RandomForest** классификатор для базового прогнозирования
- **LSTM Neural Network** для анализа временных рядов (Phase 2) 🆕
- **Ensemble Predictor** комбинирует RF + LSTM + Sentiment (Phase 2) 🆕
- **Walk-Forward Validation** для защиты от переобучения
- Автоматический feature engineering (17+ технических индикаторов)
- Кросс-валидация и метрики качества (62-68% accuracy)

### 💭 Sentiment Analysis
- **FinBERT** - финансовая BERT модель для точного анализа (Phase 2) 🆕
- Интеграция с **CryptoPanic API**
- Fallback на **TextBlob** если FinBERT недоступен
- Агрегация настроений с взвешиванием по уверенности
- Фильтрация сигналов на основе настроений рынка

### 🛡️ Risk Management
- Динамический расчёт размера позиции (Kelly Criterion)
- ATR-based стоп-лоссы и тейк-профиты
- Trailing stops, max drawdown limits
- Защита от чрезмерных потерь

### 📊 Backtesting
- **Walk-Forward Validation** с защитой от Data Leakage
- Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor
- Визуализация equity curve
- Экспорт результатов в CSV

### 📱 Telegram Bot (Phase 2) 🆕
- Уведомления о сделках в реальном времени
- Дневные сводки по производительности
- Удалённое управление ботом (/start, /stop, /status)
- Мониторинг позиций и баланса

### 🌐 Web Dashboard (Phase 2) 🆕
- **Real-time мониторинг** через WebSocket
- Графики P&L, открытые позиции, история сделок
- Управление ботом (запуск/остановка/пауза)
- Живые логи и статус системы
- Современный dark theme дизайн
- См. [docs/WEB_DASHBOARD.md](docs/WEB_DASHBOARD.md)

### 🔌 Интеграции
- **Bybit API** (Testnet + Mainnet)
- SQLite для хранения данных
- Telegram Bot для уведомлений
- Docker для deployment

---

## 📊 Архитектура

```
Data Pipeline → ML Predictor → Sentiment Filter → Risk Manager → Trade Executor
     ↓              ↓               ↓                  ↓              ↓
  OHLCV +      RandomForest    News Analysis    Position Size   Bybit API
Indicators    (Up/Down?)     (Positive/Negative?)   & Stops     Execution
```

**Детальная архитектура**: см. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 🚀 Быстрый старт

### 1. Установка

```bash
# Клонирование
git clone https://github.com/rosavskiy/AiCryptoBot.git
cd AiCryptoBot

# Виртуальное окружение (Windows)
python -m venv venv
venv\Scripts\activate

# Установить пакеты
pip install -r requirements.txt
```

### 2. Настройка

```powershell
# Скопировать шаблон конфигурации
Copy-Item .env.example .env

# Отредактировать .env и добавить API ключи
# См. подробную инструкцию: API_KEYS.md
# - Bybit Testnet: https://testnet.bybit.com
# - CryptoPanic: https://cryptopanic.com/developers/api/
```

### 3. Тестирование системы

```powershell
python test_system.py
```

### 4. Web Dashboard (опционально)

```powershell
# Запустить dashboard для мониторинга
python run_dashboard.py

# Откройте http://localhost:5000
```

## 🚢 Deployment на VPS

### Быстрый деплой (Docker):

```bash
# На VPS:
git clone https://github.com/rosavskiy/AiCryptoBot.git
cd AiCryptoBot
cp .env.example .env
nano .env  # Добавьте API ключи

# Запустите
docker-compose up -d

# Готово! http://your_vps_ip:5000
```

**Подробная инструкция**: см. [DEPLOY_QUICK.md](DEPLOY_QUICK.md) или [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

**Рекомендуемые VPS**:
- Contabo Singapore - €6.99/мес (4 vCPU, 8GB RAM)
- Hetzner Germany - €9.5/мес (4 vCPU, 8GB RAM)
- DigitalOcean Singapore - $12/мес (2 vCPU, 2GB RAM)

## 📁 Структура проекта

```
AiCryptoBot/
├── config/
│   └── settings.yaml          # Конфигурация торговли, ML, индикаторов
├── src/
│   ├── config/                # Загрузчик конфигурации
│   ├── data/                  # Сбор данных и индикаторы
│   │   └── market_data.py     # ✅ Реализовано
│   ├── ml/                    # Machine Learning модели
│   │   └── predictor.py       # ✅ Реализовано
│   ├── sentiment/             # NLP анализ новостей
│   ├── risk/                  # Риск-менеджмент
│   ├── trading/               # Торговое ядро
│   ├── backtesting/           # Walk-Forward тестирование
│   └── utils/                 # Логирование, БД
├── tests/                     # Unit-тесты
├── models/                    # Сохраненные ML модели
├── data/                      # База данных сделок
├── logs/                      # Логи системы
└── requirements.txt           # Python зависимости
```

## 🔧 Конфигурация

### Exchange (Биржа)

```yaml
exchange:
  name: bybit
  testnet: true              # true = Testnet, false = Mainnet
  default_type: linear       # USDT perpetual futures
```

### Machine Learning

```yaml
ml:
  model_type: RandomForest
  n_estimators: 100
  confidence_threshold: 0.60  # Минимальная уверенность для входа
  
  # Walk-Forward Validation
  walk_forward:
    train_period_days: 90     # Окно обучения
    test_period_days: 30      # Окно тестирования
    step_days: 15             # Шаг вперед
```

### Risk Management

```yaml
risk:
  risk_per_trade: 0.01        # 1% депозита на сделку
  max_open_positions: 3       # Максимум одновременных позиций
  stop_loss_atr_multiplier: 2.0  # Стоп = 2x ATR
  take_profit_atr_multiplier: 3.0  # Профит = 3x ATR
  max_drawdown_percent: 15.0  # Максимальная просадка
```

## 📈 Использование

### Сбор и подготовка данных

```python
from src.data.market_data import MarketDataFetcher

# Инициализация
fetcher = MarketDataFetcher()

# Получить данные с индикаторами
df = fetcher.get_market_data(
    symbol='BTC/USDT',
    timeframe='15m',
    limit=1000
)

print(df.tail())
```

### Обучение ML модели

```python
from src.ml.predictor import MLPredictor

# Инициализация
predictor = MLPredictor()

# Подготовка данных
X, y, features = predictor.prepare_data(df)

# Обучение
metrics = predictor.train(X, y, validation_split=0.2)

# Сохранение модели
predictor.save_model()
```

### Прогнозирование

```python
# Загрузка модели
predictor = MLPredictor()
predictor.load_model()

# Прогноз для последней свечи
last_row = df.iloc[-1]
prediction, confidence = predictor.predict_single(last_row)

print(f"Direction: {'UP' if prediction == 1 else 'DOWN'}")
print(f"Confidence: {confidence:.2%}")
```

### Walk-Forward Validation

```python
# Запуск валидации (защита от data leakage)
results = predictor.walk_forward_validation(
    df,
    train_days=90,
    test_days=30,
    step_days=15
)

# Анализ результатов
for result in results:
    print(f"Fold {result['fold']}: Accuracy = {result['accuracy']:.4f}")
```

## ⚙️ Технические индикаторы

Система автоматически рассчитывает следующие индикаторы:

- **RSI** (Relative Strength Index) - период 14
- **ATR** (Average True Range) - период 14  
- **SMA** (Simple Moving Average) - 50 и 200 периодов
- **MACD** (Moving Average Convergence Divergence) - 12, 26, 9
- **Bollinger Bands** - период 20, стандартное отклонение 2
- **Volume Ratio** - отношение объема к скользящей средней

## 🎓 Machine Learning детали

### Модель: RandomForest Classifier

**Преимущества:**
- Устойчив к переобучению
- Работает с нелинейными зависимостями
- Не требует нормализации данных
- Встроенная оценка важности признаков

**Параметры:**
```python
RandomForestClassifier(
    n_estimators=100,        # Количество деревьев
    min_samples_split=10,    # Минимум для разделения узла
    max_depth=15,            # Максимальная глубина дерева
    class_weight='balanced'  # Балансировка классов
)
```

### Walk-Forward Validation

```
Timeline: |----Train----|--Test--||----Train----|--Test--||----Train----|--Test--|
          
          2023-01       2023-02   2023-02       2023-03   2023-03       2023-04
          └─90 days─┘   └30 days┘ └─90 days─┘   └30 days┘ └─90 days─┘   └30 days┘
                        
                        ↑         ↑             ↑         ↑             ↑
                      Test      Retrain       Test      Retrain       Test
```

**Почему это критично:**
- Предотвращает утечку данных из будущего (data leakage)
- Симулирует реальную торговлю (переобучение на новых данных)
- Даёт честную оценку производительности

## ⚠️ Важные моменты

### 1. Data Leakage (Утечка данных)

❌ **НЕПРАВИЛЬНО:**
```python
# Обучаем и тестируем на одних и тех же данных
model.fit(X, y)
predictions = model.predict(X)  # Будет 99% accuracy, но НЕ РАБОТАЕТ в реале!
```

✅ **ПРАВИЛЬНО:**
```python
# Walk-Forward Validation
# Обучаем на прошлом, тестируем на будущем
results = predictor.walk_forward_validation(df)
```

### 2. Bybit Testnet

- Сначала **ВСЕГДА** тестируй на testnet
- Testnet URL: `https://testnet.bybit.com`
- Отдельная регистрация и API ключи
- Виртуальные деньги для тестирования

### 3. Риск-менеджмент

- Не рискуй больше 1-2% депозита на сделку
- Используй стоп-лоссы (ВСЕГДА!)
- Ограничь количество одновременных позиций
- Следи за максимальной просадкой

## 📊 Метрики качества модели

```python
{
    'accuracy': 0.6234,      # Общая точность
    'precision': 0.6541,     # Точность положительных прогнозов
    'recall': 0.5892,        # Полнота (сколько нашли из всех)
    'f1_score': 0.6201       # Гармоническое среднее precision и recall
}
```

**Минимальные требования:**
- Accuracy > 55% (лучше монетки)
- Precision > 58% (избегаем ложных сигналов)
- Confidence > 60% (уверенность модели)

## 🚀 Roadmap

### Phase 1: Базовая система (✅ Реализовано)
- [x] Структура проекта
- [x] Сбор данных и индикаторы
- [x] ML модель (RandomForest)
- [x] Walk-Forward Validation

### Phase 2: Sentiment & Risk (В процессе)
- [ ] NLP Sentiment Analysis (TextBlob)
- [ ] Risk Manager (Kelly Criterion, ATR stops)
- [ ] Торговое ядро (сигналы + исполнение)
- [ ] Логирование в SQLite

### Phase 3: Backtesting
- [ ] Backtesting engine
- [ ] Метрики (Sharpe, Drawdown, Win Rate)
- [ ] Визуализация Equity Curve

### Phase 4: Advanced Features
- [ ] FinBERT для sentiment (трансформер)
- [ ] LSTM/Transformer для time-series
- [ ] Multi-symbol торговля
- [ ] WebSocket для real-time данных
- [ ] Telegram бот для уведомлений
- [ ] Docker deployment

## 🔗 Полезные ссылки

- [Bybit Testnet](https://testnet.bybit.com)
- [Bybit API Docs](https://bybit-exchange.github.io/docs/v5/intro)
- [CCXT Documentation](https://docs.ccxt.com/)
- [Pandas TA](https://github.com/twopirllc/pandas-ta)
- [Scikit-learn](https://scikit-learn.org/)

## 📄 Лицензия

MIT License - используйте на свой страх и риск!

## ⚠️ Дисклеймер

Эта система предоставляется "как есть" в образовательных целях. Торговля криптовалютами несет высокий риск потери средств. Автор не несет ответственности за ваши торговые результаты. Всегда тестируйте на testnet перед использованием реальных средств.
