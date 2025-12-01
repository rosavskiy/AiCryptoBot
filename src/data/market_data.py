"""
Market Data Module
==================
Fetches OHLCV data from Bybit and generates technical indicators.
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Optional, List
from datetime import datetime
import logging

from ..config.config_loader import get_config


logger = logging.getLogger(__name__)


class MarketDataFetcher:
    """Fetches and processes market data from exchange"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = None):
        """
        Initialize market data fetcher
        
        Args:
            api_key: Exchange API key (optional for public data)
            api_secret: Exchange API secret (optional for public data)
            testnet: Use testnet if True, mainnet if False (reads from config if None)
        """
        config = get_config()
        
        # Get exchange name from config
        exchange_name = config.get('exchange', 'name', default='bybit')
        
        # Get credentials
        if api_key is None or api_secret is None:
            creds = config.get_api_credentials()
            api_key = creds['api_key']
            api_secret = creds['api_secret']
            if testnet is None:
                testnet = creds['testnet']
        
        # Initialize exchange dynamically
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': config.get('exchange', 'default_type', default='linear')
            }
        })
        
        # Enable testnet mode
        if testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info(f"[TESTNET] {exchange_name.upper()} TESTNET mode enabled")
        else:
            logger.warning(f"[WARNING] {exchange_name.upper()} MAINNET mode - trading with real money!")
        
        self.config = config
        self.testnet = testnet
        self.exchange_name = exchange_name
    
    def fetch_ohlcv(
        self,
        symbol: str = None,
        timeframe: str = None,
        limit: int = None
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from exchange
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '15m', '1h')
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with OHLCV data
        """
        # Use defaults from config
        if symbol is None:
            symbol = self.config.get('symbols', default=['BTC/USDT'])[0]
        if timeframe is None:
            timeframe = self.config.get('timeframe', 'trading', default='15m')
        if limit is None:
            limit = self.config.get('timeframe', 'lookback_bars', default=1000)
        
        try:
            logger.info(f"[DATA] Fetching {limit} bars of {symbol} ({timeframe})...")
            bars = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(
                bars,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Remove any duplicate columns (safety check)
            df = df.loc[:, ~df.columns.duplicated()]
            
            logger.info(f"[SUCCESS] Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
            return df
            
        except Exception as e:
            logger.error(f"[ERROR] Error fetching data: {e}")
            raise
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators to OHLCV dataframe
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with added technical indicators
        """
        df = df.copy()
        config = self.config.get('indicators', default={})
        
        # RSI (Relative Strength Index)
        rsi_period = config.get('rsi', {}).get('period', 14)
        df['RSI'] = ta.rsi(df['close'], length=rsi_period)
        
        # ATR (Average True Range) - for volatility
        atr_period = config.get('atr', {}).get('period', 14)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=atr_period)
        
        # SMA (Simple Moving Averages)
        sma_fast = config.get('sma', {}).get('fast', 50)
        sma_slow = config.get('sma', {}).get('slow', 200)
        df['SMA_50'] = ta.sma(df['close'], length=sma_fast)
        df['SMA_200'] = ta.sma(df['close'], length=sma_slow)
        
        # MACD (Moving Average Convergence Divergence)
        macd_config = config.get('macd', {})
        macd = ta.macd(
            df['close'],
            fast=macd_config.get('fast', 12),
            slow=macd_config.get('slow', 26),
            signal=macd_config.get('signal', 9)
        )
        if macd is not None:
            df['MACD'] = macd['MACD_12_26_9']
            df['MACD_signal'] = macd['MACDs_12_26_9']
            df['MACD_hist'] = macd['MACDh_12_26_9']
        
        # Bollinger Bands
        bb_config = config.get('bollinger', {})
        bb_period = bb_config.get('period', 20)
        bb_std = bb_config.get('std', 2)
        bbands = ta.bbands(
            df['close'],
            length=bb_period,
            std=bb_std
        )
        if bbands is not None and len(bbands.columns) >= 3:
            # pandas_ta может возвращать разные форматы имен колонок
            cols = bbands.columns.tolist()
            df['BB_lower'] = bbands.iloc[:, 0]  # Первая колонка - нижняя граница
            df['BB_middle'] = bbands.iloc[:, 1]  # Средняя
            df['BB_upper'] = bbands.iloc[:, 2]   # Верхняя граница
        
        # Volume features
        df['volume_sma'] = ta.sma(df['volume'], length=20)
        df['volume_sma_ratio'] = df['volume'] / df['volume_sma']
        
        # Price momentum
        df['momentum'] = df['close'].pct_change(periods=10)
        
        # Remove any duplicate columns that might have been added by indicators
        df = df.loc[:, ~df.columns.duplicated()]
        
        logger.info(f"[SUCCESS] Added {len(df.columns) - 5} technical indicators")
        return df
    
    def create_ml_target(
        self,
        df: pd.DataFrame,
        method: str = 'binary',
        forward_bars: int = 1,
        threshold: float = 0.001
    ) -> pd.DataFrame:
        """
        Create target variable for ML prediction
        
        Args:
            df: DataFrame with price data
            method: 'binary' (up/down) or 'continuous' (% change)
            forward_bars: How many bars ahead to predict
            threshold: Minimum price change to consider as signal (for binary)
        
        Returns:
            DataFrame with 'Target' column added
        """
        df = df.copy()
        
        if method == 'binary':
            # Binary classification: 1 if price goes up, 0 if down
            future_return = df['close'].shift(-forward_bars) / df['close'] - 1
            df['Target'] = (future_return > threshold).astype(int)
            
            # Count distribution
            target_counts = df['Target'].value_counts()
            logger.info(f"[DATA] Target distribution: {target_counts.to_dict()}")
            
        elif method == 'continuous':
            # Regression: predict actual % change
            df['Target'] = (df['close'].shift(-forward_bars) / df['close'] - 1) * 100
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare final feature set for ML
        
        Args:
            df: DataFrame with indicators
        
        Returns:
            Clean DataFrame ready for ML
        """
        # Get feature list from config
        feature_list = self.config.get('ml', 'features', default=[
            'RSI', 'ATR', 'volume', 'SMA_50', 'SMA_200',
            'MACD', 'MACD_signal', 'BB_upper', 'BB_lower', 'volume_sma_ratio'
        ])
        
        # Build required columns starting with OHLCV
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        
        # Add features from config, avoiding duplicates
        for feat in feature_list:
            if feat not in required_cols:
                required_cols.append(feat)
        
        # Add target if exists
        if 'Target' in df.columns:
            required_cols.append('Target')
        
        # Remove duplicates from columns
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Filter existing columns
        available_cols = [col for col in required_cols if col in df.columns]
        df_clean = df[available_cols].copy()
        
        # Drop rows with NaN (from indicator calculation)
        rows_before = len(df_clean)
        df_clean.dropna(inplace=True)
        rows_after = len(df_clean)
        
        if rows_before > rows_after:
            logger.info(f"[CLEAN] Dropped {rows_before - rows_after} rows with NaN values")
        
        return df_clean
    
    def get_market_data(
        self,
        symbol: str = None,
        timeframe: str = None,
        limit: int = None,
        with_target: bool = True
    ) -> pd.DataFrame:
        """
        Complete pipeline: fetch data, add indicators, create target
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of bars
            with_target: Create target variable for ML
        
        Returns:
            Ready-to-use DataFrame for ML
        """
        # Fetch OHLCV
        df = self.fetch_ohlcv(symbol, timeframe, limit)
        
        # Add technical indicators
        df = self.add_technical_indicators(df)
        
        # Create target for ML
        if with_target:
            df = self.create_ml_target(df)
        
        # Prepare final features
        df = self.prepare_features(df)
        
        logger.info(f"[SUCCESS] Market data ready: {len(df)} rows, {len(df.columns)} columns")
        return df
    
    def get_current_price(self, symbol: str = None) -> float:
        """Get current market price"""
        if symbol is None:
            symbol = self.config.get('symbols', default=['BTC/USDT'])[0]
        
        ticker = self.exchange.fetch_ticker(symbol)
        return ticker['last']
    
    def get_account_balance(self) -> dict:
        """Get account balance (requires API keys)"""
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"[ERROR] Error fetching balance: {e}")
            return {}


def main():
    """Test market data fetcher"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize fetcher
    fetcher = MarketDataFetcher()
    
    # Fetch and process data
    df = fetcher.get_market_data(symbol='BTC/USDT', timeframe='15m', limit=500)
    
    print("\n" + "="*80)
    print("📊 MARKET DATA SAMPLE")
    print("="*80)
    print(df.tail(10))
    print("\n" + "="*80)
    print("📈 DATA STATISTICS")
    print("="*80)
    print(df.describe())
    
    # Get current price
    price = fetcher.get_current_price('BTC/USDT')
    print(f"\n💰 Current BTC/USDT price: ${price:,.2f}")


if __name__ == "__main__":
    main()
