"""
Trading Executor
================
Combines ML predictions, sentiment, and risk management to execute trades.
Manages open positions, stop-loss, and take-profit orders.
"""

import ccxt
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import time
import pandas as pd

from ..config.config_loader import get_config
from ..data.market_data import MarketDataFetcher
from ..ml.predictor import MLPredictor
from ..sentiment.news_analyzer import NewsAnalyzer
from ..risk.risk_manager import RiskManager
from ..utils.trade_logger import TradeLogger


logger = logging.getLogger(__name__)


class TradingExecutor:
    """
    Main trading executor - orchestrates all components
    """
    
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        testnet: bool = True,
        dry_run: bool = False,
        analyze_only: bool = False,
        initial_capital: float = None
    ):
        """
        Initialize trading executor
        
        Args:
            api_key: Exchange API key
            api_secret: Exchange API secret
            testnet: Use testnet if True
            dry_run: Simulate trades without execution
            analyze_only: Only analyze market, do not trade
            initial_capital: Starting capital in USDT
        """
        self.config = get_config()
        self.dry_run = dry_run
        self.analyze_only = analyze_only
        
        # Initialize components
        self.data_fetcher = MarketDataFetcher(api_key, api_secret, testnet)
        self.predictor = MLPredictor()
        self.sentiment_analyzer = NewsAnalyzer()
        self.risk_manager = RiskManager(initial_capital)
        self.portfolio_manager = self.risk_manager  # Alias for web access
        self.trade_logger = TradeLogger()
        
        # Exchange connection
        self.exchange = self.data_fetcher.exchange
        self.testnet = testnet
        
        # Trading parameters
        self.ml_threshold = self.config.get('trading', 'entry', 'ml_probability_min', default=0.60)
        self.sentiment_threshold = self.config.get('trading', 'entry', 'sentiment_min', default=-0.1)
        
        # Active positions tracking
        self.active_positions: Dict[str, Dict] = {}
        
        # Try to load existing model, if not found will train on first analysis
        self._model_loaded = False
        try:
            self.predictor.load_model()
            self._model_loaded = True
            logger.info("[EXECUTOR] ML model loaded from file")
        except Exception as e:
            logger.warning(f"[EXECUTOR] Could not load ML model: {e}")
            logger.info("[EXECUTOR] Model will be trained on first analysis")
        
        logger.info(f"[EXECUTOR] Trading Executor initialized ({'TESTNET' if testnet else 'MAINNET'})")
        logger.info(f"[EXECUTOR] ML threshold: {self.ml_threshold:.2%}, Sentiment: {self.sentiment_threshold}")
    
    def analyze_and_trade(self, symbol: str = 'BTC/USDT', dry_run: bool = False) -> Dict:
        """
        Perform one complete trading iteration: analyze + signal + trade
        
        Args:
            symbol: Trading symbol
            dry_run: Simulate trades without execution
            
        Returns:
            Dictionary with iteration results
        """
        result = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'analysis': None,
            'signal': None,
            'trade': None,
            'positions_checked': False
        }
        
        try:
            # Check existing positions first
            if self.active_positions:
                logger.info(f"\n[CHECK] Checking {len(self.active_positions)} active positions...")
                self.check_positions()
                result['positions_checked'] = True
            
            # Market analysis
            logger.info(f"\n[ANALYZE] Starting analysis for {symbol}...")
            analysis = self.analyze_market(symbol)
            result['analysis'] = {
                'price': analysis['price'],
                'ml_signal': analysis['ml_signal'],
                'ml_confidence': analysis['ml_confidence'],
                'sentiment': analysis['sentiment_label']
            }
            
            # Generate signal
            should_trade, reason, direction = self.generate_signal(analysis)
            result['signal'] = {
                'should_trade': should_trade,
                'reason': reason,
                'direction': direction
            }
            
            logger.info(f"\n[SIGNAL] {symbol}: {'TRADE' if should_trade else 'NO TRADE'}")
            logger.info(f"[SIGNAL] Reason: {reason}")
            
            # Execute trade if signal is positive
            if should_trade:
                trade_result = self.execute_trade(analysis, direction, dry_run=dry_run)
                result['trade'] = trade_result
                
                if trade_result:
                    logger.info(f"[SUCCESS] Trade executed: {direction.upper()} {symbol}")
                else:
                    logger.warning(f"[FAILED] Trade execution failed")
            
            # Log portfolio status
            self._log_portfolio_status()
            
        except Exception as e:
            logger.error(f"[ERROR] Trading iteration failed: {e}", exc_info=True)
            result['error'] = str(e)
        
        return result
    
    def _log_portfolio_status(self):
        """Log current portfolio status"""
        logger.info(f"\n{'='*80}")
        logger.info(f"[PORTFOLIO] Status")
        logger.info(f"{'='*80}")
        
        capital = self.risk_manager.current_capital
        positions = len(self.active_positions)
        max_positions = self.risk_manager.max_positions
        exposure = sum(pos.get('size', 0) * pos.get('entry_price', 0) 
                      for pos in self.active_positions.values())
        exposure_pct = (exposure / capital * 100) if capital > 0 else 0
        
        drawdown = self.risk_manager.current_drawdown
        total_pnl = self.risk_manager.total_pnl
        total_pnl_pct = (total_pnl / self.risk_manager.initial_capital * 100) if self.risk_manager.initial_capital > 0 else 0
        
        logger.info(f"  Capital:    ${capital:,.2f}")
        logger.info(f"  Positions:  {positions}/{max_positions}")
        logger.info(f"  Exposure:   ${exposure:,.2f} ({exposure_pct:.1f}%)")
        logger.info(f"  Drawdown:   {drawdown:.2f}%")
        logger.info(f"  PnL:        ${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")
        logger.info(f"{'='*80}\n")
    
    def analyze_market(self, symbol: str = 'BTC/USDT') -> Dict:
        """
        Perform complete market analysis
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"\n[ANALYZE] Starting analysis for {symbol}...")
        
        # Fetch market data
        df = self.data_fetcher.fetch_ohlcv(symbol)
        df = self.data_fetcher.add_technical_indicators(df)
        df = self.data_fetcher.create_ml_target(df)
        df = self.data_fetcher.prepare_features(df)
        
        # Remove duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Get current market state
        current_price = df['close'].iloc[-1]
        current_atr = df['ATR'].iloc[-1]
        
        # Train model if not loaded
        if not self._model_loaded:
            logger.info("[TRAIN] Training ML model (first run)...")
            X, y, features = self.predictor.prepare_data(df)
            metrics = self.predictor.train(X, y, validation_split=0.2)
            self.predictor.save_model()
            self._model_loaded = True
            logger.info("[TRAIN] Model trained and saved")
        
        # ML prediction
        X, y, features = self.predictor.prepare_data(df)
        last_row = X.iloc[-1]
        
        if isinstance(last_row, pd.Series) and last_row.index.duplicated().any():
            last_row = last_row[~last_row.index.duplicated(keep='first')]
        
        ml_prediction, ml_confidence = self.predictor.predict_single(last_row)
        ml_signal = "UP" if ml_prediction == 1 else "DOWN"
        
        # Sentiment analysis
        symbol_short = symbol.split('/')[0]
        sentiment = self.sentiment_analyzer.get_sentiment(symbol_short)
        
        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'price': current_price,
            'atr': current_atr,
            'ml_signal': ml_signal,
            'ml_confidence': ml_confidence,
            'sentiment_score': sentiment['score'],
            'sentiment_label': sentiment['label'],
            'dataframe': df
        }
        
        logger.info(f"[ANALYZE] Price: ${current_price:.2f}, ATR: ${current_atr:.2f}")
        logger.info(f"[ANALYZE] ML: {ml_signal} ({ml_confidence:.2%})")
        logger.info(f"[ANALYZE] Sentiment: {sentiment['label']} ({sentiment['score']:.4f})")
        
        # Log analysis to database
        rsi_value = df['RSI'].iloc[-1] if 'RSI' in df.columns else None
        self.trade_logger.log_analysis(
            symbol=symbol,
            price=current_price,
            atr=current_atr,
            ml_signal=ml_signal,
            ml_confidence=ml_confidence,
            sentiment_score=sentiment['score'],
            sentiment_label=sentiment['label'],
            decision='pending',  # Will be updated after signal generation
            rsi=rsi_value
        )
        
        return analysis
    
    def generate_signal(self, analysis: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        Generate trading signal based on analysis
        
        Args:
            analysis: Market analysis results
        
        Returns:
            Tuple of (should_trade, reason, direction)
        """
        # Check ML confidence
        if analysis['ml_confidence'] < self.ml_threshold:
            return False, f"ML confidence too low: {analysis['ml_confidence']:.2%} < {self.ml_threshold:.2%}", None
        
        # Check sentiment
        if analysis['sentiment_score'] < self.sentiment_threshold:
            return False, f"Sentiment too negative: {analysis['sentiment_score']:.4f} < {self.sentiment_threshold}", None
        
        # Check risk management
        can_trade, risk_reason = self.risk_manager.can_open_position()
        if not can_trade:
            return False, f"Risk check failed: {risk_reason}", None
        
        # Check if already have position in this symbol
        if analysis['symbol'] in self.active_positions:
            return False, f"Already have open position in {analysis['symbol']}", None
        
        # All checks passed
        direction = 'long' if analysis['ml_signal'] == 'UP' else 'short'
        return True, "All checks passed", direction
    
    def execute_trade(self, analysis: Dict, direction: str, dry_run: bool = False) -> Optional[Dict]:
        """
        Execute trade on exchange
        
        Args:
            analysis: Market analysis
            direction: 'long' or 'short'
            dry_run: If True, simulate trade without actual execution
        
        Returns:
            Trade execution result or None
        """
        symbol = analysis['symbol']
        current_price = analysis['price']
        atr = analysis['atr']
        
        # Calculate stop-loss and take-profit
        stop_loss = self.risk_manager.calculate_stop_loss(current_price, atr, direction)
        take_profit = self.risk_manager.calculate_take_profit(current_price, atr, direction)
        
        # Calculate position size
        position_size, quantity = self.risk_manager.calculate_position_size(
            current_price,
            stop_loss,
            method='fixed'
        )
        
        # Round quantity to exchange precision
        quantity = self._round_quantity(symbol, quantity)
        
        logger.info(f"\n[EXECUTE] {'DRY RUN - ' if dry_run else ''}Executing {direction.upper()} trade")
        logger.info(f"[EXECUTE] Symbol: {symbol}")
        logger.info(f"[EXECUTE] Price: ${current_price:.2f}")
        logger.info(f"[EXECUTE] Quantity: {quantity}")
        logger.info(f"[EXECUTE] Position Size: ${position_size:.2f}")
        logger.info(f"[EXECUTE] Stop-Loss: ${stop_loss:.2f}")
        logger.info(f"[EXECUTE] Take-Profit: ${take_profit:.2f}")
        
        if dry_run:
            # Simulate trade
            trade_result = {
                'symbol': symbol,
                'side': 'buy' if direction == 'long' else 'sell',
                'type': 'market',
                'price': current_price,
                'quantity': quantity,
                'position_size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'timestamp': datetime.now(),
                'order_id': f"DRY_RUN_{int(time.time())}",
                'status': 'simulated'
            }
            
            logger.info(f"[EXECUTE] DRY RUN - Trade simulated successfully")
        else:
            # Real trade execution
            try:
                # Place market order
                side = 'buy' if direction == 'long' else 'sell'
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=quantity
                )
                
                # Place stop-loss order
                sl_order = self._place_stop_loss(symbol, quantity, stop_loss, direction)
                
                # Place take-profit order
                tp_order = self._place_take_profit(symbol, quantity, take_profit, direction)
                
                trade_result = {
                    'symbol': symbol,
                    'side': side,
                    'type': 'market',
                    'price': order.get('price', current_price),
                    'quantity': quantity,
                    'position_size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'timestamp': datetime.now(),
                    'order_id': order['id'],
                    'status': order['status'],
                    'sl_order_id': sl_order.get('id') if sl_order else None,
                    'tp_order_id': tp_order.get('id') if tp_order else None
                }
                
                logger.info(f"[EXECUTE] Trade executed successfully - Order ID: {order['id']}")
                
            except Exception as e:
                logger.error(f"[ERROR] Trade execution failed: {e}")
                return None
        
        # Register position with risk manager
        position = self.risk_manager.add_position(
            symbol=symbol,
            entry_price=current_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            direction=direction
        )
        
        # Log trade to database
        trade_id = self.trade_logger.log_trade_open(
            symbol=symbol,
            side=trade_result['side'],
            entry_price=current_price,
            quantity=quantity,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            direction=direction,
            ml_confidence=analysis.get('ml_confidence'),
            sentiment_score=analysis.get('sentiment_score'),
            order_id=trade_result.get('order_id')
        )
        
        # Add to active positions
        self.active_positions[symbol] = {
            **trade_result,
            'position': position,
            'trade_id': trade_id
        }
        
        # Log event
        self.trade_logger.log_event(
            'trade_open',
            'info',
            f"Position opened: {symbol} {direction.upper()} @ ${current_price:.2f}",
            f"Size: ${position_size:.2f}, SL: ${stop_loss:.2f}, TP: ${take_profit:.2f}"
        )
        
        return trade_result
    
    def _place_stop_loss(self, symbol: str, quantity: float, stop_price: float, direction: str) -> Optional[Dict]:
        """
        Place stop-loss order
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            stop_price: Stop-loss trigger price
            direction: 'long' or 'short'
        
        Returns:
            Order result or None
        """
        try:
            side = 'sell' if direction == 'long' else 'buy'
            
            # Bybit stop-loss order
            order = self.exchange.create_order(
                symbol=symbol,
                type='stop_market',
                side=side,
                amount=quantity,
                params={
                    'stopPrice': stop_price,
                    'triggerBy': 'LastPrice'
                }
            )
            
            logger.info(f"[SL] Stop-loss placed at ${stop_price:.2f}")
            return order
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to place stop-loss: {e}")
            return None
    
    def _place_take_profit(self, symbol: str, quantity: float, tp_price: float, direction: str) -> Optional[Dict]:
        """
        Place take-profit order
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            tp_price: Take-profit trigger price
            direction: 'long' or 'short'
        
        Returns:
            Order result or None
        """
        try:
            side = 'sell' if direction == 'long' else 'buy'
            
            # Bybit take-profit order
            order = self.exchange.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=quantity,
                price=tp_price
            )
            
            logger.info(f"[TP] Take-profit placed at ${tp_price:.2f}")
            return order
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to place take-profit: {e}")
            return None
    
    def _round_quantity(self, symbol: str, quantity: float) -> float:
        """
        Round quantity to exchange precision
        
        Args:
            symbol: Trading symbol
            quantity: Raw quantity
        
        Returns:
            Rounded quantity
        """
        try:
            markets = self.exchange.load_markets()
            precision = markets[symbol]['precision']['amount']
            
            if precision is not None:
                return round(quantity, precision)
        except Exception as e:
            logger.warning(f"[WARNING] Could not get precision for {symbol}: {e}")
        
        # Default to 6 decimals for crypto
        return round(quantity, 6)
    
    def check_positions(self) -> List[Dict]:
        """
        Check status of all active positions
        
        Returns:
            List of position updates
        """
        updates = []
        
        for symbol, position_data in list(self.active_positions.items()):
            try:
                # Get current price
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                position = position_data['position']
                entry_price = position['entry_price']
                stop_loss = position['stop_loss']
                take_profit = position['take_profit']
                direction = position['direction']
                
                # Calculate current PnL
                if direction == 'long':
                    pnl = (current_price - entry_price) * position['quantity']
                    pnl_pct = ((current_price / entry_price) - 1) * 100
                else:
                    pnl = (entry_price - current_price) * position['quantity']
                    pnl_pct = ((entry_price / current_price) - 1) * 100
                
                # Check if hit stop-loss or take-profit
                should_close = False
                close_reason = None
                
                if direction == 'long':
                    if current_price <= stop_loss:
                        should_close = True
                        close_reason = 'stop_loss'
                    elif current_price >= take_profit:
                        should_close = True
                        close_reason = 'take_profit'
                else:  # short
                    if current_price >= stop_loss:
                        should_close = True
                        close_reason = 'stop_loss'
                    elif current_price <= take_profit:
                        should_close = True
                        close_reason = 'take_profit'
                
                update = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'should_close': should_close,
                    'close_reason': close_reason
                }
                
                updates.append(update)
                
                # Log position status
                logger.info(f"[POSITION] {symbol}: ${current_price:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
                
                # Close position if needed
                if should_close:
                    logger.info(f"[CLOSE] Closing {symbol} - Reason: {close_reason}")
                    self.close_position(symbol, current_price)
                
            except Exception as e:
                logger.error(f"[ERROR] Failed to check position {symbol}: {e}")
        
        return updates
    
    def close_position(self, symbol: str, exit_price: float = None, dry_run: bool = False) -> Optional[Dict]:
        """
        Close an open position
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price (if None, use current market price)
            dry_run: Simulate close without execution
        
        Returns:
            Close result or None
        """
        if symbol not in self.active_positions:
            logger.warning(f"[WARNING] No active position for {symbol}")
            return None
        
        position_data = self.active_positions[symbol]
        position = position_data['position']
        
        # Get current price if not provided
        if exit_price is None:
            ticker = self.exchange.fetch_ticker(symbol)
            exit_price = ticker['last']
        
        logger.info(f"[CLOSE] {'DRY RUN - ' if dry_run else ''}Closing position {symbol} @ ${exit_price:.2f}")
        
        if not dry_run:
            try:
                # Close market position
                side = 'sell' if position['direction'] == 'long' else 'buy'
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=position['quantity']
                )
                
                # Cancel stop-loss and take-profit orders
                if position_data.get('sl_order_id'):
                    try:
                        self.exchange.cancel_order(position_data['sl_order_id'], symbol)
                    except:
                        pass
                
                if position_data.get('tp_order_id'):
                    try:
                        self.exchange.cancel_order(position_data['tp_order_id'], symbol)
                    except:
                        pass
                
                logger.info(f"[CLOSE] Position closed - Order ID: {order['id']}")
                
            except Exception as e:
                logger.error(f"[ERROR] Failed to close position: {e}")
                return None
        
        # Update risk manager
        closed_position = self.risk_manager.close_position(symbol, exit_price)
        
        # Log trade close to database
        if position_data.get('trade_id') and closed_position:
            self.trade_logger.log_trade_close(
                trade_id=position_data['trade_id'],
                exit_price=exit_price,
                pnl=closed_position['pnl'],
                pnl_pct=closed_position['pnl_pct'],
                exit_reason='manual' if not dry_run else 'simulated'
            )
            
            # Log event
            self.trade_logger.log_event(
                'trade_close',
                'info',
                f"Position closed: {symbol} @ ${exit_price:.2f}",
                f"PnL: ${closed_position['pnl']:+.2f} ({closed_position['pnl_pct']:+.2f}%)"
            )
        
        # Remove from active positions
        del self.active_positions[symbol]
        
        return closed_position
    
    def run_trading_loop(
        self,
        symbols: List[str] = None,
        interval_seconds: int = 900,
        dry_run: bool = True
    ):
        """
        Main trading loop
        
        Args:
            symbols: List of symbols to trade (default from config)
            interval_seconds: Time between iterations (default 15 min)
            dry_run: Simulate trades without execution
        """
        if symbols is None:
            symbols = self.config.get('symbols', default=['BTC/USDT'])
        
        logger.info(f"\n{'='*80}")
        logger.info(f"[LOOP] Starting trading loop ({'DRY RUN' if dry_run else 'LIVE'})")
        logger.info(f"[LOOP] Symbols: {symbols}")
        logger.info(f"[LOOP] Interval: {interval_seconds}s ({interval_seconds/60:.0f} min)")
        logger.info(f"{'='*80}\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"[LOOP] Iteration #{iteration} - {datetime.now()}")
                logger.info(f"{'='*80}")
                
                # Check existing positions first
                if self.active_positions:
                    logger.info(f"\n[CHECK] Checking {len(self.active_positions)} active positions...")
                    self.check_positions()
                
                # Analyze each symbol
                for symbol in symbols:
                    try:
                        # Market analysis
                        analysis = self.analyze_market(symbol)
                        
                        # Generate signal
                        should_trade, reason, direction = self.generate_signal(analysis)
                        
                        logger.info(f"\n[SIGNAL] {symbol}: {'TRADE' if should_trade else 'NO TRADE'}")
                        logger.info(f"[SIGNAL] Reason: {reason}")
                        
                        if should_trade and direction:
                            # Execute trade
                            trade = self.execute_trade(analysis, direction, dry_run=dry_run)
                            
                            if trade:
                                logger.info(f"[SUCCESS] Trade executed for {symbol}")
                        
                    except Exception as e:
                        logger.error(f"[ERROR] Failed to process {symbol}: {e}")
                        continue
                
                # Display portfolio status
                metrics = self.risk_manager.get_risk_metrics()
                logger.info(f"\n{'='*80}")
                logger.info(f"[PORTFOLIO] Status")
                logger.info(f"{'='*80}")
                logger.info(f"  Capital:    ${metrics['current_capital']:,.2f}")
                logger.info(f"  Positions:  {metrics['open_positions']}/{self.risk_manager.max_open_positions}")
                logger.info(f"  Exposure:   ${metrics['total_exposure']:,.2f} ({metrics['exposure_pct']:.1%})")
                logger.info(f"  Drawdown:   {metrics['drawdown_pct']:.2f}%")
                logger.info(f"  PnL:        ${metrics['profit_loss']:+,.2f} ({metrics['return_pct']:+.2f}%)")
                logger.info(f"{'='*80}\n")
                
                # Wait for next iteration
                logger.info(f"[SLEEP] Waiting {interval_seconds}s until next iteration...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("\n[STOP] Trading loop interrupted by user")
            
            # Close all positions on exit
            if self.active_positions:
                logger.info(f"[CLEANUP] Closing {len(self.active_positions)} open positions...")
                for symbol in list(self.active_positions.keys()):
                    self.close_position(symbol, dry_run=dry_run)
            
            logger.info("[STOP] Trading loop stopped")
