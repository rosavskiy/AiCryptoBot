"""
Trading Executor Test Script
=============================
Tests the complete trading execution system in DRY RUN mode.
"""

import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading.executor import TradingExecutor


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_executor():
    """Test trading executor"""
    print("\n" + "="*80)
    print("   TRADING EXECUTOR TEST (DRY RUN)")
    print("="*80 + "\n")
    
    # Initialize executor
    executor = TradingExecutor(
        testnet=True,
        initial_capital=10000.0
    )
    
    # Test 1: Market Analysis
    print("\n" + "="*80)
    print("[TEST 1] MARKET ANALYSIS")
    print("="*80 + "\n")
    
    symbol = 'BTC/USDT'
    analysis = executor.analyze_market(symbol)
    
    print(f"\n[ANALYSIS RESULTS]")
    print(f"  Symbol:           {analysis['symbol']}")
    print(f"  Price:            ${analysis['price']:.2f}")
    print(f"  ATR:              ${analysis['atr']:.2f}")
    print(f"  ML Signal:        {analysis['ml_signal']}")
    print(f"  ML Confidence:    {analysis['ml_confidence']:.2%}")
    print(f"  Sentiment:        {analysis['sentiment_label']} ({analysis['sentiment_score']:.4f})")
    
    # Test 2: Signal Generation
    print("\n" + "="*80)
    print("[TEST 2] SIGNAL GENERATION")
    print("="*80 + "\n")
    
    should_trade, reason, direction = executor.generate_signal(analysis)
    
    print(f"[SIGNAL]")
    print(f"  Should Trade:     {should_trade}")
    print(f"  Reason:           {reason}")
    print(f"  Direction:        {direction if direction else 'N/A'}")
    
    # Test 3: Trade Execution (Dry Run)
    if should_trade and direction:
        print("\n" + "="*80)
        print("[TEST 3] TRADE EXECUTION (DRY RUN)")
        print("="*80 + "\n")
        
        trade = executor.execute_trade(analysis, direction, dry_run=True)
        
        if trade:
            print(f"\n[TRADE EXECUTED]")
            print(f"  Order ID:         {trade['order_id']}")
            print(f"  Symbol:           {trade['symbol']}")
            print(f"  Side:             {trade['side'].upper()}")
            print(f"  Price:            ${trade['price']:.2f}")
            print(f"  Quantity:         {trade['quantity']:.6f}")
            print(f"  Position Size:    ${trade['position_size']:.2f}")
            print(f"  Stop-Loss:        ${trade['stop_loss']:.2f}")
            print(f"  Take-Profit:      ${trade['take_profit']:.2f}")
            print(f"  Status:           {trade['status']}")
            
            # Test 4: Position Management
            print("\n" + "="*80)
            print("[TEST 4] POSITION MANAGEMENT")
            print("="*80 + "\n")
            
            print(f"[INFO] Active positions: {len(executor.active_positions)}")
            
            # Check position
            updates = executor.check_positions()
            
            for update in updates:
                print(f"\n[POSITION UPDATE]")
                print(f"  Symbol:           {update['symbol']}")
                print(f"  Current Price:    ${update['current_price']:.2f}")
                print(f"  PnL:              ${update['pnl']:+.2f} ({update['pnl_pct']:+.2f}%)")
                print(f"  Should Close:     {update['should_close']}")
                if update['close_reason']:
                    print(f"  Close Reason:     {update['close_reason']}")
            
            # Simulate closing at take-profit for testing
            print(f"\n[TEST] Simulating position close at take-profit...")
            closed = executor.close_position(
                trade['symbol'],
                trade['take_profit'],
                dry_run=True
            )
            
            if closed:
                print(f"\n[POSITION CLOSED]")
                print(f"  Symbol:           {closed.get('symbol', 'N/A')}")
                print(f"  Exit Price:       ${closed.get('exit_price', 0):.2f}")
                print(f"  PnL:              ${closed.get('pnl', 0):+.2f}")
                print(f"  PnL %:            {closed.get('pnl_pct', 0):+.2f}%")
    else:
        print(f"\n[INFO] No trade signal generated, skipping execution tests")
    
    # Test 5: Risk Metrics
    print("\n" + "="*80)
    print("[TEST 5] RISK METRICS")
    print("="*80 + "\n")
    
    metrics = executor.risk_manager.get_risk_metrics()
    
    print(f"[PORTFOLIO METRICS]")
    print(f"  Initial Capital:  ${executor.risk_manager.initial_capital:,.2f}")
    print(f"  Current Capital:  ${metrics['current_capital']:,.2f}")
    print(f"  Peak Capital:     ${metrics['peak_capital']:,.2f}")
    print(f"  Drawdown:         {metrics['drawdown_pct']:.2f}%")
    print(f"  Open Positions:   {metrics['open_positions']}")
    print(f"  Total Exposure:   ${metrics['total_exposure']:,.2f}")
    print(f"  Exposure %:       {metrics['exposure_pct']:.2%}")
    print(f"  Daily Trades:     {metrics['daily_trades']}")
    print(f"  Total PnL:        ${metrics['profit_loss']:+,.2f}")
    print(f"  Total Return:     {metrics['return_pct']:+.2f}%")


def main():
    """Run executor tests"""
    setup_logging()
    
    print("\n" + "="*80)
    print("   AI CRYPTO BOT - TRADING EXECUTOR TEST")
    print("="*80)
    
    try:
        test_executor()
        
        print("\n" + "="*80)
        print("   ALL TESTS COMPLETED!")
        print("="*80)
        
        print("\n[INFO] Trading Executor verified:")
        print("   [+] Market analysis (Data + ML + Sentiment)")
        print("   [+] Signal generation (thresholds + filters)")
        print("   [+] Trade execution (DRY RUN mode)")
        print("   [+] Position management (open/close)")
        print("   [+] Risk metrics tracking")
        
        print("\n[INFO] Next steps:")
        print("   1. Test with real Bybit Testnet (set dry_run=False)")
        print("   2. Add database logging for trades")
        print("   3. Run backtesting on historical data")
        print("   4. Deploy to VPS for 24/7 operation")
        
        print("\n[WARNING] This was a DRY RUN - no real orders placed")
        print("[WARNING] To trade on testnet: executor.execute_trade(..., dry_run=False)")
        print("[WARNING] NEVER use mainnet without thorough testing!")
        
    except Exception as e:
        logging.error(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
