"""
Main Test Script
================
Tests the data fetching and ML prediction pipeline.
"""

import sys
from pathlib import Path
import logging
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.market_data import MarketDataFetcher
from src.ml.predictor import MLPredictor


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/test_run.log')
        ]
    )


def test_data_pipeline():
    """Test data fetching and processing"""
    print("\n" + "="*80)
    print("[DATA] TESTING DATA PIPELINE")
    print("="*80 + "\n")
    
    # Initialize fetcher
    fetcher = MarketDataFetcher()
    
    # Fetch data
    df = fetcher.get_market_data(
        symbol='BTC/USDT',
        timeframe='15m',
        limit=1000
    )
    
    print(f"\n[SUCCESS] Successfully fetched {len(df)} rows")
    print(f"[INFO] Columns: {list(df.columns)}")
    print(f"\n[DATA] Last 5 rows:")
    print(df.tail())
    
    return df


def test_ml_pipeline(df):
    """Test ML training and prediction"""
    print("\n" + "="*80)
    print("[ML] TESTING ML PIPELINE")
    print("="*80 + "\n")
    
    # Remove duplicate columns before ML pipeline
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Initialize predictor
    predictor = MLPredictor()
    
    # Prepare data
    X, y, features = predictor.prepare_data(df)
    
    print(f"\n[SUCCESS] Prepared features: {features}")
    print(f"[INFO] Training samples: {len(X)}")
    print(f"[INFO] Target distribution:")
    print(y.value_counts())
    
    # Train model
    print("\n[ML] Training model...")
    metrics = predictor.train(X, y, validation_split=0.2)
    
    # Save model
    predictor.save_model()
    
    # Test prediction
    print("\n[ML] Testing prediction on latest data...")
    last_row = X.iloc[-1]
    # Remove duplicate indices if any
    if isinstance(last_row, pd.Series) and last_row.index.duplicated().any():
        last_row = last_row[~last_row.index.duplicated(keep='first')]
    
    prediction, confidence = predictor.predict_single(last_row)
    
    print(f"\n{'='*80}")
    print(f"[PREDICTION] Direction: {'UP' if prediction == 1 else 'DOWN'}")
    print(f"[PREDICTION] Confidence: {confidence:.2%}")
    print(f"{'='*80}\n")
    
    return predictor


def test_walk_forward_validation(df):
    """Test Walk-Forward Validation"""
    print("\n" + "="*80)
    print("[VALIDATION] TESTING WALK-FORWARD VALIDATION")
    print("="*80 + "\n")
    
    predictor = MLPredictor()
    
    # Run walk-forward validation
    results = predictor.walk_forward_validation(
        df,
        train_days=30,  # Smaller for testing
        test_days=10,
        step_days=5
    )
    
    print(f"\n[SUCCESS] Completed {len(results)} validation folds")
    
    return results


def main():
    """Main test function"""
    setup_logging()
    
    print("\n" + "="*80)
    print("   AI CRYPTO BOT - SYSTEM TEST")
    print("="*80 + "\n")
    
    try:
        # Test 1: Data Pipeline
        df = test_data_pipeline()
        
        # Test 2: ML Pipeline
        predictor = test_ml_pipeline(df)
        
        # Test 3: Walk-Forward Validation (optional, takes time)
        # Uncomment to run full validation
        # test_walk_forward_validation(df)
        
        print("\n" + "="*80)
        print("   ALL TESTS PASSED!")
        print("="*80 + "\n")
        
        print("[INFO] Next steps:")
        print("   1. Copy .env.example to .env and add your Bybit API keys")
        print("   2. Test on Bybit Testnet first")
        print("   3. Run full Walk-Forward validation")
        print("   4. Proceed to implement Sentiment and Risk modules")
        
    except Exception as e:
        logging.error(f"[ERROR] Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
