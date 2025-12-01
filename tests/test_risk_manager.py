"""
Unit тесты для модуля risk_manager.py
"""
import unittest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.risk.risk_manager import RiskManager


class TestRiskManager(unittest.TestCase):
    """Тесты для класса RiskManager"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.config = {
            'risk': {
                'max_position_size': 0.1,
                'max_portfolio_risk': 0.02,
                'kelly_fraction': 0.25,
                'stop_loss_atr_multiplier': 2.0,
                'max_daily_loss': 0.05,
                'max_drawdown': 0.15,
                'min_win_rate': 0.40,
                'correlation_threshold': 0.7
            },
            'trading': {
                'initial_capital': 10000
            }
        }
        # Передаём initial_capital напрямую, чтобы избежать зависимости от ConfigManager
        self.risk_manager = RiskManager(initial_capital=10000)
    
    def test_initialization(self):
        """Тест инициализации класса"""
        self.assertEqual(self.risk_manager.initial_capital, 10000)
        self.assertEqual(self.risk_manager.max_position_size, 0.1)
        self.assertEqual(self.risk_manager.max_portfolio_risk, 0.02)
        self.assertEqual(len(self.risk_manager.trade_history), 0)
    
    def test_calculate_position_size_basic(self):
        """Тест базового расчёта размера позиции"""
        current_price = 40000
        stop_loss = 39000
        balance = 10000
        
        position_size = self.risk_manager.calculate_position_size(
            current_price, stop_loss, balance
        )
        
        # Проверяем, что размер позиции положительный и не превышает лимиты
        self.assertGreater(position_size, 0)
        position_value = position_size * current_price
        self.assertLessEqual(position_value / balance, self.config['risk']['max_position_size'])
    
    def test_calculate_position_size_with_win_rate(self):
        """Тест расчёта размера позиции с учётом win rate"""
        current_price = 40000
        stop_loss = 39000
        balance = 10000
        win_rate = 0.55
        
        position_size = self.risk_manager.calculate_position_size(
            current_price, stop_loss, balance, win_rate=win_rate
        )
        
        self.assertGreater(position_size, 0)
        
        # Размер с учётом Kelly должен отличаться от базового
        basic_size = self.risk_manager.calculate_position_size(
            current_price, stop_loss, balance
        )
        self.assertNotEqual(position_size, basic_size)
    
    def test_calculate_position_size_zero_risk(self):
        """Тест расчёта когда стоп-лосс равен цене входа"""
        current_price = 40000
        stop_loss = 40000  # Нулевой риск
        balance = 10000
        
        position_size = self.risk_manager.calculate_position_size(
            current_price, stop_loss, balance
        )
        
        # При нулевом риске должен вернуться минимальный размер
        self.assertEqual(position_size, 0)
    
    def test_calculate_stop_loss(self):
        """Тест расчёта стоп-лосса"""
        current_price = 40000
        atr = 500
        
        # Long позиция
        stop_loss_long = self.risk_manager.calculate_stop_loss(
            current_price, atr, side='long'
        )
        expected_long = current_price - (atr * 2.0)
        self.assertAlmostEqual(stop_loss_long, expected_long, places=2)
        
        # Short позиция
        stop_loss_short = self.risk_manager.calculate_stop_loss(
            current_price, atr, side='short'
        )
        expected_short = current_price + (atr * 2.0)
        self.assertAlmostEqual(stop_loss_short, expected_short, places=2)
    
    def test_calculate_take_profit(self):
        """Тест расчёта тейк-профита"""
        entry_price = 40000
        stop_loss = 39000
        
        # Long позиция
        take_profit_long = self.risk_manager.calculate_take_profit(
            entry_price, stop_loss, side='long'
        )
        risk = entry_price - stop_loss
        expected_long = entry_price + (risk * 2.0)
        self.assertAlmostEqual(take_profit_long, expected_long, places=2)
        
        # Short позиция
        entry_price = 40000
        stop_loss = 41000
        take_profit_short = self.risk_manager.calculate_take_profit(
            entry_price, stop_loss, side='short'
        )
        risk = stop_loss - entry_price
        expected_short = entry_price - (risk * 2.0)
        self.assertAlmostEqual(take_profit_short, expected_short, places=2)
    
    def test_check_risk_limits_within_limits(self):
        """Тест проверки лимитов риска - в пределах нормы"""
        balance = 10000
        open_positions = 1
        daily_pnl = -200  # -2%
        total_drawdown = -800  # -8%
        
        result = self.risk_manager.check_risk_limits(
            balance, open_positions, daily_pnl, total_drawdown
        )
        
        self.assertTrue(result)
    
    def test_check_risk_limits_daily_loss_exceeded(self):
        """Тест проверки лимитов - превышен дневной убыток"""
        balance = 10000
        open_positions = 1
        daily_pnl = -600  # -6%, превышает max_daily_loss (5%)
        total_drawdown = -800
        
        result = self.risk_manager.check_risk_limits(
            balance, open_positions, daily_pnl, total_drawdown
        )
        
        self.assertFalse(result)
    
    def test_check_risk_limits_max_drawdown_exceeded(self):
        """Тест проверки лимитов - превышена максимальная просадка"""
        balance = 10000
        open_positions = 1
        daily_pnl = -200
        total_drawdown = -1600  # -16%, превышает max_drawdown (15%)
        
        result = self.risk_manager.check_risk_limits(
            balance, open_positions, daily_pnl, total_drawdown
        )
        
        self.assertFalse(result)
    
    def test_update_trade_history(self):
        """Тест обновления истории сделок"""
        trade = {
            'symbol': 'BTC/USDT',
            'side': 'long',
            'entry_price': 40000,
            'exit_price': 41000,
            'pnl': 1000,
            'pnl_pct': 2.5
        }
        
        self.risk_manager.update_trade_history(trade)
        
        self.assertEqual(len(self.risk_manager.trade_history), 1)
        self.assertEqual(self.risk_manager.trade_history[0]['pnl'], 1000)
    
    def test_get_performance_metrics_empty(self):
        """Тест метрик производительности при пустой истории"""
        metrics = self.risk_manager.get_performance_metrics()
        
        self.assertEqual(metrics['total_trades'], 0)
        self.assertEqual(metrics['win_rate'], 0)
        self.assertEqual(metrics['total_pnl'], 0)
    
    def test_get_performance_metrics_with_trades(self):
        """Тест метрик производительности с историей сделок"""
        trades = [
            {'pnl': 1000, 'pnl_pct': 2.5},
            {'pnl': -500, 'pnl_pct': -1.25},
            {'pnl': 800, 'pnl_pct': 2.0},
            {'pnl': -300, 'pnl_pct': -0.75},
        ]
        
        for trade in trades:
            self.risk_manager.update_trade_history(trade)
        
        metrics = self.risk_manager.get_performance_metrics()
        
        self.assertEqual(metrics['total_trades'], 4)
        self.assertEqual(metrics['winning_trades'], 2)
        self.assertEqual(metrics['losing_trades'], 2)
        self.assertAlmostEqual(metrics['win_rate'], 0.5, places=2)
        self.assertEqual(metrics['total_pnl'], 1000)
        self.assertAlmostEqual(metrics['avg_win'], 900, places=0)
        self.assertAlmostEqual(metrics['avg_loss'], -400, places=0)
        self.assertAlmostEqual(metrics['profit_factor'], 1800 / 800, places=2)
    
    def test_kelly_criterion_calculation(self):
        """Тест расчёта критерия Келли"""
        # Win rate 60%, avg win/loss ratio 1.5
        win_rate = 0.6
        avg_win = 1500
        avg_loss = -1000
        
        # Kelly = W - (1-W)/(R), где R = avg_win/abs(avg_loss)
        # Kelly = 0.6 - 0.4/1.5 = 0.6 - 0.267 = 0.333
        expected_kelly = 0.333
        
        # Проверяем через расчёт размера позиции с win_rate
        position_size_with_kelly = self.risk_manager.calculate_position_size(
            current_price=40000,
            stop_loss=39000,
            balance=10000,
            win_rate=win_rate
        )
        
        # С Kelly fraction 0.25, размер должен быть скорректирован
        self.assertGreater(position_size_with_kelly, 0)
    
    def test_position_size_max_limit(self):
        """Тест что размер позиции не превышает максимум"""
        current_price = 40000
        stop_loss = 39900  # Очень близкий стоп (малый риск)
        balance = 10000
        
        position_size = self.risk_manager.calculate_position_size(
            current_price, stop_loss, balance
        )
        
        position_value = position_size * current_price
        position_pct = position_value / balance
        
        # Размер позиции не должен превышать max_position_size
        self.assertLessEqual(position_pct, self.config['risk']['max_position_size'])


if __name__ == '__main__':
    unittest.main()
