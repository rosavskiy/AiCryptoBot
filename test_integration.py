"""
Integration Test - Combined ML + Sentiment + Risk
==================================================
Tests the complete trading signal generation pipeline.
"""

import sys
from pathlib import Path
import logging
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.market_data import MarketDataFetcher
from src.ml.predictor import MLPredictor
from src.sentiment.news_analyzer import NewsAnalyzer
from src.risk.risk_manager import RiskManager


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_complete_pipeline():
    """Test complete trading pipeline"""
    print("\n" + "="*80)
    print("   COMPLETE TRADING PIPELINE TEST")
    print("="*80 + "\n")
    
    symbol = 'BTC/USDT'
    symbol_short = 'BTC'
    
    # ========================================
    # Step 1: Fetch Market Data
    # ========================================
    print("\n" + "="*80)
    print("[STEP 1] FETCHING MARKET DATA")
    print("="*80 + "\n")
    
    fetcher = MarketDataFetcher()
    df = fetcher.fetch_ohlcv(symbol=symbol)
    df = fetcher.add_technical_indicators(df)
    df = fetcher.create_ml_target(df)
    df = fetcher.prepare_features(df)
    
    print(f"[SUCCESS] Market data ready: {len(df)} rows")
    print(f"[INFO] Latest price: ${df['close'].iloc[-1]:.2f}")
    print(f"[INFO] ATR: ${df['ATR'].iloc[-1]:.2f}")
    
    # ========================================
    # Step 2: Train ML Model
    # ========================================
    print("\n" + "="*80)
    print("[STEP 2] TRAINING ML MODEL")
    print("="*80 + "\n")
    
    predictor = MLPredictor()
    df_clean = df.loc[:, ~df.columns.duplicated()]
    X, y, features = predictor.prepare_data(df_clean)
    
    print(f"[INFO] Training on {len(X)} samples...")
    metrics = predictor.train(X, y, validation_split=0.2)
    predictor.save_model()
    
    # Get prediction for latest data
    last_row = X.iloc[-1]
    if isinstance(last_row, pd.Series) and last_row.index.duplicated().any():
        last_row = last_row[~last_row.index.duplicated(keep='first')]
    
    ml_prediction, ml_confidence = predictor.predict_single(last_row)
    ml_signal = "UP" if ml_prediction == 1 else "DOWN"
    
    print(f"\n[ML SIGNAL] Direction: {ml_signal}")
    print(f"[ML SIGNAL] Confidence: {ml_confidence:.2%}")
    
    # ========================================
    # Step 3: Analyze Sentiment
    # ========================================
    print("\n" + "="*80)
    print("[STEP 3] ANALYZING SENTIMENT")
    print("="*80 + "\n")
    
    analyzer = NewsAnalyzer()
    sentiment = analyzer.get_sentiment(symbol_short, hours_back=24)
    
    print(f"[SENTIMENT] Score: {sentiment['score']:.4f}")
    print(f"[SENTIMENT] Label: {sentiment['label'].upper()}")
    print(f"[SENTIMENT] Confidence: {sentiment['confidence']:.2%}")
    print(f"[SENTIMENT] News count: {sentiment['news_count']}")
    
    should_trade_sentiment, sentiment_score = analyzer.should_trade(symbol_short)
    
    # ========================================
    # Step 4: Risk Management
    # ========================================
    print("\n" + "="*80)
    print("[STEP 4] RISK MANAGEMENT CALCULATIONS")
    print("="*80 + "\n")
    
    risk_manager = RiskManager(initial_capital=10000.0)
    
    # Get latest market data
    current_price = df['close'].iloc[-1]
    current_atr = df['ATR'].iloc[-1]
    
    # Calculate stop-loss and take-profit
    direction = 'long' if ml_signal == 'UP' else 'short'
    stop_loss = risk_manager.calculate_stop_loss(current_price, current_atr, direction)
    take_profit = risk_manager.calculate_take_profit(current_price, current_atr, direction)
    
    # Calculate position size
    position_size, quantity = risk_manager.calculate_position_size(
        current_price,
        stop_loss,
        method='fixed'
    )
    
    # Check if can trade
    can_trade, reason = risk_manager.can_open_position()
    
    print(f"\n[RISK] Current Price: ${current_price:.2f}")
    print(f"[RISK] Stop-Loss: ${stop_loss:.2f}")
    print(f"[RISK] Take-Profit: ${take_profit:.2f}")
    print(f"[RISK] Position Size: ${position_size:.2f} ({quantity:.6f} {symbol_short})")
    print(f"[RISK] Can Trade: {can_trade} ({reason})")
    
    # ========================================
    # Step 5: Combined Decision
    # ========================================
    print("\n" + "="*80)
    print("[STEP 5] FINAL TRADING DECISION")
    print("="*80 + "\n")
    
    # Decision logic
    ml_threshold = 0.60  # From config
    sentiment_threshold = -0.1  # From config
    
    decision_passed = []
    decision_failed = []
    
    # Check ML confidence
    if ml_confidence >= ml_threshold:
        decision_passed.append(f"ML confidence {ml_confidence:.2%} >= {ml_threshold:.2%}")
    else:
        decision_failed.append(f"ML confidence {ml_confidence:.2%} < {ml_threshold:.2%}")
    
    # Check sentiment
    if sentiment_score >= sentiment_threshold:
        decision_passed.append(f"Sentiment {sentiment_score:.4f} >= {sentiment_threshold}")
    else:
        decision_failed.append(f"Sentiment {sentiment_score:.4f} < {sentiment_threshold}")
    
    # Check risk management
    if can_trade:
        decision_passed.append(f"Risk checks passed")
    else:
        decision_failed.append(f"Risk check failed: {reason}")
    
    # Final decision
    final_decision = len(decision_failed) == 0
    
    print("[DECISION CRITERIA]")
    print("-" * 80)
    
    if decision_passed:
        print("\n[PASSED]")
        for check in decision_passed:
            print(f"  + {check}")
    
    if decision_failed:
        print("\n[FAILED]")
        for check in decision_failed:
            print(f"  x {check}")
    
    print("\n" + "="*80)
    if final_decision:
        print(f"   TRADE SIGNAL: {ml_signal} {symbol}")
        print("="*80)
        print(f"\n  Entry Price:  ${current_price:.2f}")
        print(f"  Quantity:     {quantity:.6f} {symbol_short}")
        print(f"  Position:     ${position_size:.2f}")
        print(f"  Stop-Loss:    ${stop_loss:.2f} ({((stop_loss/current_price-1)*100):+.2f}%)")
        print(f"  Take-Profit:  ${take_profit:.2f} ({((take_profit/current_price-1)*100):+.2f}%)")
        print(f"  Risk/Reward:  1:{abs((take_profit-current_price)/(current_price-stop_loss)):.2f}")
    else:
        print("   NO TRADE - CONDITIONS NOT MET")
        print("="*80)
    
    # ========================================
    # Step 6: Simulate Position (if decision is to trade)
    # ========================================
    if final_decision:
        print("\n" + "="*80)
        print("[STEP 6] SIMULATING POSITION")
        print("="*80 + "\n")
        
        # Open position
        position = risk_manager.add_position(
            symbol=symbol,
            entry_price=current_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            direction=direction
        )
        
        # Get risk metrics
        metrics = risk_manager.get_risk_metrics()
        
        print(f"\n[PORTFOLIO]")
        print(f"  Capital:         ${metrics['current_capital']:,.2f}")
        print(f"  Open Positions:  {metrics['open_positions']}")
        print(f"  Exposure:        ${metrics['total_exposure']:,.2f} ({metrics['exposure_pct']:.1%})")
        print(f"  Drawdown:        {metrics['drawdown_pct']:.2f}%")
        print(f"  Daily Trades:    {metrics['daily_trades']}")
        
        # Simulate exit at take-profit for demonstration
        print(f"\n[SIMULATION] Closing position at take-profit: ${take_profit:.2f}")
        closed_pos = risk_manager.close_position(symbol, take_profit)
        
        if closed_pos:
            print(f"\n[RESULT]")
            print(f"  PnL:        ${closed_pos['pnl']:+,.2f} ({closed_pos['pnl_pct']:+.2f}%)")
            print(f"  New Capital: ${risk_manager.current_capital:,.2f}")
            print(f"  Total Return: {((risk_manager.current_capital/risk_manager.initial_capital-1)*100):+.2f}%")


def main():
    """Run integration test"""
    setup_logging()
    
    print("\n" + "="*80)
    print("   AI CRYPTO BOT - INTEGRATION TEST")
    print("   ML + Sentiment + Risk Management")
    print("="*80)
    
    try:
        test_complete_pipeline()
        
        print("\n" + "="*80)
        print("   INTEGRATION TEST COMPLETED!")
        print("="*80)
        
        print("\n[INFO] System components verified:")
        print("   [+] Market data fetching (Bybit Testnet)")
        print("   [+] Technical indicators (13 features)")
        print("   [+] ML prediction (RandomForest)")
        print("   [+] Sentiment analysis (TextBlob)")
        print("   [+] Risk management (position sizing, SL/TP)")
        print("   [+] Combined decision logic")
        
        print("\n[INFO] Next steps:")
        print("   1. Implement Trading Executor module")
        print("   2. Add database logging")
        print("   3. Develop backtesting system")
        print("   4. Deploy to VPS with real testnet trading")
        
    except Exception as e:
        logging.error(f"[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
