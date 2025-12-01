# 📖 API Documentation

## Overview

This document describes the internal APIs and interfaces used in AiCryptoBot.

---

## Core Modules

### 1. MarketData

**Location**: `src/data/market_data.py`

#### Methods

##### `fetch_ohlcv(symbol, timeframe, limit)`
Fetch OHLCV data from exchange.

**Parameters:**
- `symbol` (str): Trading pair (e.g., "BTC/USDT")
- `timeframe` (str): Candle timeframe (e.g., "15m")
- `limit` (int): Number of candles

**Returns:**
- `pd.DataFrame`: OHLCV data

**Example:**
```python
market_data = MarketData(config)
df = market_data.fetch_ohlcv("BTC/USDT", "15m", 1000)
```

##### `add_indicators(df)`
Add technical indicators to DataFrame.

**Parameters:**
- `df` (pd.DataFrame): OHLCV data

**Returns:**
- `pd.DataFrame`: Data with indicators

**Indicators Added:**
- RSI, ATR, SMA_50, SMA_200, MACD, BB, volume_sma_ratio

##### `create_ml_target(df, forward_bars=5, threshold=0.5)`
Create binary target for ML.

**Parameters:**
- `df` (pd.DataFrame): Data with indicators
- `forward_bars` (int): Lookahead period
- `threshold` (float): % threshold for "Up" class

**Returns:**
- `pd.DataFrame`: Data with "Target" column (0=Down, 1=Up)

---

### 2. MLPredictor

**Location**: `src/ml/predictor.py`

#### Methods

##### `train(X, y)`
Train the ML model.

**Parameters:**
- `X` (pd.DataFrame): Feature matrix
- `y` (pd.Series): Target labels

**Returns:**
- None (model saved internally)

**Example:**
```python
predictor = MLPredictor(config)
predictor.train(X_train, y_train)
```

##### `predict_single(features)`
Predict for single data point.

**Parameters:**
- `features` (pd.Series): Feature values

**Returns:**
- `tuple`: (prediction, confidence)
  - prediction (int): 0=Down, 1=Up
  - confidence (float): 0-1

**Example:**
```python
prediction, confidence = predictor.predict_single(latest_features)
if prediction == 1 and confidence > 0.6:
    # Generate BUY signal
```

##### `save_model(filepath)`
Save trained model to disk.

**Parameters:**
- `filepath` (str): Path to save model

**Example:**
```python
predictor.save_model("models/btc_model.pkl")
```

##### `load_model(filepath)`
Load model from disk.

**Parameters:**
- `filepath` (str): Path to model file

---

### 3. NewsAnalyzer

**Location**: `src/sentiment/news_analyzer.py`

#### Methods

##### `get_sentiment(symbol)`
Get aggregated sentiment for symbol.

**Parameters:**
- `symbol` (str): Crypto symbol (e.g., "BTC")

**Returns:**
- `dict`: 
```python
{
    "score": 0.25,      # -1 to 1
    "label": "positive", # positive/neutral/negative
    "count": 15         # Number of articles
}
```

**Example:**
```python
analyzer = NewsAnalyzer(config)
sentiment = analyzer.get_sentiment("BTC")
if sentiment["score"] > 0.1:
    # Positive sentiment
```

---

### 4. RiskManager

**Location**: `src/risk/risk_manager.py`

#### Methods

##### `calculate_position_size(price, atr, confidence)`
Calculate optimal position size.

**Parameters:**
- `price` (float): Current asset price
- `atr` (float): Average True Range
- `confidence` (float): ML confidence (0-1)

**Returns:**
- `dict`:
```python
{
    "quantity": 0.05,        # Amount to trade
    "position_size": 2000,   # USD value
    "stop_loss": 49500,      # SL price
    "take_profit": 51000     # TP price
}
```

##### `check_risk_limits()`
Check if risk limits are violated.

**Returns:**
- `dict`:
```python
{
    "can_trade": True,
    "reason": None,         # or reason for blocking
    "daily_pnl": -50.25,
    "total_drawdown": 2.5
}
```

---

### 5. TradeExecutor

**Location**: `src/trading/executor.py`

#### Methods

##### `execute_signal(signal)`
Execute trading signal.

**Parameters:**
- `signal` (dict):
```python
{
    "action": "buy",      # buy/sell
    "symbol": "BTC/USDT",
    "price": 50000,
    "quantity": 0.05,
    "stop_loss": 49500,
    "take_profit": 51000
}
```

