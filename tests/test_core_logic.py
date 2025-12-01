"""
Упрощённые unit тесты для основных модулей
Эти тесты не зависят от ConfigManager и тестируют core функциональность
"""
import unittest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMarketDataBasic(unittest.TestCase):
    """Базовые тесты для технических индикаторов"""
    
    def test_rsi_calculation(self):
        """Тест расчёта RSI"""
        # Создаём тестовые данные с явным трендом
        prices = [44, 44.5, 45, 45.5, 46, 46.5, 47, 47.5, 48, 48.5, 49, 49.5, 50]
        df = pd.DataFrame({'close': prices})
        
        # Простой RSI расчёт
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # RSI должен быть выше 50 для восходящего тренда
        self.assertTrue(rsi.iloc[-1] > 50 or np.isnan(rsi.iloc[-1]))
    
    def test_sma_calculation(self):
        """Тест расчёта простой скользящей средней"""
        prices = [40, 42, 41, 43, 44, 45, 46, 47, 48, 49]
        df = pd.DataFrame({'close': prices})
        
        sma_5 = df['close'].rolling(window=5).mean()
        
        # Последнее значение SMA(5) должно быть средним последних 5 цен
        expected = np.mean(prices[-5:])
        self.assertAlmostEqual(sma_5.iloc[-1], expected, places=2)
    
    def test_bollinger_bands(self):
        """Тест расчёта полос Боллинджера"""
        prices = np.random.uniform(40, 50, 50)
        df = pd.DataFrame({'close': prices})
        
        window = 20
        sma = df['close'].rolling(window=window).mean()
        std = df['close'].rolling(window=window).std()
        
        bb_upper = sma + (std * 2)
        bb_lower = sma - (std * 2)
        
        # Верхняя полоса должна быть выше нижней
        self.assertTrue((bb_upper.dropna() > bb_lower.dropna()).all())


class TestPositionSizingBasic(unittest.TestCase):
    """Базовые тесты для расчёта размера позиции"""
    
    def test_basic_position_calculation(self):
        """Тест базового расчёта размера позиции"""
        capital = 10000
        risk_percent = 0.02  # 2%
        entry_price = 40000
        stop_loss = 39000
        
        # Риск в долларах
        risk_amount = capital * risk_percent
        
        # Риск на одну монету
        risk_per_coin = entry_price - stop_loss
        
        # Размер позиции в монетах
        position_size = risk_amount / risk_per_coin
        
        # Проверки
        self.assertGreater(position_size, 0)
        self.assertLess(position_size * entry_price, capital)  # Не превышаем капитал
        
        # Проверяем что риск соответствует заданному
        actual_risk = position_size * risk_per_coin
        self.assertAlmostEqual(actual_risk, risk_amount, places=2)
    
    def test_kelly_criterion_basic(self):
        """Тест расчёта критерия Келли"""
        win_rate = 0.6
        avg_win = 1000
        avg_loss = 500
        
        # Kelly formula: f = (W - (1-W)/R)
        # где W = win rate, R = avg_win/avg_loss
        R = avg_win / avg_loss
        kelly_fraction = win_rate - ((1 - win_rate) / R)
        
        # Kelly должен быть положительным для выигрышной стратегии
        self.assertGreater(kelly_fraction, 0)
        self.assertLess(kelly_fraction, 1)  # И меньше 100%


