#!/usr/bin/env python3
"""
Train models using PUBLIC Binance API (no auth required)
Works from any location, no VPN needed!
"""

import ccxt
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def fetch_public_data(symbol='BTC/USDT', timeframe='1h', limit=2000):
    """Fetch OHLCV data from Binance PUBLIC API"""
    logger.info(f"📡 Connecting to Binance PUBLIC API...")
    
    # No API keys needed for public data!
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    
    logger.info(f"📊 Fetching {limit} {timeframe} candles for {symbol}...")
    bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    logger.info(f"✅ Fetched {len(df)} candles")
    logger.info(f"📅 From {df.index.min()} to {df.index.max()}")
    logger.info(f"💰 Price: ${df['close'].iloc[0]:.2f} → ${df['close'].iloc[-1]:.2f}")
    
    return df

def add_indicators(df):
    """Add technical indicators"""
    logger.info("🔧 Adding technical indicators...")
    
    # SMA
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()
    
    # EMA
    df['ema_12'] = df['close'].ewm(span=12).mean()
    df['ema_26'] = df['close'].ewm(span=26).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # Volume
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_sma_ratio'] = df['volume'] / df['volume_sma']
    
    logger.info(f"✅ Added {len(df.columns)} features")
    return df

def create_target(df, future_bars=5, threshold=0.005):
    """Create ML target: will price go up by threshold% in future_bars?"""
    df['future_close'] = df['close'].shift(-future_bars)
    df['price_change'] = (df['future_close'] - df['close']) / df['close']
    df['target'] = (df['price_change'] > threshold).astype(int)
    logger.info(f"🎯 Target created: {df['target'].sum()} UP, {len(df) - df['target'].sum()} DOWN")
    return df

def train_model(df):
    """Train RandomForest model"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    
    feature_cols = ['open', 'high', 'low', 'close', 'volume',
                    'sma_20', 'sma_50', 'ema_12', 'ema_26',
                    'rsi', 'macd', 'macd_signal', 'macd_hist',
                    'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
                    'atr', 'volume_sma_ratio']
    
    df_clean = df.dropna()
    logger.info(f"📊 Training data: {len(df_clean)} samples")
    
    X = df_clean[feature_cols]
    y = df_clean['target']
    
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    logger.info("🤖 Training RandomForest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    
    model.fit(X_train, y_train)
    
    train_score = model.score(X_train, y_train)
    val_score = model.score(X_val, y_val)
    
    logger.info(f"✅ Training accuracy: {train_score:.2%}")
    logger.info(f"✅ Validation accuracy: {val_score:.2%}")
    
    # Feature importance
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info("📊 Top 5 features:")
    for idx, row in importances.head(5).iterrows():
        logger.info(f"   {row['feature']}: {row['importance']:.4f}")
    
    return model, feature_cols

def main():
    """Main training pipeline"""
    print("\n" + "="*60)
    print("🚀 ML TRAINING WITH PUBLIC BINANCE API")
    print("="*60 + "\n")
    
    # Fetch data
    df = fetch_public_data(symbol='BTC/USDT', timeframe='1h', limit=2000)
    
    # Add indicators
    df = add_indicators(df)
    
    # Create target
    df = create_target(df, future_bars=5)
    
    # Train model
    model, feature_cols = train_model(df)
    
    # Save model
    models_dir = Path('models')
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / 'random_forest_model.joblib'
    joblib.dump({
        'model': model,
        'feature_columns': feature_cols,
        'trained_at': pd.Timestamp.now().isoformat()
    }, model_path)
    
    logger.info(f"💾 Model saved to {model_path}")
    
    print("\n" + "="*60)
    print("✅ TRAINING COMPLETED!")
    print("="*60)
    print("\n📝 Next step: Run bot in PAPER TRADING mode")
    print("   python main.py --mode paper --web-dashboard\n")

if __name__ == '__main__':
    main()
