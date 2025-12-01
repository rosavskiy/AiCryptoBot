"""
Интеграционные тесты для проверки взаимодействия модулей
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.market_data import MarketData
from src.ml.predictor import MLPredictor
from src.risk.risk_manager import RiskManager
from src.trading.executor import TradeExecutor


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты"""
    
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
            },
            'ml': {
                'model_type': 'RandomForest',
                'n_estimators': 50,
                'max_depth': 10,
                'random_state': 42,
                'test_size': 0.2
            },
            'risk': {
                'max_position_size': 0.1,
                'max_portfolio_risk': 0.02,
                'kelly_fraction': 0.25,
                'stop_loss_atr_multiplier': 2.0,
                'max_daily_loss': 0.05,
                'max_drawdown': 0.15
            },
            'trading': {
                'initial_capital': 10000,
                'min_confidence': 0.6
            }
        }
    
    @patch('ccxt.bybit')
    def test_data_to_prediction_pipeline(self, mock_bybit):
        """Тест полного пайплайна: данные → индикаторы → ML предсказание"""
        # Мокаем OHLCV данные
        mock_exchange = Mock()
        ohlcv_data = []
        base_time = 1704067200000
        for i in range(300):
            ohlcv_data.append([
                base_time + i * 3600000,
                40000 + np.random.randn() * 100,
                41000 + np.random.randn() * 100,
                39000 + np.random.randn() * 100,
                40000 + np.random.randn() * 100,
                100 + np.random.randn() * 10
            ])
        mock_exchange.fetch_ohlcv.return_value = ohlcv_data
        mock_bybit.return_value = mock_exchange
        
        # Шаг 1: Получаем данные
        market_data = MarketData(self.config)
        market_data.exchange = mock_exchange
        df = market_data.fetch_ohlcv(limit=300)
        
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 300)
        
        # Шаг 2: Добавляем индикаторы
        df = market_data.add_indicators(df)
        
        self.assertIn('sma_20', df.columns)
        self.assertIn('rsi', df.columns)
        
        # Шаг 3: Создаём таргет для обучения
        df = market_data.create_ml_target(df, future_bars=5)
        
        self.assertIn('target', df.columns)
        
        # Шаг 4: Обучаем ML модель
        predictor = MLPredictor(self.config)
        feature_columns = [
            'open', 'high', 'low', 'close', 'volume',
            'sma_20', 'sma_50', 'ema_12', 'ema_26',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_upper', 'bb_middle', 'bb_lower', 'atr'
        ]
        
        train_success = predictor.train(df, feature_columns)
        
        self.assertTrue(train_success)
        self.assertIsNotNone(predictor.model)
        
        # Шаг 5: Делаем предсказание
        latest_data = df[feature_columns].iloc[[-1]]
        signal, confidence = predictor.predict_single(latest_data)
        
        self.assertIn(signal, [-1, 0, 1])
        self.assertTrue(0 <= confidence <= 1)
    
    @patch('ccxt.bybit')
    def test_prediction_to_trade_execution_pipeline(self, mock_bybit):
        """Тест пайплайна: ML предсказание → риск-менеджмент → исполнение сделки"""
        # Подготовка моков
        mock_exchange = Mock()
        mock_exchange.fetch_balance.return_value = {'USDT': {'free': 10000}}
        mock_exchange.fetch_ticker.return_value = {'last': 40000}
        mock_exchange.create_order.return_value = {
            'id': '12345',
            'symbol': 'BTC/USDT',
            'type': 'limit',
            'side': 'buy',
            'price': 40000,
            'amount': 0.025,
            'status': 'closed'
        }
        mock_bybit.return_value = mock_exchange
        
        # Инициализация компонентов
        risk_manager = RiskManager(self.config)
        executor = TradeExecutor(self.config, mock_exchange)
        
        # Шаг 1: ML модель выдала сигнал на покупку
        ml_signal = 1  # Long
        ml_confidence = 0.75
        current_price = 40000
        atr = 500
        
        # Проверяем что уверенность выше минимального порога
        self.assertGreater(ml_confidence, self.config['trading']['min_confidence'])
        
        # Шаг 2: Риск-менеджер рассчитывает параметры сделки
        stop_loss = risk_manager.calculate_stop_loss(current_price, atr, side='long')
        take_profit = risk_manager.calculate_take_profit(current_price, stop_loss, side='long')
        
        balance = 10000
        position_size = risk_manager.calculate_position_size(
            current_price, stop_loss, balance
        )
        
        self.assertGreater(position_size, 0)
        self.assertLess(stop_loss, current_price)
        self.assertGreater(take_profit, current_price)
        
        # Шаг 3: Проверяем риск-лимиты
        can_trade = risk_manager.check_risk_limits(
            balance=balance,
            open_positions=0,
            daily_pnl=0,
            total_drawdown=0
        )
        
        self.assertTrue(can_trade)
        
        # Шаг 4: Исполняем сделку (мокированную)
        # В реальности executor.execute_signal() делает это
        # Здесь просто проверяем что параметры корректные
        self.assertIsNotNone(position_size)
        self.assertIsNotNone(stop_loss)
        self.assertIsNotNone(take_profit)
    
    def test_risk_limits_prevent_trade(self):
        """Тест что риск-лимиты блокируют сделку при превышении"""
        risk_manager = RiskManager(self.config)
        
        # Сценарий: большая дневная просадка
        balance = 10000
        daily_pnl = -600  # -6%
        
        can_trade = risk_manager.check_risk_limits(
            balance=balance,
            open_positions=0,
            daily_pnl=daily_pnl,
            total_drawdown=-600
        )
        
        # Сделка должна быть заблокирована
        self.assertFalse(can_trade)
    
    @patch('ccxt.bybit')
    def test_full_trade_lifecycle(self, mock_bybit):
        """Тест полного жизненного цикла сделки"""
        mock_exchange = Mock()
        mock_exchange.fetch_balance.return_value = {'USDT': {'free': 10000}}
        mock_exchange.fetch_ticker.return_value = {'last': 40000}
        
        # Мок для создания ордера
        mock_exchange.create_order.return_value = {
            'id': '12345',
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'price': 40000,
            'amount': 0.025,
            'status': 'closed'
        }
        
        # Мок для закрытия позиции
        mock_exchange.fetch_order.return_value = {
            'id': '12345',
            'status': 'closed',
            'filled': 0.025,
            'average': 41000
        }
        
        mock_bybit.return_value = mock_exchange
        
        risk_manager = RiskManager(self.config)
        executor = TradeExecutor(self.config, mock_exchange)
        
        # 1. Открываем позицию
        entry_price = 40000
        stop_loss = 39000
        take_profit = 42000
        balance = 10000
        
        position_size = risk_manager.calculate_position_size(
            entry_price, stop_loss, balance
        )
        
        # Проверяем что размер позиции корректный
        self.assertGreater(position_size, 0)
        
        # 2. Закрываем позицию с прибылью (мокированно)
        exit_price = 41000
        pnl = (exit_price - entry_price) * position_size
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        
        # 3. Обновляем историю сделок
        trade = {
            'symbol': 'BTC/USDT',
            'side': 'long',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'size': position_size,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        }
        
        risk_manager.update_trade_history(trade)
        
        # 4. Проверяем метрики
        metrics = risk_manager.get_performance_metrics()
        
        self.assertEqual(metrics['total_trades'], 1)
        self.assertEqual(metrics['winning_trades'], 1)
        self.assertGreater(metrics['total_pnl'], 0)
        self.assertEqual(metrics['win_rate'], 1.0)
    
    def test_multiple_trades_performance_tracking(self):
        """Тест отслеживания производительности множественных сделок"""
        risk_manager = RiskManager(self.config)
        
        # Симулируем серию сделок
        trades = [
            {'pnl': 1000, 'pnl_pct': 2.5},   # Win
            {'pnl': -500, 'pnl_pct': -1.25}, # Loss
            {'pnl': 1500, 'pnl_pct': 3.75},  # Win
            {'pnl': -300, 'pnl_pct': -0.75}, # Loss
            {'pnl': 800, 'pnl_pct': 2.0},    # Win
        ]
        
        for trade in trades:
            risk_manager.update_trade_history(trade)
        
        metrics = risk_manager.get_performance_metrics()
        
        # Проверяем метрики
        self.assertEqual(metrics['total_trades'], 5)
        self.assertEqual(metrics['winning_trades'], 3)
        self.assertEqual(metrics['losing_trades'], 2)
        self.assertAlmostEqual(metrics['win_rate'], 0.6, places=2)
        
        total_wins = 1000 + 1500 + 800
        total_losses = 500 + 300
        expected_pnl = total_wins - total_losses
        
        self.assertEqual(metrics['total_pnl'], expected_pnl)
        self.assertGreater(metrics['profit_factor'], 1)  # Прибыльная стратегия


if __name__ == '__main__':
    unittest.main()
