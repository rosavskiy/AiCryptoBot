"""
Unit тесты для модуля market_data.py
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.market_data import MarketData


class TestMarketData(unittest.TestCase):
    """Тесты для класса MarketData"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.config = {
            'exchange': {'name': 'bybit', 'testnet': True},
            'symbols': ['BTC/USDT'],
            'timeframe': '1h',
            'indicators': {
                'sma_periods': [20, 50],
                'ema_periods': [12, 26],
                'rsi_period': 14,
                'macd': {'fast': 12, 'slow': 26, 'signal': 9},
                'bollinger': {'period': 20, 'std': 2},
                'atr_period': 14
            }
        }
        self.market_data = MarketData(self.config)
    
    @patch('ccxt.bybit')
    def test_initialization(self, mock_bybit):
        """Тест инициализации класса"""
        self.assertIsNotNone(self.market_data.exchange)
        self.assertEqual(self.market_data.symbol, 'BTC/USDT')
        self.assertEqual(self.market_data.timeframe, '1h')
    
    def test_add_indicators_with_valid_data(self):
        """Тест добавления индикаторов с валидными данными"""
        # Создаём тестовый датафрейм
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(40000, 45000, 100),
            'high': np.random.uniform(45000, 46000, 100),
            'low': np.random.uniform(39000, 40000, 100),
            'close': np.random.uniform(40000, 45000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })
        
        result = self.market_data.add_indicators(df)
        
        # Проверяем наличие индикаторов
        self.assertIn('sma_20', result.columns)
        self.assertIn('sma_50', result.columns)
        self.assertIn('ema_12', result.columns)
        self.assertIn('rsi', result.columns)
        self.assertIn('macd', result.columns)
        self.assertIn('bb_upper', result.columns)
        self.assertIn('atr', result.columns)
        
        # Проверяем, что индикаторы не содержат NaN после прогрева
        warmup = 60
        self.assertFalse(result.iloc[warmup:]['sma_20'].isna().any())
        self.assertFalse(result.iloc[warmup:]['rsi'].isna().any())
    
    def test_add_indicators_with_insufficient_data(self):
        """Тест добавления индикаторов с недостаточным количеством данных"""
        # Создаём датафрейм с малым количеством строк
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='1h'),
            'open': [40000] * 10,
            'high': [45000] * 10,
            'low': [39000] * 10,
            'close': [42000] * 10,
            'volume': [100] * 10
        })
        
        result = self.market_data.add_indicators(df)
        
        # Индикаторы должны быть добавлены, но содержать NaN
        self.assertIn('sma_50', result.columns)
        self.assertTrue(result['sma_50'].isna().all())
    
    def test_create_ml_target(self):
        """Тест создания таргета для ML"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        df = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.uniform(40000, 45000, 100)
        })
        
        result = self.market_data.create_ml_target(df, future_bars=5)
        
        self.assertIn('target', result.columns)
        self.assertIn('future_return', result.columns)
        
        # Проверяем, что последние future_bars строк имеют NaN в таргете
        self.assertTrue(result['target'].iloc[-5:].isna().all())
        
        # Проверяем значения таргета (должны быть -1, 0, 1)
        valid_targets = result['target'].dropna().unique()
        self.assertTrue(all(t in [-1, 0, 1] for t in valid_targets))
    
    @patch('ccxt.bybit')
    def test_fetch_ohlcv_success(self, mock_bybit):
        """Тест успешного получения OHLCV данных"""
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1704067200000, 42000, 43000, 41000, 42500, 100],
            [1704070800000, 42500, 43500, 42000, 43000, 150],
            [1704074400000, 43000, 44000, 42500, 43500, 200],
        ]
        mock_bybit.return_value = mock_exchange
        
        md = MarketData(self.config)
        md.exchange = mock_exchange
        
        df = md.fetch_ohlcv(limit=3)
        
        self.assertEqual(len(df), 3)
        self.assertIn('open', df.columns)
        self.assertIn('close', df.columns)
        self.assertIn('volume', df.columns)
        self.assertEqual(df.iloc[0]['open'], 42000)
    
    @patch('ccxt.bybit')
    def test_fetch_ohlcv_api_error(self, mock_bybit):
        """Тест обработки ошибки API при получении OHLCV"""
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.side_effect = Exception("API Error")
        mock_bybit.return_value = mock_exchange
        
        md = MarketData(self.config)
        md.exchange = mock_exchange
        
        df = md.fetch_ohlcv(limit=100)
        
        # При ошибке должен вернуться пустой датафрейм
        self.assertTrue(df.empty)
    
    def test_indicator_ranges(self):
        """Тест корректности диапазонов индикаторов"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(40000, 45000, 100),
            'high': np.random.uniform(45000, 46000, 100),
            'low': np.random.uniform(39000, 40000, 100),
            'close': np.random.uniform(40000, 45000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })
        
        result = self.market_data.add_indicators(df)
        
        # RSI должен быть в диапазоне [0, 100]
        rsi_valid = result['rsi'].dropna()
        self.assertTrue((rsi_valid >= 0).all() and (rsi_valid <= 100).all())
        
        # ATR должен быть положительным
        atr_valid = result['atr'].dropna()
        self.assertTrue((atr_valid > 0).all())


if __name__ == '__main__':
    unittest.main()
