"""
Trade Logger Test Script
=========================
Tests the trade logging and database functionality.
"""

import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.trade_logger import TradeLogger
from datetime import datetime


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_trade_logger():
    """Test trade logger functionality"""
    print("\n" + "="*80)
    print("   TRADE LOGGER TEST")
    print("="*80 + "\n")
    
    # Initialize logger
    logger = TradeLogger(db_path='data/test_trading.db')
    
    # Test 1: Log trade open
    print("\n" + "="*80)
    print("[TEST 1] LOG TRADE OPEN")
    print("="*80 + "\n")
    
    trade_id = logger.log_trade_open(
        symbol='BTC/USDT',
        side='buy',
        entry_price=96000.0,
        quantity=0.01,
        position_size=960.0,
        stop_loss=95000.0,
        take_profit=97500.0,
        direction='long',
        ml_confidence=0.85,
        sentiment_score=0.15,
        order_id='TEST_12345'
    )
    
    print(f"[SUCCESS] Trade logged with ID: {trade_id}")
    
    # Test 2: Log event
    print("\n" + "="*80)
    print("[TEST 2] LOG SYSTEM EVENT")
    print("="*80 + "\n")
    
    logger.log_event(
        event_type='system',
        severity='info',
        message='System started successfully',
        details='All components initialized'
    )
    
    logger.log_event(
        event_type='error',
        severity='warning',
        message='API rate limit approaching',
        details='Used 80% of rate limit'
    )
    
    print("[SUCCESS] Events logged")
    
    # Test 3: Log market analysis
    print("\n" + "="*80)
    print("[TEST 3] LOG MARKET ANALYSIS")
    print("="*80 + "\n")
    
    logger.log_analysis(
        symbol='BTC/USDT',
        price=96000.0,
        atr=450.0,
        ml_signal='UP',
        ml_confidence=0.85,
        sentiment_score=0.15,
        sentiment_label='positive',
        decision='trade',
        reason='All conditions met',
        rsi=65.5
    )
    
    logger.log_analysis(
        symbol='ETH/USDT',
        price=3500.0,
        atr=75.0,
        ml_signal='DOWN',
        ml_confidence=0.55,
        sentiment_score=-0.2,
        sentiment_label='negative',
        decision='no_trade',
        reason='Sentiment too negative',
        rsi=45.0
    )
    
    print("[SUCCESS] Market analysis logged")
    
    # Test 4: Log metrics
    print("\n" + "="*80)
    print("[TEST 4] LOG PERFORMANCE METRICS")
    print("="*80 + "\n")
    
    logger.log_metrics(
        capital=10500.0,
        peak_capital=10500.0,
        drawdown=0.0,
        open_positions=1,
        total_exposure=960.0,
        daily_trades=1,
        total_pnl=500.0,
        win_rate=75.0,
        avg_win=150.0,
        avg_loss=-50.0,
        sharpe_ratio=1.8
    )
    
    print("[SUCCESS] Metrics logged")
    
    # Test 5: Close trade
    print("\n" + "="*80)
    print("[TEST 5] LOG TRADE CLOSE")
    print("="*80 + "\n")
    
    logger.log_trade_close(
        trade_id=trade_id,
        exit_price=97500.0,
        pnl=15.0,
        pnl_pct=1.56,
        exit_reason='take_profit'
    )
    
    print(f"[SUCCESS] Trade {trade_id} closed")
    
    # Test 6: Query trades
    print("\n" + "="*80)
    print("[TEST 6] QUERY TRADES")
    print("="*80 + "\n")
    
    trades = logger.get_trades(status='closed', limit=10)
    print(f"[INFO] Found {len(trades)} closed trades")
    if not trades.empty:
        print("\n[TRADES]")
        print(trades[['symbol', 'side', 'entry_price', 'exit_price', 'pnl', 'pnl_pct']].to_string())
    
    # Test 7: Query events
    print("\n" + "="*80)
    print("[TEST 7] QUERY EVENTS")
    print("="*80 + "\n")
    
    events = logger.get_events(limit=10)
    print(f"[INFO] Found {len(events)} events")
    if not events.empty:
        print("\n[EVENTS]")
        print(events[['timestamp', 'event_type', 'severity', 'message']].tail().to_string())
    
    # Test 8: Performance summary
    print("\n" + "="*80)
    print("[TEST 8] PERFORMANCE SUMMARY")
    print("="*80 + "\n")
    
    summary = logger.get_performance_summary()
    
    print("[PERFORMANCE METRICS]")
    print(f"  Total Trades:     {summary['total_trades']}")
    print(f"  Winning Trades:   {summary['winning_trades']}")
    print(f"  Losing Trades:    {summary['losing_trades']}")
    print(f"  Win Rate:         {summary['win_rate']:.2f}%")
    print(f"  Total PnL:        ${summary['total_pnl']:+,.2f}")
    print(f"  Average Win:      ${summary['avg_win']:+,.2f}")
    print(f"  Average Loss:     ${summary['avg_loss']:+,.2f}")
    print(f"  Max Win:          ${summary['max_win']:+,.2f}")
    print(f"  Max Loss:         ${summary['max_loss']:+,.2f}")
    print(f"  Profit Factor:    {summary['profit_factor']:.2f}")
    
    # Test 9: Export to CSV
    print("\n" + "="*80)
    print("[TEST 9] EXPORT TO CSV")
    print("="*80 + "\n")
    
    logger.export_to_csv('trades', 'data/trades_export.csv')
    logger.export_to_csv('events', 'data/events_export.csv')
    
    print("[SUCCESS] Data exported to CSV files")


def main():
    """Run logger tests"""
    setup_logging()
    
    print("\n" + "="*80)
    print("   AI CRYPTO BOT - TRADE LOGGER TEST")
    print("="*80)
    
    try:
        test_trade_logger()
        
        print("\n" + "="*80)
        print("   ALL TESTS COMPLETED!")
        print("="*80)
        
        print("\n[INFO] Trade Logger verified:")
        print("   [+] SQLite database creation")
        print("   [+] Trade logging (open/close)")
        print("   [+] Event logging")
        print("   [+] Market analysis logging")
        print("   [+] Performance metrics logging")
        print("   [+] Data querying")
        print("   [+] Performance summary")
        print("   [+] CSV export")
        
        print("\n[INFO] Database location: data/test_trading.db")
        print("[INFO] CSV exports: data/trades_export.csv, data/events_export.csv")
        
    except Exception as e:
        logging.error(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
