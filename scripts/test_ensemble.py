"""
Test Ensemble Model
===================
Тестирует предсказания ensemble модели
"""

import sys
import logging
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.market_data import MarketDataFetcher
from src.ml.ensemble_predictor import get_ensemble_predictor
from src.config.config_loader import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main testing function"""
    print("\n" + "="*60)
    print("🧪 ENSEMBLE MODEL TESTING")
    print("="*60 + "\n")
    
    # Load config
    config = get_config()
    symbol = config.get('symbols', default=['BTC/USDT'])[0]
    
    print(f"📊 Testing symbol: {symbol}\n")
    
    # Load models
    models_dir = Path('models')
    
    if not models_dir.exists():
        print(f"❌ Model directory not found: {models_dir}")
        print("   Run train_ensemble.py first!")
        return
    
    print(f"📂 Loading models from {models_dir}...")
    ensemble = get_ensemble_predictor()
    results = ensemble.load_models(str(models_dir))
    
    print("\n📊 Model Status:")
    for model, success in results.items():
        status = "✅ Loaded" if success else "❌ Not loaded"
        print(f"   {model}: {status}")
    
    # Check overall status
    status = ensemble.get_model_status()
    if not any(status.values()):
        print("\n❌ No models available for testing")
        return
    
    # Fetch recent data
    print(f"\n⏳ Fetching recent data for {symbol}...")
    market_data = MarketDataFetcher()
    df = market_data.fetch_ohlcv(symbol=symbol, limit=500)
    
    if df.empty:
        print(f"❌ No data fetched for {symbol}")
        return
    
    print(f"✅ Fetched {len(df)} bars")
    
    # Add indicators
    print("⏳ Calculating indicators...")
    df = market_data.add_technical_indicators(df)
    df = df.dropna()
    
    if len(df) < 100:
        print(f"❌ Insufficient data: {len(df)} bars")
        return
    
    print(f"✅ Prepared {len(df)} bars\n")
    
    # Make predictions on last N bars
    test_periods = [1, 5, 10, 20]
    
    print("=" * 60)
    print("🔮 PREDICTIONS")
    print("=" * 60 + "\n")
    
    for n in test_periods:
        test_df = df.tail(100 + n).head(100)
        
        try:
            signal, confidence, details = ensemble.predict(
                test_df,
                symbol=symbol.split('/')[0]
            )
            
            signal_str = {-1: '📉 SELL', 0: '➡️ HOLD', 1: '📈 BUY'}[signal]
            
            print(f"📅 {n} bars ago:")
            print(f"   Signal: {signal_str}")
            print(f"   Confidence: {confidence:.2%}")
            print(f"   Price: ${df.iloc[-n]['close']:,.2f}")
            
            # Show individual model predictions
            print(f"   Models:")
            print(f"     RF: signal={details['random_forest']['signal']:+d}, "
                  f"conf={details['random_forest']['confidence']:.1%}")
            print(f"     LSTM: signal={details['lstm']['signal']:+d}, "
                  f"conf={details['lstm']['confidence']:.1%}")
            print(f"     Sentiment: signal={details['sentiment']['signal']:+d}, "
                  f"score={details['sentiment']['score']:+.2f}")
            print()
            
        except Exception as e:
            print(f"❌ Prediction error: {e}\n")
    
    # Current prediction
    print("=" * 60)
    print("🎯 CURRENT PREDICTION")
    print("=" * 60 + "\n")
    
    try:
        signal, confidence, details = ensemble.predict(
            df.tail(100),
            symbol=symbol.split('/')[0]
        )
        
        signal_str = {-1: '📉 SELL', 0: '➡️ HOLD', 1: '📈 BUY'}[signal]
        current_price = df.iloc[-1]['close']
        
        print(f"Current Price: ${current_price:,.2f}")
        print(f"Signal: {signal_str}")
        print(f"Confidence: {confidence:.2%}\n")
        
        print("Individual Models:")
        print(f"  RandomForest:")
        print(f"    Signal: {details['random_forest']['signal']:+d}")
        print(f"    Confidence: {details['random_forest']['confidence']:.1%}")
        
        print(f"  LSTM:")
        print(f"    Signal: {details['lstm']['signal']:+d}")
        print(f"    Confidence: {details['lstm']['confidence']:.1%}")
        
        print(f"  Sentiment:")
        print(f"    Signal: {details['sentiment']['signal']:+d}")
        print(f"    Score: {details['sentiment']['score']:+.2f}")
        print(f"    Confidence: {details['sentiment'].get('confidence', 0):.1%}")
        
        print(f"\nEnsemble Scores:")
        ens = details['ensemble']
        print(f"  Buy:  {ens['buy_score']:.3f}")
        print(f"  Sell: {ens['sell_score']:.3f}")
        print(f"  Hold: {ens['hold_score']:.3f}")
        
        # Trading recommendation
        print(f"\n{'='*60}")
        if signal != 0 and confidence >= 0.6:
            action = "ОТКРЫТЬ ПОЗИЦИЮ" if signal == 1 else "ОТКРЫТЬ SHORT"
            print(f"✅ Рекомендация: {action}")
            print(f"   Уверенность выше порога (60%)")
        else:
            print(f"⏸️ Рекомендация: ЖДАТЬ")
            if signal == 0:
                print(f"   Нейтральный сигнал")
            else:
                print(f"   Уверенность ниже порога ({confidence:.1%} < 60%)")
        print(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Current prediction error: {e}", exc_info=True)
        print(f"❌ Error getting current prediction: {e}\n")
    
    print("✅ Testing completed\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
