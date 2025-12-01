"""
Sentiment Analysis Test Script
===============================
Tests the news fetching and sentiment analysis functionality.
"""

import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sentiment.news_analyzer import NewsAnalyzer


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_sentiment_analysis():
    """Test sentiment analysis for various symbols"""
    print("\n" + "="*80)
    print("   SENTIMENT ANALYSIS TEST")
    print("="*80 + "\n")
    
    analyzer = NewsAnalyzer()
    
    # Test symbols
    symbols = ['BTC', 'ETH']
    
    for symbol in symbols:
        print(f"\n[TESTING] Analyzing sentiment for {symbol}...")
        print("-" * 80)
        
        try:
            # Get sentiment
            sentiment = analyzer.get_sentiment(symbol, hours_back=24)
            
            print(f"[RESULT] Sentiment Analysis for {symbol}:")
            print(f"  Score:      {sentiment['score']:.4f} (-1 to 1)")
            print(f"  Label:      {sentiment['label'].upper()}")
            print(f"  Confidence: {sentiment['confidence']:.2%}")
            print(f"  News Count: {sentiment['news_count']}")
            print(f"  Sources:    {', '.join(sentiment['sources']) if sentiment['sources'] else 'None'}")
            print(f"  Cached:     {sentiment['cached']}")
            
            # Check if trading is allowed
            should_trade, score = analyzer.should_trade(symbol)
            print(f"\n  [FILTER] Should Trade: {'YES' if should_trade else 'NO'}")
            print(f"  [FILTER] Reason: {'Sentiment >= -0.1' if should_trade else 'Sentiment too negative'}")
            
        except Exception as e:
            print(f"[ERROR] Failed to analyze {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    # Test cache
    print("\n" + "="*80)
    print("[CACHE] Testing cache functionality...")
    print("="*80 + "\n")
    
    print("[INFO] Fetching BTC sentiment again (should use cache)...")
    sentiment_cached = analyzer.get_sentiment('BTC', hours_back=24)
    
    if sentiment_cached['cached']:
        print("[SUCCESS] Cache is working! Sentiment retrieved from cache.")
    else:
        print("[WARNING] Cache not used (might have expired)")
    
    print(f"  Cached Score: {sentiment_cached['score']:.4f}")


def test_manual_texts():
    """Test sentiment on manual text samples"""
    print("\n" + "="*80)
    print("   MANUAL TEXT SENTIMENT TEST")
    print("="*80 + "\n")
    
    analyzer = NewsAnalyzer()
    
    test_texts = [
        "Bitcoin surges to new all-time high as institutions adopt cryptocurrency",
        "Major hack leads to significant losses in crypto market",
        "Ethereum upgrade successfully implemented, network stable",
        "Regulatory concerns cause market uncertainty",
        "Bullish momentum continues as Bitcoin breaks resistance"
    ]
    
    print("[INFO] Analyzing sample news headlines:\n")
    
    for i, text in enumerate(test_texts, 1):
        sentiment = analyzer._analyze_texts([text])
        label = analyzer._score_to_label(sentiment)
        
        print(f"{i}. \"{text}\"")
        print(f"   Score: {sentiment:.4f} | Label: {label.upper()}\n")
    
    # Test aggregated sentiment
    print("[INFO] Aggregated sentiment of all texts:")
    agg_sentiment = analyzer._analyze_texts(test_texts)
    agg_label = analyzer._score_to_label(agg_sentiment)
    print(f"  Score: {agg_sentiment:.4f}")
    print(f"  Label: {agg_label.upper()}")


def main():
    """Run all tests"""
    setup_logging()
    
    print("\n" + "="*80)
    print("   AI CRYPTO BOT - SENTIMENT MODULE TEST")
    print("="*80)
    
    try:
        # Test manual text analysis first (doesn't require API keys)
        test_manual_texts()
        
        # Test live news fetching (requires API keys)
        print("\n\n[INFO] Attempting to fetch live news...")
        print("[INFO] If you see warnings about API keys, add them to .env file:")
        print("[INFO]   - CRYPTOPANIC_API_KEY from https://cryptopanic.com/developers/api/")
        print("[INFO]   - NEWSAPI_KEY from https://newsapi.org/register")
        print("-" * 80 + "\n")
        
        test_sentiment_analysis()
        
        print("\n" + "="*80)
        print("   ALL TESTS COMPLETED!")
        print("="*80)
        
        print("\n[INFO] Next steps:")
        print("   1. Add API keys to .env file for live news fetching")
        print("   2. Test with different symbols and time ranges")
        print("   3. Integrate with ML predictor for combined signals")
        print("   4. (Phase 2) Migrate to FinBERT for better accuracy")
        
    except Exception as e:
        logging.error(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
