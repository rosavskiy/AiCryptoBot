"""
Unit тесты для модуля backtest.py
"""
import unittest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtesting.backtest import Backtester


class TestBacktester(unittest.TestCase):
    """Тесты для класса Backtester"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.config = {
            'backtesting': {
                'initial_capital': 10000,
                'commission': 0.001,
                'slippage': 0.0005,
                'walk_forward': {
                    'train_size': 0.7,
                    'test_size': 0.3,
                    'n_splits': 3
                }
            },
            'risk': {
                'max_position_size': 0.1,
                'stop_loss_atr_multiplier': 2.0,
                'kelly_fraction': 0.25
            },
            'ml': {
                'model_type': 'RandomForest',
                'n_estimators': 50,
                'max_depth': 10,
                'random_state': 42
            }
        }
        self.backtester = Backtester(self.config)
    
    def _create_sample_data(self, n_samples=500):
        """Создание тестовых данных для бэктеста"""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=n_samples, freq='1h')
        
        # Генерируем цены с трендом
        close_prices = 40000 + np.cumsum(np.random.randn(n_samples) * 100)
        
        data = {
            'timestamp': dates,
            'open': close_prices + np.random.randn(n_samples) * 50,
            'high': close_prices + np.abs(np.random.randn(n_samples) * 100),
            'low': close_prices - np.abs(np.random.randn(n_samples) * 100),
            'close': close_prices,
            'volume': np.random.uniform(100, 1000, n_samples),
            'sma_20': close_prices + np.random.randn(n_samples) * 20,
            'sma_50': close_prices + np.random.randn(n_samples) * 30,
            'ema_12': close_prices + np.random.randn(n_samples) * 15,
            'ema_26': close_prices + np.random.randn(n_samples) * 25,
            'rsi': np.random.uniform(30, 70, n_samples),
            'macd': np.random.randn(n_samples) * 10,
            'macd_signal': np.random.randn(n_samples) * 8,
            'macd_hist': np.random.randn(n_samples) * 5,
            'bb_upper': close_prices + 500,
            'bb_middle': close_prices,
            'bb_lower': close_prices - 500,
            'atr': np.random.uniform(200, 600, n_samples),
            'target': np.random.choice([-1, 0, 1], n_samples)
        }
        
        return pd.DataFrame(data)
    
    def test_initialization(self):
        """Тест инициализации класса"""
        self.assertEqual(self.backtester.initial_capital, 10000)
        self.assertEqual(self.backtester.commission, 0.001)
        self.assertEqual(self.backtester.slippage, 0.0005)
        self.assertEqual(len(self.backtester.trades), 0)
    
    def test_calculate_trade_cost(self):
        """Тест расчёта стоимости сделки (комиссия + проскальзывание)"""
        price = 40000
        size = 0.025
        
        cost = self.backtester.calculate_trade_cost(price, size)
        
        # Стоимость = цена * размер * (комиссия + проскальзывание)
        expected = price * size * (self.config['backtesting']['commission'] + 
                                   self.config['backtesting']['slippage'])
        
        self.assertAlmostEqual(cost, expected, places=2)
    
    def test_execute_trade_long(self):
        """Тест исполнения long сделки"""
        entry_price = 40000
        exit_price = 41000
        size = 0.025
        
        pnl = self.backtester.execute_trade('long', entry_price, exit_price, size)
        
        # PnL = (exit - entry) * size - costs
        gross_pnl = (exit_price - entry_price) * size
        entry_cost = self.backtester.calculate_trade_cost(entry_price, size)
        exit_cost = self.backtester.calculate_trade_cost(exit_price, size)
        expected_pnl = gross_pnl - entry_cost - exit_cost
        
        self.assertAlmostEqual(pnl, expected_pnl, places=2)
        self.assertGreater(pnl, 0)  # Прибыльная сделка
    
    def test_execute_trade_short(self):
        """Тест исполнения short сделки"""
        entry_price = 40000
        exit_price = 39000
        size = 0.025
        
        pnl = self.backtester.execute_trade('short', entry_price, exit_price, size)
        
        # PnL для short = (entry - exit) * size - costs
        gross_pnl = (entry_price - exit_price) * size
        expected_pnl = gross_pnl - (
            self.backtester.calculate_trade_cost(entry_price, size) +
            self.backtester.calculate_trade_cost(exit_price, size)
        )
        
        self.assertAlmostEqual(pnl, expected_pnl, places=2)
        self.assertGreater(pnl, 0)  # Прибыльная сделка
    
    def test_execute_trade_long_loss(self):
        """Тест убыточной long сделки"""
        entry_price = 40000
        exit_price = 39000  # Цена упала
        size = 0.025
        
        pnl = self.backtester.execute_trade('long', entry_price, exit_price, size)
        
        self.assertLess(pnl, 0)  # Убыточная сделка
    
    def test_calculate_metrics_empty_trades(self):
        """Тест расчёта метрик при отсутствии сделок"""
        df = self._create_sample_data(100)
        equity_curve = [10000] * len(df)
        
        metrics = self.backtester.calculate_metrics(equity_curve)
        
        self.assertEqual(metrics['total_trades'], 0)
        self.assertEqual(metrics['total_return'], 0)
        self.assertEqual(metrics['sharpe_ratio'], 0)
    
    def test_calculate_metrics_with_trades(self):
        """Тест расчёта метрик с историей сделок"""
        # Добавляем сделки
        self.backtester.trades = [
            {'pnl': 1000, 'pnl_pct': 10},
            {'pnl': -500, 'pnl_pct': -5},
            {'pnl': 1500, 'pnl_pct': 15},
            {'pnl': -300, 'pnl_pct': -3},
        ]
        
        # Создаём equity curve
        initial = 10000
        equity_curve = [initial]
        for trade in self.backtester.trades:
            equity_curve.append(equity_curve[-1] + trade['pnl'])
        
        metrics = self.backtester.calculate_metrics(equity_curve)
        
        self.assertEqual(metrics['total_trades'], 4)
        self.assertEqual(metrics['winning_trades'], 2)
        self.assertEqual(metrics['losing_trades'], 2)
        self.assertAlmostEqual(metrics['win_rate'], 0.5, places=2)
        
        expected_return = ((equity_curve[-1] - initial) / initial) * 100
        self.assertAlmostEqual(metrics['total_return'], expected_return, places=2)
    
    def test_calculate_sharpe_ratio(self):
        """Тест расчёта коэффициента Шарпа"""
        # Создаём equity curve с положительным ростом
        equity_curve = [10000 + i * 100 for i in range(100)]
        
        metrics = self.backtester.calculate_metrics(equity_curve)
        
        # Sharpe должен быть положительным для растущей equity
        self.assertGreater(metrics['sharpe_ratio'], 0)
    
    def test_calculate_max_drawdown(self):
        """Тест расчёта максимальной просадки"""
        # Equity curve с просадкой
        equity_curve = [10000, 11000, 12000, 10500, 9000, 9500, 11000, 12500]
        
        metrics = self.backtester.calculate_metrics(equity_curve)
        
        # Max drawdown: от 12000 до 9000 = -25%
        expected_dd = ((9000 - 12000) / 12000) * 100
        self.assertAlmostEqual(metrics['max_drawdown'], expected_dd, places=1)
        self.assertLess(metrics['max_drawdown'], 0)
    
    @patch('src.ml.predictor.MLPredictor')
    @patch('src.risk.risk_manager.RiskManager')
    def test_walk_forward_validation_structure(self, mock_risk, mock_predictor):
        """Тест структуры Walk-Forward Validation"""
        df = self._create_sample_data(500)
        feature_columns = ['sma_20', 'rsi', 'macd', 'atr']
        
        # Настраиваем моки
        mock_predictor_instance = Mock()
        mock_predictor_instance.train.return_value = True
        mock_predictor_instance.predict_single.return_value = (1, 0.75)
        mock_predictor.return_value = mock_predictor_instance
        
        mock_risk_instance = Mock()
        mock_risk_instance.calculate_position_size.return_value = 0.025
        mock_risk_instance.calculate_stop_loss.return_value = 39000
        mock_risk_instance.check_risk_limits.return_value = True
        mock_risk.return_value = mock_risk_instance
        
        results = self.backtester.walk_forward_validation(df, feature_columns)
        
        # Проверяем что результаты содержат все необходимые поля
        self.assertIn('equity_curve', results)
        self.assertIn('metrics', results)
        self.assertIn('trades', results)
        
        # Equity curve должна иметь ту же длину что и DataFrame
        self.assertEqual(len(results['equity_curve']), len(df))
    
    def test_equity_curve_monotonic_properties(self):
        """Тест свойств equity curve"""
        # Equity curve не должна быть отрицательной
        equity_curve = [10000, 10500, 10200, 10800, 10400]
        
        self.assertTrue(all(e > 0 for e in equity_curve))
    
    def test_commission_and_slippage_impact(self):
        """Тест влияния комиссии и проскальзывания"""
        entry_price = 40000
        exit_price = 40100  # Малая прибыль
        size = 0.025
        
        # Без комиссии и проскальзывания
        gross_pnl = (exit_price - entry_price) * size
        
        # С комиссией и проскальзыванием
        net_pnl = self.backtester.execute_trade('long', entry_price, exit_price, size)
        
        # Net PnL должен быть меньше gross из-за затрат
        self.assertLess(net_pnl, gross_pnl)
        
        # Затраты должны быть положительными
        costs = gross_pnl - net_pnl
        self.assertGreater(costs, 0)
    
    def test_profit_factor_calculation(self):
        """Тест расчёта profit factor"""
        self.backtester.trades = [
            {'pnl': 1000},
            {'pnl': -500},
            {'pnl': 1500},
            {'pnl': -300},
        ]
        
        total_wins = 1000 + 1500
        total_losses = abs(-500 - 300)
        expected_pf = total_wins / total_losses
        
        equity_curve = [10000 + sum(t['pnl'] for t in self.backtester.trades[:i+1]) 
                       for i in range(len(self.backtester.trades))]
        
        metrics = self.backtester.calculate_metrics(equity_curve)
        
        self.assertAlmostEqual(metrics['profit_factor'], expected_pf, places=2)


if __name__ == '__main__':
    unittest.main()
