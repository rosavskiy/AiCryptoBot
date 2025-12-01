"""
Trade Logger
============
Logs all trades and system events to SQLite database.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

from ..config.config_loader import get_config


logger = logging.getLogger(__name__)


class TradeLogger:
    """
    Logs trades and events to SQLite database
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize trade logger
        
        Args:
            db_path: Path to SQLite database file
        """
        self.config = get_config()
        
        if db_path is None:
            db_path = self.config.get('logging', 'database', 'path', default='data/trading.db')
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        logger.info(f"[DB] Trade Logger initialized: {self.db_path}")
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                position_size REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                direction TEXT NOT NULL,
                status TEXT NOT NULL,
                pnl REAL,
                pnl_pct REAL,
                ml_confidence REAL,
                sentiment_score REAL,
                order_id TEXT,
                exit_reason TEXT,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                duration_seconds INTEGER
            )
        ''')
        
        # Events table (system events, errors, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT
            )
        ''')
        
        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                capital REAL NOT NULL,
                peak_capital REAL NOT NULL,
                drawdown REAL NOT NULL,
                open_positions INTEGER NOT NULL,
                total_exposure REAL NOT NULL,
                daily_trades INTEGER NOT NULL,
                total_pnl REAL NOT NULL,
                win_rate REAL,
                avg_win REAL,
                avg_loss REAL,
                sharpe_ratio REAL
            )
        ''')
        
        # Market analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                atr REAL NOT NULL,
                rsi REAL,
                ml_signal TEXT NOT NULL,
                ml_confidence REAL NOT NULL,
                sentiment_score REAL NOT NULL,
                sentiment_label TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("[DB] Database tables initialized")
    
    def log_trade_open(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        position_size: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
        ml_confidence: float = None,
        sentiment_score: float = None,
        order_id: str = None
    ) -> int:
        """
        Log trade opening
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            entry_price: Entry price
            quantity: Position quantity
            position_size: Position size in USDT
            stop_loss: Stop-loss price
            take_profit: Take-profit price
            direction: 'long' or 'short'
            ml_confidence: ML model confidence
            sentiment_score: Sentiment score
            order_id: Exchange order ID
        
        Returns:
            Trade ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO trades (
                timestamp, symbol, side, entry_price, quantity, position_size,
                stop_loss, take_profit, direction, status, ml_confidence,
                sentiment_score, order_id, entry_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, symbol, side, entry_price, quantity, position_size,
            stop_loss, take_profit, direction, 'open', ml_confidence,
            sentiment_score, order_id, timestamp
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"[DB] Trade opened: ID={trade_id}, {symbol} {direction.upper()}")
        
        return trade_id
    
    def log_trade_close(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        exit_reason: str = None
    ):
        """
        Log trade closing
        
        Args:
            trade_id: Trade ID from log_trade_open
            exit_price: Exit price
            pnl: Profit/Loss in USDT
            pnl_pct: Profit/Loss percentage
            exit_reason: Reason for closing (stop_loss, take_profit, manual, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        exit_time = datetime.now().isoformat()
        
        # Get entry time to calculate duration
        cursor.execute('SELECT entry_time FROM trades WHERE id = ?', (trade_id,))
        result = cursor.fetchone()
        
        if result:
            entry_time = datetime.fromisoformat(result[0])
            exit_datetime = datetime.fromisoformat(exit_time)
            duration = int((exit_datetime - entry_time).total_seconds())
        else:
            duration = None
        
        cursor.execute('''
            UPDATE trades
            SET exit_price = ?, pnl = ?, pnl_pct = ?, status = ?,
                exit_reason = ?, exit_time = ?, duration_seconds = ?
            WHERE id = ?
        ''', (exit_price, pnl, pnl_pct, 'closed', exit_reason, exit_time, duration, trade_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[DB] Trade closed: ID={trade_id}, PnL=${pnl:+.2f} ({pnl_pct:+.2f}%)")
    
    def log_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: str = None
    ):
        """
        Log system event
        
        Args:
            event_type: Type of event (trade, error, warning, info, etc.)
            severity: Severity level (info, warning, error, critical)
            message: Event message
            details: Additional details (JSON, text, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO events (timestamp, event_type, severity, message, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, event_type, severity, message, details))
        
        conn.commit()
        conn.close()
    
    def log_metrics(
        self,
        capital: float,
        peak_capital: float,
        drawdown: float,
        open_positions: int,
        total_exposure: float,
        daily_trades: int,
        total_pnl: float,
        win_rate: float = None,
        avg_win: float = None,
        avg_loss: float = None,
        sharpe_ratio: float = None
    ):
        """
        Log performance metrics
        
        Args:
            capital: Current capital
            peak_capital: Peak capital
            drawdown: Current drawdown
            open_positions: Number of open positions
            total_exposure: Total exposure
            daily_trades: Daily trade count
            total_pnl: Total PnL
            win_rate: Win rate percentage
            avg_win: Average winning trade
            avg_loss: Average losing trade
            sharpe_ratio: Sharpe ratio
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO metrics (
                timestamp, capital, peak_capital, drawdown, open_positions,
                total_exposure, daily_trades, total_pnl, win_rate, avg_win,
                avg_loss, sharpe_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, capital, peak_capital, drawdown, open_positions,
            total_exposure, daily_trades, total_pnl, win_rate, avg_win,
            avg_loss, sharpe_ratio
        ))
        
        conn.commit()
        conn.close()
    
    def log_analysis(
        self,
        symbol: str,
        price: float,
        atr: float,
        ml_signal: str,
        ml_confidence: float,
        sentiment_score: float,
        sentiment_label: str,
        decision: str,
        reason: str = None,
        rsi: float = None
    ):
        """
        Log market analysis
        
        Args:
            symbol: Trading symbol
            price: Current price
            atr: ATR value
            ml_signal: ML signal (UP/DOWN)
            ml_confidence: ML confidence
            sentiment_score: Sentiment score
            sentiment_label: Sentiment label
            decision: Trade decision (trade/no_trade)
            reason: Decision reason
            rsi: RSI value
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO analysis (
                timestamp, symbol, price, atr, rsi, ml_signal, ml_confidence,
                sentiment_score, sentiment_label, decision, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, symbol, price, atr, rsi, ml_signal, ml_confidence,
            sentiment_score, sentiment_label, decision, reason
        ))
        
        conn.commit()
        conn.close()
    
    def get_trades(
        self,
        status: str = None,
        symbol: str = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get trades from database
        
        Args:
            status: Filter by status ('open', 'closed', None for all)
            symbol: Filter by symbol
            limit: Maximum number of trades to return
        
        Returns:
            DataFrame with trades
        """
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_events(
        self,
        event_type: str = None,
        severity: str = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get events from database
        
        Args:
            event_type: Filter by event type
            severity: Filter by severity
            limit: Maximum number of events
        
        Returns:
            DataFrame with events
        """
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_performance_summary(self) -> Dict:
        """
        Get performance summary statistics
        
        Returns:
            Dictionary with performance metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'closed'")
        total_trades = cursor.fetchone()[0]
        
        # Winning trades
        cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'closed' AND pnl > 0")
        winning_trades = cursor.fetchone()[0]
        
        # Total PnL
        cursor.execute("SELECT SUM(pnl) FROM trades WHERE status = 'closed'")
        result = cursor.fetchone()
        total_pnl = result[0] if result[0] else 0
        
        # Average PnL
        cursor.execute("SELECT AVG(pnl) FROM trades WHERE status = 'closed' AND pnl > 0")
        result = cursor.fetchone()
        avg_win = result[0] if result[0] else 0
        
        cursor.execute("SELECT AVG(pnl) FROM trades WHERE status = 'closed' AND pnl < 0")
        result = cursor.fetchone()
        avg_loss = result[0] if result[0] else 0
        
        # Max win/loss
        cursor.execute("SELECT MAX(pnl) FROM trades WHERE status = 'closed'")
        result = cursor.fetchone()
        max_win = result[0] if result[0] else 0
        
        cursor.execute("SELECT MIN(pnl) FROM trades WHERE status = 'closed'")
        result = cursor.fetchone()
        max_loss = result[0] if result[0] else 0
        
        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Profit factor
        total_wins = cursor.execute("SELECT SUM(pnl) FROM trades WHERE status = 'closed' AND pnl > 0").fetchone()[0] or 0
        total_losses = abs(cursor.execute("SELECT SUM(pnl) FROM trades WHERE status = 'closed' AND pnl < 0").fetchone()[0] or 0)
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        
        conn.close()
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_win': max_win,
            'max_loss': max_loss,
            'profit_factor': profit_factor
        }
    
    def export_to_csv(self, table: str, output_path: str):
        """
        Export table to CSV
        
        Args:
            table: Table name (trades, events, metrics, analysis)
            output_path: Output CSV file path
        """
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        conn.close()
        
        df.to_csv(output_path, index=False)
        logger.info(f"[DB] Exported {table} to {output_path}")
    
    def clear_old_data(self, days: int = 90):
        """
        Clear data older than specified days
        
        Args:
            days: Number of days to keep
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("DELETE FROM events WHERE timestamp < ?", (cutoff_date,))
        cursor.execute("DELETE FROM analysis WHERE timestamp < ?", (cutoff_date,))
        cursor.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_date,))
        
        conn.commit()
        deleted_count = cursor.rowcount
        conn.close()
        
        logger.info(f"[DB] Deleted {deleted_count} old records (older than {days} days)")
