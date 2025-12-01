"""
Check Phase 2 Installation
===========================
Проверяет, что все компоненты Phase 2 установлены корректно
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_torch():
    """Check PyTorch installation"""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        device = 'CUDA' if cuda_available else 'CPU'
        print(f"✅ PyTorch: Available ({device})")
        if cuda_available:
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
        return True
    except ImportError:
        print("❌ PyTorch: Not installed")
        print("   Install: pip install torch")
        return False


def check_transformers():
    """Check Transformers installation"""
    try:
        import transformers
        print(f"✅ Transformers: Available (v{transformers.__version__})")
        return True
    except ImportError:
        print("❌ Transformers: Not installed")
        print("   Install: pip install transformers")
        return False


def check_finbert():
    """Check FinBERT model"""
    try:
        from src.sentiment.finbert_analyzer import get_sentiment_analyzer
        analyzer = get_sentiment_analyzer()
        
        if analyzer.finbert_available:
            print("✅ FinBERT: Model loaded")
            print(f"   Device: {analyzer.device}")
            return True
        else:
            print("⚠️ FinBERT: Not available (using TextBlob fallback)")
            return False
    except Exception as e:
        print(f"❌ FinBERT: Error - {e}")
        return False


def check_lstm():
    """Check LSTM predictor"""
    try:
        from src.ml.lstm_predictor import LSTMPredictor
        predictor = LSTMPredictor()
        print(f"✅ LSTM: Model initialized")
        print(f"   Device: {predictor.device}")
        return True
    except Exception as e:
        print(f"❌ LSTM: Error - {e}")
        return False


def check_telegram():
    """Check Telegram bot configuration"""
    try:
        from src.utils.telegram_notifier import get_telegram_notifier
        notifier = get_telegram_notifier()
        
        if notifier.enabled:
            print("✅ Telegram: Bot configured")
            print(f"   Token: {notifier.bot_token[:10]}...")
            return True
        else:
            print("⚠️ Telegram: Not configured (optional)")
            print("   Set bot_token and chat_id in config/settings.yaml")
            return False
    except Exception as e:
        print(f"❌ Telegram: Error - {e}")
        return False


def check_ensemble():
    """Check Ensemble predictor"""
    try:
        from src.ml.ensemble_predictor import get_ensemble_predictor
        ensemble = get_ensemble_predictor()
        status = ensemble.get_model_status()
        
        print("✅ Ensemble: Initialized")
        print(f"   RandomForest: {'Ready' if status['random_forest'] else 'Not trained'}")
        print(f"   LSTM: {'Ready' if status['lstm'] else 'Not trained'}")
        print(f"   Sentiment: {'Ready' if status['sentiment'] else 'Not available'}")
        return True
    except Exception as e:
        print(f"❌ Ensemble: Error - {e}")
        return False


def check_python_version():
    """Check Python version"""
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 9:
        print(f"✅ Python: {major}.{minor} (OK)")
        return True
    else:
        print(f"⚠️ Python: {major}.{minor} (Recommended: 3.9+)")
        return False


def main():
    print("\n" + "="*60)
    print("🔍 PHASE 2 INSTALLATION CHECK")
    print("="*60 + "\n")
    
    results = []
    
    print("📦 Core Dependencies:")
    results.append(check_python_version())
    results.append(check_torch())
    results.append(check_transformers())
    print()
    
    print("🤖 AI Models:")
    results.append(check_finbert())
    results.append(check_lstm())
    results.append(check_ensemble())
    print()
    
    print("📱 Integrations:")
    results.append(check_telegram())
    print()
    
    print("="*60)
    
    critical_checks = results[:5]  # First 5 are critical
    
    if all(critical_checks):
        print("🎉 Phase 2 готова к использованию!")
        print()
        print("📝 Следующие шаги:")
        print("   1. python scripts/train_ensemble.py")
        print("   2. python scripts/test_ensemble.py")
        print("   3. python run_backtest.py --use-ensemble")
        print("   4. python main.py --use-ensemble --enable-telegram")
    elif any(critical_checks):
        print("⚠️ Phase 2 частично готова")
        print()
        print("Установите недостающие компоненты:")
        print("   pip install transformers torch python-telegram-bot")
    else:
        print("❌ Phase 2 не установлена")
        print()
        print("Установите зависимости:")
        print("   pip install -r requirements.txt")
    
    print("="*60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error running checks: {e}")
        sys.exit(1)
