"""
Backtesting Engine with Walk-Forward Validation
Calculates: Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

from src.data.market_data import MarketDataFetcher
from src.ml.predictor import MLPredictor
from src.sentiment.news_analyzer import NewsAnalyzer
from src.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class Backtester:
    """
    Backtesting engine with Walk-Forward validation
    Prevents data leakage and provides realistic performance metrics
    """
    
    def __init__(
        self,
        symbol: str = 'BTC/USDT',
        interval: str = '15m',
        initial_capital: float = 10000.0,
        risk_per_trade: float = 0.01,
        ml_threshold: float = 0.60,
        sentiment_threshold: float = -0.1,
        commission: float = 0.0006  # 0.06% Bybit maker/taker fee
    ):
        """
        Initialize Backtester
        
        Args:
            symbol: Trading pair
            interval: Timeframe for candles
            initial_capital: Starting capital in USDT
            risk_per_trade: Risk per trade (0.01 = 1%)
            ml_threshold: Minimum ML confidence to trade
            sentiment_threshold: Minimum sentiment score
            commission: Trading commission per trade
        """
        self.symbol = symbol
        self.interval = interval
        self.initial_capital = initial_capital
        self.commission = commission
        
        # Initialize components
        self.market_data = MarketDataFetcher(testnet=True)
        self.ml_predictor = MLPredictor()
        self.sentiment_analyzer = NewsAnalyzer()
        self.risk_manager = RiskManager(initial_capital=initial_capital)
        
        # Override risk_per_trade from constructor
        self.risk_manager.risk_per_trade = risk_per_trade
        
        # Trading parameters
        self.ml_threshold = ml_threshold
        self.sentiment_threshold = sentiment_threshold
        
        # Results storage
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.daily_returns: List[float] = []
        
        logger.info(f"[BACKTEST] Initialized for {symbol}")
        logger.info(f"[BACKTEST] Initial capital: ${initial_capital:,.2f}")
        logger.info(f"[BACKTEST] Commission: {commission*100:.2f}%")
    
    def walk_forward_validation(
        self,
        train_size: int = 400,
        test_size: int = 200,
        total_periods: int = 3
    ) -> Dict:
        """
        Walk-Forward Validation to prevent data leakage
        
        Args:
            train_size: Number of candles for training ML model
            test_size: Number of candles for testing strategy
            total_periods: Number of walk-forward windows
        
        Returns:
            Dictionary with aggregated results
        """
        logger.info("\n" + "="*80)
        logger.info("   WALK-FORWARD VALIDATION")
        logger.info("="*80)
        logger.info(f"[WF] Train size: {train_size} candles")
        logger.info(f"[WF] Test size: {test_size} candles")
        logger.info(f"[WF] Total periods: {total_periods}")
        
        # Fetch all available data once
        logger.info(f"\n[WF] Fetching historical data...")
        all_data = self._fetch_all_data()
        
        if all_data is None or len(all_data) < (train_size + test_size):
            logger.error(f"[WF] Insufficient data: need {train_size + test_size}, got {len(all_data) if all_data is not None else 0}")
            return {}
        
        logger.info(f"[WF] Retrieved {len(all_data)} candles total")
        
        all_results = []
        
        # Calculate total data needed
        total_needed = train_size + (test_size * total_periods)
        if len(all_data) < total_needed:
            logger.warning(f"[WF] Not enough data for {total_periods} periods, adjusting...")
            total_periods = (len(all_data) - train_size) // test_size
            logger.info(f"[WF] Using {total_periods} periods instead")
        
        for period in range(total_periods):
            logger.info(f"\n[WF] Period {period + 1}/{total_periods}")
            
            # Calculate indices for this period
            # Train on [start : train_end], test on [train_end : test_end]
            train_start = period * test_size
            train_end = train_start + train_size
            test_end = train_end + test_size
            
            # Slice data
            train_data = all_data.iloc[train_start:train_end].copy()
            test_data = all_data.iloc[train_end:test_end].copy()
            
            logger.info(f"[WF] Training on candles {train_start} to {train_end} ({len(train_data)} samples)")
            logger.info(f"[WF] Testing on candles {train_end} to {test_end} ({len(test_data)} samples)")
            
            if len(train_data) < 100 or len(test_data) < 50:
                logger.warning(f"[WF] Insufficient data for period {period + 1}")
                continue
            
            # Train model on training period
            logger.info(f"[WF] Training ML model...")
            
            # Split features and target (check both 'target' and 'Target')
            target_col = 'target' if 'target' in train_data.columns else 'Target'
            if target_col in train_data.columns:
                y_train = train_data[target_col]
                X_train = train_data.drop(columns=[target_col])
                
                # Remove 'Target' or 'target' if both exist somehow
                cols_to_drop = [c for c in ['target', 'Target'] if c in X_train.columns]
                if cols_to_drop:
                    X_train = X_train.drop(columns=cols_to_drop)
                
                self.ml_predictor.train(X_train, y_train)
            else:
                logger.warning(f"[WF] No target column in training data")
                continue
            
            # Test strategy on test period
            logger.info(f"[WF] Testing strategy...")
            period_results = self._backtest_period(test_data, period_id=period)
            
            if period_results:
                all_results.append(period_results)
        
        # Aggregate results
        if not all_results:
            logger.error("[WF] No valid periods for walk-forward validation")
            return {}
        
        logger.info("\n" + "="*80)
        logger.info("   WALK-FORWARD RESULTS")
        logger.info("="*80)
        
        aggregated = self._aggregate_wf_results(all_results)
        return aggregated
    
    def _fetch_all_data(self) -> Optional[pd.DataFrame]:
        """
        Fetch all available historical data
        
        Returns:
            DataFrame with OHLCV + indicators + target
        """
        try:
            logger.info(f"[DATA] Fetching 1000 candles...")
            
            # Fetch data
            df = self.market_data.fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.interval,
                limit=1000
            )
            
            if df is None or len(df) == 0:
                return None
            
            # Add indicators
            df = self.market_data.add_technical_indicators(df)
            
            # Create target
            df = self.market_data.create_ml_target(df)
            
            # Save Target before cleaning (note: capital T)
            if 'Target' in df.columns:
                target_series = df['Target'].copy()
            else:
                logger.error("[DATA] No Target column created")
                return None
            
            # Clean data
            df = self.market_data.prepare_features(df)
            
            # Add target back (lowercase for consistency)
            df['target'] = target_series.loc[df.index]
            
            logger.info(f"[DATA] Retrieved {len(df)} candles with indicators")
            return df
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch historical data: {e}")
            return None
    
    def _backtest_period(
        self,
        data: pd.DataFrame,
        period_id: int = 0
    ) -> Dict:
        """
        Backtest strategy on a specific period
        
        Args:
            data: DataFrame with OHLCV + indicators
            period_id: Period identifier for tracking
        
        Returns:
            Dictionary with period results
        """
        # Reset portfolio for this period
        capital = self.initial_capital
        peak_capital = capital
        positions = []
        period_trades = []
        
        # Data already has features and target, just use it
        features = data.copy()
        
        if features is None or len(features) == 0:
            return {}
        
        # Iterate through data (simulate real-time trading)
        for i in range(len(features)):
            current_data = features.iloc[:i+1]
            
            # Skip if not enough data
            if len(current_data) < 50:
                continue
            
            # Get current price and ATR
            current_price = current_data['close'].iloc[-1]
            current_atr = current_data['ATR'].iloc[-1] if 'ATR' in current_data else current_price * 0.02
            
            # Check for position exits first
            for position in positions[:]:
                exit_price = None
                exit_reason = None
                
                # Check stop-loss
                if position['side'] == 'long':
                    if current_price <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'stop_loss'
                    elif current_price >= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'take_profit'
                else:  # short
                    if current_price >= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'stop_loss'
                    elif current_price <= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'take_profit'
                
                # Exit position if triggered
                if exit_price:
                    pnl = self._calculate_pnl(position, exit_price)
                    capital += pnl
                    peak_capital = max(peak_capital, capital)
                    
                    # Record trade
                    trade = {
                        'period': period_id,
                        'entry_time': position['entry_time'],
                        'exit_time': i,
                        'side': position['side'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'pnl_pct': (pnl / position['position_size']) * 100,
                        'exit_reason': exit_reason
                    }
                    period_trades.append(trade)
                    positions.remove(position)
            
            # Generate new signal if no positions
            if len(positions) == 0:
                signal = self._generate_signal(current_data)
                
                if signal and signal['should_trade']:
                    # Calculate position size
                    position_size = capital * self.risk_manager.risk_per_trade
                    quantity = position_size / current_price
                    
                    # Calculate SL/TP
                    if signal['direction'] == 'long':
                        stop_loss = current_price - (2 * current_atr)
                        take_profit = current_price + (3 * current_atr)
                    else:  # short
                        stop_loss = current_price + (2 * current_atr)
                        take_profit = current_price - (3 * current_atr)
                    
                    # Open position
                    position = {
                        'entry_time': i,
                        'side': signal['direction'],
                        'entry_price': current_price,
                        'quantity': quantity,
                        'position_size': position_size,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }
                    positions.append(position)
        
        # Close any remaining positions at end
        if positions:
            final_price = features['close'].iloc[-1]
            for position in positions:
                pnl = self._calculate_pnl(position, final_price)
                capital += pnl
                
                trade = {
                    'period': period_id,
                    'entry_time': position['entry_time'],
                    'exit_time': len(features) - 1,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': final_price,
                    'quantity': position['quantity'],
                    'pnl': pnl,
                    'pnl_pct': (pnl / position['position_size']) * 100,
                    'exit_reason': 'period_end'
                }
                period_trades.append(trade)
        
        # Calculate period metrics
        results = self._calculate_period_metrics(period_trades, capital, peak_capital)
        results['period_id'] = period_id
        results['trades'] = period_trades
        
        logger.info(f"[PERIOD {period_id}] Trades: {len(period_trades)}, "
                   f"Final capital: ${capital:,.2f}, "
                   f"Return: {((capital/self.initial_capital - 1)*100):.2f}%")
        
        return results
    
    def _generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """
        Generate trading signal using ML + Sentiment
        
        Args:
            data: DataFrame with features
        
        Returns:
            Signal dictionary or None
        """
        try:
            # ML prediction - pass last row as Series (without target column)
            last_row = data.iloc[-1]
            
            # Remove target column if present
            if 'target' in last_row.index:
                last_row = last_row.drop(['target'])
            if 'Target' in last_row.index:
                last_row = last_row.drop(['Target'])
            
            ml_signal, ml_confidence = self.ml_predictor.predict_single(last_row)
            
            # Sentiment (use cached/neutral if no news)
            sentiment = {'score': 0.0, 'label': 'neutral'}
            
            # Check thresholds
            if ml_confidence < self.ml_threshold:
                return None
            
            if sentiment['score'] < self.sentiment_threshold:
                return None
            
            # Determine direction
            direction = 'long' if ml_signal == 'UP' else 'short'
            
            return {
                'should_trade': True,
                'direction': direction,
                'ml_signal': ml_signal,
                'ml_confidence': ml_confidence,
                'sentiment': sentiment
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Signal generation failed: {e}")
            return None
    
    def _calculate_pnl(self, position: Dict, exit_price: float) -> float:
        """
        Calculate PnL for a position including commission
        
        Args:
            position: Position dictionary
            exit_price: Exit price
        
        Returns:
            PnL in USDT
        """
        if position['side'] == 'long':
            gross_pnl = (exit_price - position['entry_price']) * position['quantity']
        else:  # short
            gross_pnl = (position['entry_price'] - exit_price) * position['quantity']
        
        # Subtract commissions (entry + exit)
        commission = position['position_size'] * self.commission * 2
        net_pnl = gross_pnl - commission
        
        return net_pnl
    
    def _calculate_period_metrics(
        self,
        trades: List[Dict],
        final_capital: float,
        peak_capital: float
    ) -> Dict:
        """
        Calculate performance metrics for a period
        
        Args:
            trades: List of trades
            final_capital: Final capital
            peak_capital: Peak capital reached
        
        Returns:
            Dictionary with metrics
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0
            }
        
        # Win rate
        winning_trades = [t for t in trades if t['pnl'] > 0]
        win_rate = (len(winning_trades) / len(trades)) * 100
        
        # Total return
        total_return = ((final_capital / self.initial_capital) - 1) * 100
        
        # Max drawdown
        max_drawdown = ((peak_capital - final_capital) / peak_capital) * 100 if peak_capital > 0 else 0
        
        # Profit factor
        total_wins = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        total_losses = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        
        # Sharpe ratio (simplified - using trade returns)
        returns = [t['pnl_pct'] for t in trades]
        if len(returns) > 1:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(trades) - len(winning_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'final_capital': final_capital,
            'peak_capital': peak_capital,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': profit_factor,
            'avg_win': np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if winning_trades else 0,
            'avg_loss': np.mean([t['pnl'] for t in trades if t['pnl'] < 0]) if len(trades) > len(winning_trades) else 0
        }
    
    def _aggregate_wf_results(self, all_results: List[Dict]) -> Dict:
        """
        Aggregate results from all walk-forward periods
        
        Args:
            all_results: List of period results
        
        Returns:
            Aggregated metrics
        """
        total_trades = sum(r['total_trades'] for r in all_results)
        total_winning = sum(r['winning_trades'] for r in all_results)
        
        # Average metrics
        avg_win_rate = np.mean([r['win_rate'] for r in all_results])
        avg_return = np.mean([r['total_return'] for r in all_results])
        avg_drawdown = np.mean([r['max_drawdown'] for r in all_results])
        avg_sharpe = np.mean([r['sharpe_ratio'] for r in all_results])
        avg_profit_factor = np.mean([r['profit_factor'] for r in all_results])
        
        # Final capital (compounded across periods)
        final_capital = self.initial_capital
        for r in all_results:
            period_return = r['total_return'] / 100
            final_capital = final_capital * (1 + period_return)
        
        total_return = ((final_capital / self.initial_capital) - 1) * 100
        
        aggregated = {
            'periods': len(all_results),
            'total_trades': total_trades,
            'winning_trades': total_winning,
            'losing_trades': total_trades - total_winning,
            'win_rate': avg_win_rate,
            'total_return': total_return,
            'final_capital': final_capital,
            'avg_period_return': avg_return,
            'avg_max_drawdown': avg_drawdown,
            'avg_sharpe_ratio': avg_sharpe,
            'avg_profit_factor': avg_profit_factor,
            'period_results': all_results
        }
        
        # Print summary
        logger.info(f"\n[SUMMARY] Walk-Forward Results:")
        logger.info(f"  Periods:          {aggregated['periods']}")
        logger.info(f"  Total Trades:     {aggregated['total_trades']}")
        logger.info(f"  Win Rate:         {aggregated['win_rate']:.1f}%")
        logger.info(f"  Total Return:     {aggregated['total_return']:+.2f}%")
        logger.info(f"  Final Capital:    ${aggregated['final_capital']:,.2f}")
        logger.info(f"  Avg Drawdown:     {aggregated['avg_max_drawdown']:.2f}%")
        logger.info(f"  Avg Sharpe:       {aggregated['avg_sharpe_ratio']:.2f}")
        logger.info(f"  Avg Profit Factor: {aggregated['avg_profit_factor']:.2f}")
        
        return aggregated
    
    def plot_equity_curve(
        self,
        results: Dict,
        save_path: str = 'data/backtest_equity_curve.png'
    ):
        """
        Plot equity curve with buy&hold comparison
        
        Args:
            results: Results from walk_forward_validation
            save_path: Path to save plot
        """
        try:
            if 'period_results' not in results:
                logger.warning("[PLOT] No period results to plot")
                return
            
            # Aggregate all trades
            all_trades = []
            for period_result in results['period_results']:
                all_trades.extend(period_result.get('trades', []))
            
            if not all_trades:
                logger.warning("[PLOT] No trades to plot")
                return
            
            # Build equity curve
            capital = self.initial_capital
            equity_curve = [capital]
            
            for trade in all_trades:
                capital += trade['pnl']
                equity_curve.append(capital)
            
            # Create plot
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
            
            # Plot 1: Equity Curve
            ax1.plot(range(len(equity_curve)), equity_curve, 
                    linewidth=2, label='Strategy', color='#2E86AB')
            ax1.axhline(y=self.initial_capital, color='gray', 
                       linestyle='--', alpha=0.5, label='Initial Capital')
            ax1.fill_between(range(len(equity_curve)), self.initial_capital, 
                            equity_curve, alpha=0.1, color='#2E86AB')
            ax1.set_title('Backtest Equity Curve', fontsize=14, fontweight='bold')
            ax1.set_xlabel('Trade Number', fontsize=11)
            ax1.set_ylabel('Capital (USDT)', fontsize=11)
            ax1.legend(loc='upper left', fontsize=10)
            ax1.grid(True, alpha=0.3)
            
            # Add metrics text
            metrics_text = (
                f"Total Return: {results['total_return']:+.2f}%\n"
                f"Win Rate: {results['win_rate']:.1f}%\n"
                f"Sharpe Ratio: {results['avg_sharpe_ratio']:.2f}\n"
                f"Max Drawdown: {results['avg_max_drawdown']:.2f}%\n"
                f"Total Trades: {results['total_trades']}"
            )
            ax1.text(0.02, 0.98, metrics_text, transform=ax1.transAxes,
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            # Plot 2: Drawdown
            peak = self.initial_capital
            drawdowns = []
            for equity in equity_curve:
                peak = max(peak, equity)
                dd = ((peak - equity) / peak) * 100 if peak > 0 else 0
                drawdowns.append(dd)
            
            ax2.fill_between(range(len(drawdowns)), 0, drawdowns, 
                            color='#A23B72', alpha=0.6)
            ax2.set_title('Drawdown', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Trade Number', fontsize=11)
            ax2.set_ylabel('Drawdown (%)', fontsize=11)
            ax2.grid(True, alpha=0.3)
            ax2.invert_yaxis()
            
            plt.tight_layout()
            
            # Save plot
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"[PLOT] Equity curve saved to {save_path}")
            
            plt.close()
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to plot equity curve: {e}")
    
    def export_results(
        self,
        results: Dict,
        output_path: str = 'data/backtest_results.csv'
    ):
        """
        Export backtest results to CSV
        
        Args:
            results: Results from walk_forward_validation
            output_path: Path to save CSV
        """
        try:
            # Aggregate all trades
            all_trades = []
            for period_result in results['period_results']:
                all_trades.extend(period_result.get('trades', []))
            
            if not all_trades:
                logger.warning("[EXPORT] No trades to export")
                return
            
            # Create DataFrame
            df = pd.DataFrame(all_trades)
            
            # Save to CSV
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)
            
            logger.info(f"[EXPORT] Results saved to {output_path}")
            logger.info(f"[EXPORT] Total trades exported: {len(all_trades)}")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to export results: {e}")