**Returns:**
- `dict`: Order result from exchange

##### `close_position(position_id)`
Close open position.

**Parameters:**
- `position_id` (str): Position identifier

---

### 6. Backtester

**Location**: `src/backtesting/backtest.py`

#### Methods

##### `walk_forward_validation(train_size, test_size, total_periods)`
Run Walk-Forward backtest.

**Parameters:**
- `train_size` (int): Candles for training
- `test_size` (int): Candles for testing
- `total_periods` (int): Number of WF windows

**Returns:**
- `dict`: Aggregated results
```python
{
    "total_trades": 50,
    "win_rate": 52.5,
    "total_return": 8.3,
    "sharpe_ratio": 1.4,
    "max_drawdown": 12.5,
    "profit_factor": 1.8
}
```

---

## Configuration

**Location**: `config/settings.yaml`

### Structure

```yaml
trading:
  symbol: "BTC/USDT"
  timeframe: "15m"
  mode: "testnet"

risk_management:
  risk_per_trade: 1.0
  max_daily_drawdown: 5.0

ml:
  model_type: "random_forest"
  n_estimators: 100
  buy_threshold: 60
```

### Loading Config

```python
from src.utils.config import Config

config = Config("config/settings.yaml")
symbol = config.get("trading", "symbol")
```

---

## Database Schema

**Location**: `data/trading.db`

### Tables

#### `trades`
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    symbol TEXT,
    side TEXT,              -- buy/sell
    entry_price REAL,
    exit_price REAL,
    quantity REAL,
    pnl REAL,
    pnl_percent REAL,
    status TEXT,            -- open/closed
    stop_loss REAL,
    take_profit REAL
);
```

#### `events`
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    event_type TEXT,        -- trade/signal/error
    description TEXT,
    data JSON
);
```

---

## Error Handling

### Exception Classes

```python
class InsufficientFundsError(Exception):
    """Not enough balance"""
    pass

class APIConnectionError(Exception):
    """API unavailable"""
    pass

class InvalidSignalError(Exception):
    """Invalid trading signal"""
    pass
```

### Usage

```python
try:
    executor.execute_signal(signal)
except InsufficientFundsError:
    logger.error("Not enough balance")
except APIConnectionError:
    logger.error("Exchange API down")
```

---

## Logging

### Levels

- **DEBUG**: Detailed information
- **INFO**: General information
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical failures

### Example

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Bot started")
logger.warning("Low balance")
logger.error("API connection failed")
```

---

## Testing

### Run Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_predictor.py

# With coverage
pytest --cov=src tests/
```

### Mock API Calls

```python
from unittest.mock import Mock, patch

@patch('ccxt.bybit')
def test_fetch_ohlcv(mock_exchange):
    mock_exchange.return_value.fetch_ohlcv.return_value = mock_data
    # Test logic
```

---

## Webhooks (Future)

### Incoming Webhook

```bash
POST /api/signal
{
    "symbol": "BTC/USDT",
    "action": "buy",
    "price": 50000,
    "confidence": 0.75
}
```

### Response

```json
{
    "success": true,
    "order_id": "12345",
    "message": "Order placed"
}
```

---

## Rate Limits

### Bybit API

- **REST**: 120 requests/minute
- **WebSocket**: 100 subscriptions

### Handling

```python
import time

def rate_limited_call():
    time.sleep(0.5)  # 0.5s between calls
    return exchange.fetch_ohlcv(...)
```

---

## Performance Metrics

### Calculation

```python
def calculate_sharpe_ratio(returns, risk_free_rate=0):
    return (returns.mean() - risk_free_rate) / returns.std() * np.sqrt(252)

def calculate_max_drawdown(equity_curve):
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    return drawdown.min()
```

---

## Environment Variables

Required in `.env`:

```env
BYBIT_API_KEY=xxx
BYBIT_API_SECRET=xxx
BYBIT_TESTNET=true
CRYPTOPANIC_API_KEY=xxx
NEWS_API_KEY=xxx
```

---

## Troubleshooting

### Common Issues

1. **API Authentication Failed**
   - Check API keys in `.env`
   - Verify Testnet mode matches keys

2. **Model Not Trained**
   - Run `train_model.py` first
   - Check if model file exists

3. **Insufficient Data**
   - Increase `lookback_bars` in config
   - Check exchange data availability

---

For more information, see source code documentation.