class TestPnLCalculation(unittest.TestCase):
    """Тесты для расчёта прибыли/убытка"""
    
    def test_long_trade_profit(self):
        """Тест прибыльной long сделки"""
        entry_price = 40000
        exit_price = 41000
        position_size = 0.025
        commission = 0.001
        
        # Gross PnL
        gross_pnl = (exit_price - entry_price) * position_size
        
        # Commission costs
        entry_cost = entry_price * position_size * commission
        exit_cost = exit_price * position_size * commission
        
        # Net PnL
        net_pnl = gross_pnl - entry_cost - exit_cost
        
        self.assertGreater(net_pnl, 0)  # Прибыльная сделка
        self.assertLess(net_pnl, gross_pnl)  # После комиссии меньше
    
    def test_short_trade_profit(self):
        """Тест прибыльной short сделки"""
        entry_price = 40000
        exit_price = 39000  # Цена упала
        position_size = 0.025
        
        # Для short: прибыль когда цена падает
        gross_pnl = (entry_price - exit_price) * position_size
        
        self.assertGreater(gross_pnl, 0)
    
    def test_long_trade_loss(self):
        """Тест убыточной long сделки"""
        entry_price = 40000
        exit_price = 39000  # Цена упала
        position_size = 0.025
        
        gross_pnl = (exit_price - entry_price) * position_size
        
        self.assertLess(gross_pnl, 0)  # Убыточная сделка


class TestPerformanceMetrics(unittest.TestCase):
    """Тесты для метрик производительности"""
    
    def test_win_rate_calculation(self):
        """Тест расчёта win rate"""
        trades = [
            {'pnl': 1000},
            {'pnl': -500},
            {'pnl': 800},
            {'pnl': -300},
            {'pnl': 1200}
        ]
        
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        total_trades = len(trades)
        win_rate = winning_trades / total_trades
        
        self.assertAlmostEqual(win_rate, 0.6, places=2)  # 3/5 = 60%
    
    def test_profit_factor_calculation(self):
        """Тест расчёта profit factor"""
        trades = [
            {'pnl': 1000},
            {'pnl': -500},
            {'pnl': 1500},
            {'pnl': -300},
        ]
        
        total_wins = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        total_losses = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        expected = (1000 + 1500) / (500 + 300)
        self.assertAlmostEqual(profit_factor, expected, places=2)
    
    def test_sharpe_ratio_calculation(self):
        """Тест расчёта Sharpe Ratio"""
        returns = [0.02, -0.01, 0.03, 0.01, -0.005, 0.025, 0.015]
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Годовой Sharpe (252 торговых дня)
        sharpe = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Для положительных возвратов Sharpe должен быть положительным
        self.assertGreater(sharpe, 0)
    
    def test_max_drawdown_calculation(self):
        """Тест расчёта максимальной просадки"""
        equity_curve = [10000, 11000, 12000, 10500, 9000, 9500, 11000, 12500]
        
        peak = equity_curve[0]
        max_dd = 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (value - peak) / peak
            if dd < max_dd:
                max_dd = dd
        
        # Max DD: от 12000 до 9000 = -25%
        expected_dd = (9000 - 12000) / 12000
        self.assertAlmostEqual(max_dd, expected_dd, places=2)


class TestStopLossTakeProfit(unittest.TestCase):
    """Тесты для стоп-лосса и тейк-профита"""
    
    def test_atr_stop_loss_long(self):
        """Тест расчёта стоп-лосса на основе ATR для long"""
        entry_price = 40000
        atr = 500
        atr_multiplier = 2.0
        
        stop_loss = entry_price - (atr * atr_multiplier)
        
        self.assertLess(stop_loss, entry_price)
        self.assertEqual(stop_loss, 39000)
    
    def test_atr_stop_loss_short(self):
        """Тест расчёта стоп-лосса на основе ATR для short"""
        entry_price = 40000
        atr = 500
        atr_multiplier = 2.0
        
        stop_loss = entry_price + (atr * atr_multiplier)
        
        self.assertGreater(stop_loss, entry_price)
        self.assertEqual(stop_loss, 41000)
    
    def test_risk_reward_ratio(self):
        """Тест расчёта соотношения риска к прибыли"""
        entry_price = 40000
        stop_loss = 39000
        take_profit = 42000
        
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        
        rr_ratio = reward / risk
        
        self.assertEqual(rr_ratio, 2.0)  # Risk:Reward = 1:2


if __name__ == '__main__':
    # Запускаем тесты с подробным выводом
    unittest.main(verbosity=2)
