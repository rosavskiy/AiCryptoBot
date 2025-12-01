"""
Backtest Runner - Run Walk-Forward Validation
"""

import sys
import logging
from datetime import datetime

from src.backtesting.backtest import Backtester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/backtest.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """
    Run backtesting with Walk-Forward Validation
    """
    print("\n" + "="*80)
    print("   AI CRYPTO BOT - BACKTESTING")
    print("="*80)
    
    # Initialize backtester
    backtester = Backtester(
        symbol='BTC/USDT',
        interval='15m',
        initial_capital=10000.0,
        risk_per_trade=0.01,
        ml_threshold=0.60,
        sentiment_threshold=-0.1,
        commission=0.0006
    )
    
    print("\n[BACKTEST] Configuration:")
    print(f"  Symbol:           BTC/USDT")
    print(f"  Interval:         15m")
    print(f"  Initial Capital:  $10,000.00")
    print(f"  Risk per Trade:   1.00%")
    print(f"  ML Threshold:     60.00%")
    print(f"  Sentiment Filter: -0.1")
    print(f"  Commission:       0.06%")
    
    # Run Walk-Forward Validation
    print("\n[BACKTEST] Starting Walk-Forward Validation...")
    print("[INFO] This may take 5-10 minutes to fetch data and train models...")
    
    results = backtester.walk_forward_validation(
        train_size=400,      # 400 candles training (~4 days on 15m)
        test_size=200,       # 200 candles testing (~2 days on 15m)
        total_periods=3      # 3 walk-forward windows
    )
    
    if not results:
        print("\n[ERROR] Backtesting failed - no results")
        return
    
    # Display results
    print("\n" + "="*80)
    print("   FINAL RESULTS")
    print("="*80)
    
    print(f"\n[PERFORMANCE METRICS]")
    print(f"  Walk-Forward Periods:  {results['periods']}")
    print(f"  Total Trades:          {results['total_trades']}")
    print(f"  Winning Trades:        {results['winning_trades']}")
    print(f"  Losing Trades:         {results['losing_trades']}")
    print(f"  Win Rate:              {results['win_rate']:.2f}%")
    print(f"  Total Return:          {results['total_return']:+.2f}%")
    print(f"  Final Capital:         ${results['final_capital']:,.2f}")
    print(f"  Avg Period Return:     {results['avg_period_return']:+.2f}%")
    print(f"  Avg Max Drawdown:      {results['avg_max_drawdown']:.2f}%")
    print(f"  Avg Sharpe Ratio:      {results['avg_sharpe_ratio']:.2f}")
    print(f"  Avg Profit Factor:     {results['avg_profit_factor']:.2f}")
    
    # Period breakdown
    print(f"\n[PERIOD BREAKDOWN]")
    for i, period in enumerate(results['period_results']):
        print(f"\n  Period {i+1}:")
        print(f"    Trades:        {period['total_trades']}")
        print(f"    Win Rate:      {period['win_rate']:.1f}%")
        print(f"    Return:        {period['total_return']:+.2f}%")
        print(f"    Max Drawdown:  {period['max_drawdown']:.2f}%")
        print(f"    Sharpe Ratio:  {period['sharpe_ratio']:.2f}")
    
    # Export results
    print("\n[EXPORT] Saving results...")
    backtester.export_results(results, 'data/backtest_results.csv')
    
    # Plot equity curve
    print("[PLOT] Generating equity curve...")
    backtester.plot_equity_curve(results, 'data/backtest_equity_curve.png')
    
    # Strategy evaluation
    print("\n" + "="*80)
    print("   STRATEGY EVALUATION")
    print("="*80)
    
    if results['total_return'] > 0:
        print("\n[SUCCESS] Strategy is PROFITABLE!")
    else:
        print("\n[WARNING] Strategy is UNPROFITABLE!")
    
    if results['win_rate'] > 50:
        print(f"[SUCCESS] Win rate is good: {results['win_rate']:.1f}%")
    else:
        print(f"[WARNING] Win rate is low: {results['win_rate']:.1f}%")
    
    if results['avg_sharpe_ratio'] > 1.0:
        print(f"[SUCCESS] Sharpe ratio is excellent: {results['avg_sharpe_ratio']:.2f}")
    elif results['avg_sharpe_ratio'] > 0.5:
        print(f"[INFO] Sharpe ratio is acceptable: {results['avg_sharpe_ratio']:.2f}")
    else:
        print(f"[WARNING] Sharpe ratio is low: {results['avg_sharpe_ratio']:.2f}")
    
    if results['avg_max_drawdown'] < 10:
        print(f"[SUCCESS] Drawdown is manageable: {results['avg_max_drawdown']:.2f}%")
    elif results['avg_max_drawdown'] < 20:
        print(f"[INFO] Drawdown is moderate: {results['avg_max_drawdown']:.2f}%")
    else:
        print(f"[WARNING] Drawdown is high: {results['avg_max_drawdown']:.2f}%")
    
    print("\n" + "="*80)
    print("   RECOMMENDATIONS")
    print("="*80)
    
    if results['total_return'] > 10 and results['avg_sharpe_ratio'] > 1.0:
        print("\n[READY] Strategy shows strong performance!")
        print("  - Consider testing on testnet with real execution")
        print("  - Monitor performance for 1-2 weeks before mainnet")
        print("  - Start with small capital (5-10% of total)")
    elif results['total_return'] > 0 and results['win_rate'] > 45:
        print("\n[CAUTION] Strategy shows moderate performance")
        print("  - Optimize ML threshold and risk parameters")
        print("  - Consider adding more filters (volatility, volume)")
        print("  - Run longer backtest period (6+ months)")
    else:
        print("\n[WARNING] Strategy needs improvement")
        print("  - Review ML model accuracy and features")
        print("  - Adjust entry/exit rules")
        print("  - Consider different timeframes or symbols")
        print("  - DO NOT trade with real money yet!")
    
    print("\n" + "="*80)
    print("   BACKTEST COMPLETED!")
    print("="*80)
    print(f"\nResults saved to:")
    print(f"  - data/backtest_results.csv")
    print(f"  - data/backtest_equity_curve.png")
    print(f"  - logs/backtest.log")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Backtest interrupted by user")
    except Exception as e:
        logger.error(f"[ERROR] Backtest failed: {e}", exc_info=True)
        print(f"\n[ERROR] Backtest failed: {e}")
