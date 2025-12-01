"""
Train Ensemble Model
====================
Обучает все модели в ensemble (RandomForest + LSTM)
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.market_data import MarketDataFetcher
from src.ml.ensemble_predictor import get_ensemble_predictor
from src.config.config_loader import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/train_ensemble.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main training function"""
    print("\n" + "="*60)
    print("🚀 ENSEMBLE MODEL TRAINING")
    print("="*60 + "\n")
    
    # Load config
    config = get_config()
    
    # Get symbols to train
    symbols = config.get('symbols', default=['BTC/USDT'])
    timeframe = config.get('timeframe', 'training', default='1h')
    lookback_bars = config.get('timeframe', 'lookback_bars', default=2000)
    
    print(f"📊 Training Configuration:")
    print(f"   Symbols: {', '.join(symbols)}")
    print(f"   Timeframe: {timeframe}")
    print(f"   Lookback: {lookback_bars} bars")
    print()
    
    # Feature columns
    feature_columns = [
        'open', 'high', 'low', 'close', 'volume',
        'sma_20', 'sma_50', 'ema_12', 'ema_26',
        'rsi', 'macd', 'macd_signal', 'macd_hist',
        'bb_upper', 'bb_middle', 'bb_lower',
        'bb_width', 'atr', 'volume_sma_ratio'
    ]
    
    # Train for each symbol
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"📈 Training models for {symbol}")
        print(f"{'='*60}\n")
        
        try:
            # Fetch and prepare data
            print(f"⏳ Fetching data for {symbol}...")
            market_data = MarketDataFetcher()
            
            # Fetch OHLCV data
            df = market_data.fetch_ohlcv(symbol=symbol, limit=lookback_bars)
            
            if df.empty:
                logger.error(f"No data fetched for {symbol}")
                continue
            
            print(f"✅ Fetched {len(df)} bars")
            
            # Add indicators
            print("⏳ Calculating technical indicators...")
            df = market_data.add_indicators(df)
            print(f"✅ Added {len(df.columns)} features")
            
            # Create ML target
            print("⏳ Creating ML target...")
            df = market_data.create_ml_target(df, future_bars=5)
            
            # Remove rows with NaN
            df_clean = df.dropna()
            print(f"✅ Clean data: {len(df_clean)} rows")
            
            if len(df_clean) < 200:
                logger.error(f"Insufficient data after cleaning: {len(df_clean)}")
                continue
            
            # Check feature columns
            missing_cols = [col for col in feature_columns if col not in df_clean.columns]
            if missing_cols:
                logger.error(f"Missing columns: {missing_cols}")
                continue
            
            # Train ensemble
            print("\n⏳ Training ensemble models...")
            print("-" * 60)
            
            ensemble = get_ensemble_predictor()
            results = ensemble.train(df_clean, feature_columns)
            
            print("\n📊 Training Results:")
            for model, success in results.items():
                status = "✅ Success" if success else "❌ Failed"
                print(f"   {model}: {status}")
            
            # Save models
            models_dir = Path('models') / symbol.replace('/', '_').lower()
            models_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n💾 Saving models to {models_dir}...")
            ensemble.save_models(str(models_dir))
            print("✅ Models saved successfully")
            
            # Test prediction
            print("\n🧪 Testing prediction...")
            signal, confidence, details = ensemble.predict(
                df_clean.tail(100), 
                symbol=symbol.split('/')[0]
            )
            
            signal_str = {-1: '📉 SELL', 0: '➡️ HOLD', 1: '📈 BUY'}[signal]
            print(f"\n🎯 Test Prediction: {signal_str}")
            print(f"   Confidence: {confidence:.2%}")
            print(f"   RandomForest: signal={details['random_forest']['signal']}, "
                  f"conf={details['random_forest']['confidence']:.2%}")
            print(f"   LSTM: signal={details['lstm']['signal']}, "
                  f"conf={details['lstm']['confidence']:.2%}")
            print(f"   Sentiment: signal={details['sentiment']['signal']}, "
                  f"score={details['sentiment']['score']:.2f}")
            
            print(f"\n✅ Training completed for {symbol}")
            
        except Exception as e:
            logger.error(f"Error training {symbol}: {e}", exc_info=True)
            print(f"❌ Training failed for {symbol}: {e}")
            continue
    
    print("\n" + "="*60)
    print("🎉 ENSEMBLE TRAINING COMPLETED")
    print("="*60 + "\n")
    
    print("📝 Next steps:")
    print("   1. Review training logs in logs/train_ensemble.log")
    print("   2. Test models with: python scripts/test_ensemble.py")
    print("   3. Run backtest with: python run_backtest.py --use-ensemble")
    print("   4. Start live trading: python main.py --use-ensemble")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Training interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
