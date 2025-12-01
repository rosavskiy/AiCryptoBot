"""
Unit тесты для модуля executor.py
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.trading.executor import TradeExecutor


class TestTradeExecutor(unittest.TestCase):
    """Тесты для класса TradeExecutor"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.config = {
            'exchange': {'name': 'bybit', 'testnet': True},
            'symbols': ['BTC/USDT'],
            'trading': {
                'initial_capital': 10000,
                'min_confidence': 0.6,
                'paper_trading': True
            },
            'risk': {
                'max_position_size': 0.1,
                'stop_loss_atr_multiplier': 2.0
            }
        }
        
        self.mock_exchange = Mock()
        self.mock_exchange.fetch_balance.return_value = {'USDT': {'free': 10000}}
        self.mock_exchange.fetch_ticker.return_value = {'last': 40000}
        
        self.executor = TradeExecutor(self.config, self.mock_exchange)
    
    def test_initialization(self):
        """Тест инициализации класса"""
        self.assertEqual(self.executor.symbol, 'BTC/USDT')
        self.assertEqual(self.executor.initial_capital, 10000)
        self.assertTrue(self.executor.paper_trading)
        self.assertEqual(len(self.executor.open_positions), 0)
    
    def test_execute_signal_long_paper_trading(self):
        """Тест исполнения long сигнала в paper trading"""
        signal_data = {
            'signal': 1,  # Long
            'confidence': 0.75,
            'current_price': 40000,
            'stop_loss': 39000,
            'take_profit': 42000,
            'position_size': 0.025
        }
        
        result = self.executor.execute_signal(signal_data)
        
        self.assertTrue(result)
        self.assertEqual(len(self.executor.open_positions), 1)
        
        position = self.executor.open_positions[0]
        self.assertEqual(position['side'], 'long')
        self.assertEqual(position['entry_price'], 40000)
        self.assertEqual(position['size'], 0.025)
    
    def test_execute_signal_short_paper_trading(self):
        """Тест исполнения short сигнала в paper trading"""
        signal_data = {
            'signal': -1,  # Short
            'confidence': 0.70,
            'current_price': 40000,
            'stop_loss': 41000,
            'take_profit': 38000,
            'position_size': 0.025
        }
        
        result = self.executor.execute_signal(signal_data)
        
        self.assertTrue(result)
        self.assertEqual(len(self.executor.open_positions), 1)
        
        position = self.executor.open_positions[0]
        self.assertEqual(position['side'], 'short')
    
    def test_execute_signal_low_confidence(self):
        """Тест отклонения сигнала с низкой уверенностью"""
        signal_data = {
            'signal': 1,
            'confidence': 0.5,  # Ниже min_confidence (0.6)
            'current_price': 40000,
            'stop_loss': 39000,
            'take_profit': 42000,
            'position_size': 0.025
        }
        
        result = self.executor.execute_signal(signal_data)
        
        self.assertFalse(result)
        self.assertEqual(len(self.executor.open_positions), 0)
    
    def test_execute_signal_neutral(self):
        """Тест обработки нейтрального сигнала"""
        signal_data = {
            'signal': 0,  # Neutral
            'confidence': 0.75,
            'current_price': 40000
        }
        
        result = self.executor.execute_signal(signal_data)
        
        self.assertFalse(result)
        self.assertEqual(len(self.executor.open_positions), 0)
    
    @patch('ccxt.bybit')
    def test_execute_signal_live_trading(self, mock_bybit):
        """Тест исполнения сигнала в live trading (мок)"""
        # Настраиваем live trading
        config = self.config.copy()
        config['trading']['paper_trading'] = False
        
        mock_exchange = Mock()
        mock_exchange.fetch_balance.return_value = {'USDT': {'free': 10000}}
        mock_exchange.fetch_ticker.return_value = {'last': 40000}
        mock_exchange.create_order.return_value = {
            'id': '12345',
            'status': 'closed',
            'filled': 0.025,
            'average': 40000
        }
        
        executor = TradeExecutor(config, mock_exchange)
        
        signal_data = {
            'signal': 1,
            'confidence': 0.75,
            'current_price': 40000,
            'stop_loss': 39000,
            'take_profit': 42000,
            'position_size': 0.025
        }
        
        result = executor.execute_signal(signal_data)
        
        # В live trading должен быть вызван create_order
        mock_exchange.create_order.assert_called_once()
    
    def test_close_position_paper_trading_profit(self):
        """Тест закрытия позиции с прибылью в paper trading"""
        # Открываем позицию
        position = {
            'id': 'paper_1',
            'side': 'long',
            'entry_price': 40000,
            'size': 0.025,
            'stop_loss': 39000,
            'take_profit': 42000
        }
        self.executor.open_positions.append(position)
        
        # Закрываем с прибылью
        exit_price = 41000
        pnl = self.executor.close_position('paper_1', exit_price)
        
        expected_pnl = (41000 - 40000) * 0.025
        self.assertAlmostEqual(pnl, expected_pnl, places=2)
        self.assertEqual(len(self.executor.open_positions), 0)
    
    def test_close_position_paper_trading_loss(self):
        """Тест закрытия позиции с убытком в paper trading"""
        position = {
            'id': 'paper_1',
            'side': 'long',
            'entry_price': 40000,
            'size': 0.025,
            'stop_loss': 39000,
            'take_profit': 42000
        }
        self.executor.open_positions.append(position)
        
        # Закрываем с убытком
        exit_price = 39500
        pnl = self.executor.close_position('paper_1', exit_price)
        
        expected_pnl = (39500 - 40000) * 0.025
        self.assertAlmostEqual(pnl, expected_pnl, places=2)
        self.assertLess(pnl, 0)
    
    def test_close_position_short_paper_trading(self):
        """Тест закрытия short позиции в paper trading"""
        position = {
            'id': 'paper_1',
            'side': 'short',
            'entry_price': 40000,
            'size': 0.025,
            'stop_loss': 41000,
            'take_profit': 38000
        }
        self.executor.open_positions.append(position)
        
        # Закрываем short с прибылью (цена упала)
        exit_price = 39000
        pnl = self.executor.close_position('paper_1', exit_price)
        
        expected_pnl = (40000 - 39000) * 0.025
        self.assertAlmostEqual(pnl, expected_pnl, places=2)
        self.assertGreater(pnl, 0)
    
    def test_check_stop_loss_triggered(self):
        """Тест срабатывания стоп-лосса"""
        position = {
            'id': 'paper_1',
            'side': 'long',
            'entry_price': 40000,
            'size': 0.025,
            'stop_loss': 39000,
            'take_profit': 42000
        }
        self.executor.open_positions.append(position)
        
        current_price = 38900  # Ниже стоп-лосса
        
        triggered = self.executor.check_stop_loss(position, current_price)
        
        self.assertTrue(triggered)
    
    def test_check_stop_loss_not_triggered(self):
        """Тест что стоп-лосс не срабатывает"""
        position = {
            'id': 'paper_1',
            'side': 'long',
            'entry_price': 40000,
            'size': 0.025,
            'stop_loss': 39000,
            'take_profit': 42000
        }
        self.executor.open_positions.append(position)
        
        current_price = 39500  # Выше стоп-лосса
        
        triggered = self.executor.check_stop_loss(position, current_price)
        
        self.assertFalse(triggered)
    
    def test_check_take_profit_triggered(self):
        """Тест срабатывания тейк-профита"""
        position = {
            'id': 'paper_1',
            'side': 'long',
            'entry_price': 40000,
            'size': 0.025,
            'stop_loss': 39000,
            'take_profit': 42000
        }
        self.executor.open_positions.append(position)
        
        current_price = 42100  # Выше тейк-профита
        
        triggered = self.executor.check_take_profit(position, current_price)
        
        self.assertTrue(triggered)
    
    def test_check_take_profit_not_triggered(self):
        """Тест что тейк-профит не срабатывает"""
        position = {
            'id': 'paper_1',
            'side': 'long',
            'entry_price': 40000,
            'size': 0.025,
            'stop_loss': 39000,
            'take_profit': 42000
        }
        self.executor.open_positions.append(position)
        
        current_price = 41500  # Ниже тейк-профита
        
        triggered = self.executor.check_take_profit(position, current_price)
        
        self.assertFalse(triggered)
    
    def test_get_balance(self):
        """Тест получения баланса"""
        balance = self.executor.get_balance()
        
        self.assertEqual(balance, 10000)
        self.mock_exchange.fetch_balance.assert_called_once()
    
    def test_get_current_price(self):
        """Тест получения текущей цены"""
        price = self.executor.get_current_price()
        
        self.assertEqual(price, 40000)
        self.mock_exchange.fetch_ticker.assert_called_once()
    
    def test_multiple_positions_management(self):
        """Тест управления несколькими позициями"""
        # Открываем две позиции
        positions = [
            {
                'id': 'paper_1',
                'side': 'long',
                'entry_price': 40000,
                'size': 0.02,
                'stop_loss': 39000,
                'take_profit': 42000
            },
            {
                'id': 'paper_2',
                'side': 'short',
                'entry_price': 45000,
                'size': 0.015,
                'stop_loss': 46000,
                'take_profit': 43000
            }
        ]
        
        self.executor.open_positions.extend(positions)
        
        self.assertEqual(len(self.executor.open_positions), 2)
        
        # Закрываем одну
        pnl = self.executor.close_position('paper_1', 41000)
        
        self.assertEqual(len(self.executor.open_positions), 1)
        self.assertEqual(self.executor.open_positions[0]['id'], 'paper_2')


if __name__ == '__main__':
    unittest.main()
