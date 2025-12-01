"""
Risk Manager
============
Calculates position sizes, stop-loss, take-profit levels.
Monitors drawdown and enforces risk limits.
"""

import logging
from typing import Dict, Tuple, Optional
import numpy as np
from datetime import datetime

from ..config.config_loader import get_config


logger = logging.getLogger(__name__)


class RiskManager:
    """
    Manages risk parameters for trading
    """
    
    def __init__(self, initial_capital: float = None):
        """
        Initialize risk manager
        
        Args:
            initial_capital: Starting capital in USDT
        """
        self.config = get_config()
        
        # Capital tracking
        self.initial_capital = initial_capital or \
            self.config.get('backtest', 'initial_capital', default=10000.0)
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        
        # Risk parameters from config
        self.risk_per_trade = self.config.get('risk', 'risk_per_trade', default=0.01)
        self.max_position_size = self.config.get('risk', 'max_position_size', default=0.1)
        self.max_open_positions = self.config.get('risk', 'max_open_positions', default=3)
        self.max_drawdown = self.config.get('risk', 'max_drawdown_percent', default=15.0) / 100
        
        # Stop-loss and take-profit multipliers
        self.sl_atr_mult = self.config.get('risk', 'stop_loss_atr_multiplier', default=2.0)
        self.tp_atr_mult = self.config.get('risk', 'take_profit_atr_multiplier', default=3.0)
        
        # Leverage
        self.leverage = self.config.get('risk', 'leverage', default=1)
        
        # Position tracking
        self.open_positions = []
        self.daily_trades = 0
        self.last_trade_date = None
        
        # P&L tracking (for web interface compatibility)
        self.total_pnl = 0.0
        self.current_drawdown = 0.0
        self.max_positions = self.max_open_positions  # Alias for compatibility
        
        logger.info(f"[RISK] Risk Manager initialized with ${self.initial_capital:,.2f} capital")
        logger.info(f"[RISK] Risk per trade: {self.risk_per_trade:.2%}, Max positions: {self.max_open_positions}")
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        method: str = 'fixed'
    ) -> Tuple[float, float]:
        """
        Calculate position size based on risk parameters
        
        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            method: 'fixed' or 'kelly' (Kelly Criterion)
        
        Returns:
            Tuple of (position_size_usdt, quantity_coins)
        """
        if method == 'fixed':
            return self._fixed_position_size(entry_price, stop_loss)
        elif method == 'kelly':
            return self._kelly_position_size(entry_price, stop_loss)
        else:
            raise ValueError(f"Unknown position sizing method: {method}")
    
    def _fixed_position_size(
        self,
        entry_price: float,
        stop_loss: float
    ) -> Tuple[float, float]:
        """
        Fixed percentage risk position sizing
        
        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
        
        Returns:
            Tuple of (position_size_usdt, quantity_coins)
        """
        # Risk amount in USDT
        risk_amount = self.current_capital * self.risk_per_trade
        
        # Price distance to stop-loss
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            logger.warning("[WARNING] Stop-loss equals entry price, using min position")
            position_size = self.current_capital * 0.01
        else:
            # Position size = Risk Amount / (Price Risk / Entry Price)
            position_size = risk_amount / (price_risk / entry_price)
        
        # Apply maximum position size limit
        max_position = self.current_capital * self.max_position_size
        position_size = min(position_size, max_position)
        
        # Calculate quantity
        quantity = position_size / entry_price
        
        logger.info(f"[RISK] Fixed sizing: ${position_size:.2f} USDT ({quantity:.6f} coins)")
        logger.info(f"[RISK] Risk: ${risk_amount:.2f} ({self.risk_per_trade:.2%} of capital)")
        
        return position_size, quantity
    
    def _kelly_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        win_rate: float = 0.55,
        avg_win_loss_ratio: float = 1.5
    ) -> Tuple[float, float]:
        """
        Kelly Criterion position sizing
        
        Formula: Kelly% = W - [(1-W) / R]
        Where: W = win rate, R = avg_win / avg_loss ratio
        
        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            win_rate: Historical win rate (default 55%)
            avg_win_loss_ratio: Average win/loss ratio (default 1.5)
        
        Returns:
            Tuple of (position_size_usdt, quantity_coins)
        """
        # Calculate Kelly percentage
        kelly_pct = win_rate - ((1 - win_rate) / avg_win_loss_ratio)
        
        # Use fractional Kelly (50% of full Kelly for safety)
        kelly_pct = kelly_pct * 0.5
        
        # Ensure reasonable bounds
        kelly_pct = max(0.01, min(kelly_pct, self.max_position_size))
        
        # Calculate position size
        position_size = self.current_capital * kelly_pct
        quantity = position_size / entry_price
        
        logger.info(f"[RISK] Kelly sizing: {kelly_pct:.2%} of capital = ${position_size:.2f}")
        
        return position_size, quantity
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str = 'long'
    ) -> float:
        """
        Calculate stop-loss price based on ATR
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            direction: 'long' or 'short'
        
        Returns:
            Stop-loss price
        """
        if direction == 'long':
            stop_loss = entry_price - (atr * self.sl_atr_mult)
        else:  # short
            stop_loss = entry_price + (atr * self.sl_atr_mult)
        
        logger.info(f"[RISK] Stop-loss ({direction}): ${stop_loss:.2f} (ATR: {atr:.2f})")
        
        return stop_loss
    
    def calculate_take_profit(
        self,
        entry_price: float,
        atr: float,
        direction: str = 'long'
    ) -> float:
        """
        Calculate take-profit price based on ATR
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            direction: 'long' or 'short'
        
        Returns:
            Take-profit price
        """
        if direction == 'long':
            take_profit = entry_price + (atr * self.tp_atr_mult)
        else:  # short
            take_profit = entry_price - (atr * self.tp_atr_mult)
        
        logger.info(f"[RISK] Take-profit ({direction}): ${take_profit:.2f} (ATR: {atr:.2f})")
        
        return take_profit
    
    def can_open_position(self) -> Tuple[bool, str]:
        """
        Check if a new position can be opened
        
        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        # Check drawdown
        current_drawdown = self.get_current_drawdown()
        if current_drawdown >= self.max_drawdown:
            return False, f"Max drawdown exceeded: {current_drawdown:.2%}"
        
        # Check number of open positions
        if len(self.open_positions) >= self.max_open_positions:
            return False, f"Max open positions reached: {len(self.open_positions)}/{self.max_open_positions}"
        
        # Check daily trade limit
        max_daily = self.config.get('risk', 'max_daily_trades', default=10)
        today = datetime.now().date()
        
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today
        
        if self.daily_trades >= max_daily:
            return False, f"Daily trade limit reached: {self.daily_trades}/{max_daily}"
        
        # Check minimum capital
        if self.current_capital < self.initial_capital * 0.5:
            return False, f"Capital too low: ${self.current_capital:.2f} < 50% of initial"
        
        return True, "OK"
    
    def add_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        direction: str = 'long'
    ) -> Dict:
        """
        Register a new open position
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            quantity: Position quantity
            stop_loss: Stop-loss price
            take_profit: Take-profit price
            direction: 'long' or 'short'
        
        Returns:
            Position dictionary
        """
        position = {
            'symbol': symbol,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'direction': direction,
            'entry_time': datetime.now(),
            'position_value': entry_price * quantity
        }
        
        self.open_positions.append(position)
        self.daily_trades += 1
        
        logger.info(f"[RISK] Position opened: {symbol} {direction.upper()} {quantity:.6f} @ ${entry_price:.2f}")
        logger.info(f"[RISK] SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
        
        return position
    
    def close_position(
        self,
        symbol: str,
        exit_price: float
    ) -> Optional[Dict]:
        """
        Close an open position and calculate PnL
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
        
        Returns:
            Closed position with PnL data, or None if not found
        """
        position = None
        for i, pos in enumerate(self.open_positions):
            if pos['symbol'] == symbol:
                position = self.open_positions.pop(i)
                break
        
        if not position:
            logger.warning(f"[WARNING] Position not found: {symbol}")
            return None
        
        # Calculate PnL
        quantity = position['quantity']
        entry_price = position['entry_price']
        direction = position['direction']
        
        if direction == 'long':
            pnl = (exit_price - entry_price) * quantity
        else:  # short
            pnl = (entry_price - exit_price) * quantity
        
        pnl_pct = (pnl / position['position_value']) * 100
        
        # Update capital
        self.current_capital += pnl
        
        # Update peak capital for drawdown calculation
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now()
        position['pnl'] = pnl
        position['pnl_pct'] = pnl_pct
        
        logger.info(f"[RISK] Position closed: {symbol} @ ${exit_price:.2f}")
        logger.info(f"[RISK] PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
        logger.info(f"[RISK] Current capital: ${self.current_capital:.2f}")
        
        return position
    
    def get_current_drawdown(self) -> float:
        """
        Calculate current drawdown from peak
        
        Returns:
            Drawdown as decimal (e.g., 0.15 = 15%)
        """
        if self.peak_capital == 0:
            return 0.0
        
        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        return max(0.0, drawdown)
    
    def get_risk_metrics(self) -> Dict:
        """
        Get current risk metrics
        
        Returns:
            Dictionary with risk metrics
        """
        drawdown = self.get_current_drawdown()
        total_exposure = sum(pos['position_value'] for pos in self.open_positions)
        exposure_pct = (total_exposure / self.current_capital) if self.current_capital > 0 else 0
        
        return {
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'drawdown': drawdown,
            'drawdown_pct': drawdown * 100,
            'open_positions': len(self.open_positions),
            'total_exposure': total_exposure,
            'exposure_pct': exposure_pct,
            'daily_trades': self.daily_trades,
            'profit_loss': self.current_capital - self.initial_capital,
            'return_pct': ((self.current_capital / self.initial_capital) - 1) * 100
        }
    
    def reset(self, capital: float = None):
        """
        Reset risk manager (for backtesting)
        
        Args:
            capital: New initial capital (optional)
        """
        if capital:
            self.initial_capital = capital
        
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self.open_positions = []
        self.daily_trades = 0
        self.last_trade_date = None
        
        logger.info(f"[RISK] Risk Manager reset with ${self.initial_capital:,.2f}")
