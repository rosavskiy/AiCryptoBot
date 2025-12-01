# Запуск всех тестов

**Единичные тесты по модулям:**

```bash
# Тесты MarketData
python -m pytest tests/test_market_data.py -v

# Тесты MLPredictor
python -m pytest tests/test_predictor.py -v

# Тесты NewsAnalyzer
python -m pytest tests/test_news_analyzer.py -v

# Тесты RiskManager
python -m pytest tests/test_risk_manager.py -v

# Тесты TradeExecutor
python -m pytest tests/test_executor.py -v

# Тесты Backtester
python -m pytest tests/test_backtest.py -v

# Интеграционные тесты
python -m pytest tests/test_integration.py -v
```

**Запуск всех тестов сразу:**

```bash
python -m pytest tests/ -v
```

**С покрытием кода:**

```bash
python -m pytest tests/ --cov=src --cov-report=html
```

**Только быстрые тесты (без интеграционных):**

```bash
python -m pytest tests/ -v -m "not slow"
```

**С подробным выводом и остановкой на первой ошибке:**

```bash
python -m pytest tests/ -vv -x
```

## Использование unittest

Альтернативно, можно использовать стандартный unittest:

```bash
# Все тесты
python -m unittest discover tests/

# Конкретный модуль
python -m unittest tests.test_market_data

# Конкретный тест-кейс
python -m unittest tests.test_market_data.TestMarketData

# Конкретный тест
python -m unittest tests.test_market_data.TestMarketData.test_initialization
```

## Требования

```bash
pip install pytest pytest-cov pytest-mock
```

Или используйте встроенный unittest без дополнительных зависимостей.
