"""
News Scheduler
==============
Periodically fetches news and updates sentiment analysis
"""

import logging
import threading
import time
import os
from datetime import datetime
from typing import Optional

from .news_analyzer import NewsAnalyzer

# Try to import FinBERT, fallback to None if not available
try:
    from .finbert_analyzer import FinBERTAnalyzer
    FINBERT_AVAILABLE = True
except ImportError:
    FinBERTAnalyzer = None
    FINBERT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("FinBERT not available (torch not installed), using TextBlob for sentiment analysis")

logger = logging.getLogger(__name__)


class NewsScheduler:
    """
    Manages periodic news fetching and sentiment analysis
    """
    
    def __init__(self, 
                 interval_minutes: int = 15,
                 symbols: list = None,
                 callback=None):
        """
        Initialize news scheduler
        
        Args:
            interval_minutes: How often to fetch news (default: 15)
            symbols: List of symbols to track (default: ['BTC'])
            callback: Function to call with news updates
        """
        self.interval_minutes = interval_minutes
        self.symbols = symbols or ['BTC']
        self.callback = callback
        
        # Initialize analyzers
        self.news_analyzer = NewsAnalyzer()
        self.finbert_analyzer = None
        
        if FINBERT_AVAILABLE:
            try:
                self.finbert_analyzer = FinBERTAnalyzer()
                logger.info('[NEWS] ✅ FinBERT analyzer initialized')
            except Exception as e:
                logger.warning(f'[NEWS] ⚠️ FinBERT init failed: {e}. Using TextBlob fallback.')
        else:
            logger.info('[NEWS] 📝 Using TextBlob for sentiment analysis (torch not installed)')
        
        # Scheduler state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_update: Optional[datetime] = None
        
        logger.info(f'[NEWS] Scheduler initialized: {interval_minutes}min interval, symbols: {symbols}')
    
    def start(self):
        """Start the news scheduler"""
        if self._running:
            logger.warning('[NEWS] Scheduler already running')
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()
        logger.info('[NEWS] ✅ Scheduler started')
    
    def stop(self):
        """Stop the news scheduler"""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info('[NEWS] ⏹️ Scheduler stopped')
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        # Fetch immediately on start
        self._fetch_and_analyze()
        
        while self._running:
            try:
                # Sleep in small chunks to allow quick shutdown
                for _ in range(self.interval_minutes * 60):
                    if not self._running:
                        break
                    time.sleep(1)
                
                if self._running:
                    self._fetch_and_analyze()
                    
            except Exception as e:
                logger.error(f'[NEWS] ❌ Scheduler error: {e}', exc_info=True)
                time.sleep(60)  # Wait 1 minute before retry
    
    def _fetch_and_analyze(self):
        """Fetch news and analyze sentiment"""
        try:
            logger.info('[NEWS] 📰 Fetching news...')
            self._last_update = datetime.now()
            
            all_news = []
            sentiments = []
            
            for symbol in self.symbols:
                # Fetch news
                news_items = self._fetch_news_for_symbol(symbol)
                
                if not news_items:
                    logger.warning(f'[NEWS] No news found for {symbol}')
                    continue
                
                logger.info(f'[NEWS] Fetched {len(news_items)} news items for {symbol}')
                
                # Analyze each news item
                for item in news_items:
                    sentiment_score, category = self._analyze_sentiment(item['title'])
                    
                    news_data = {
                        'symbol': symbol,
                        'title': item['title'],
                        'source': item.get('source', 'Unknown'),
                        'url': item.get('url', ''),
                        'published_at': item.get('published_at', datetime.now().isoformat()),
                        'sentiment': sentiment_score,
                        'category': category
                    }
                    
                    all_news.append(news_data)
                    sentiments.append(sentiment_score)
            
            if all_news:
                # Calculate average sentiment
                avg_sentiment = sum(sentiments) / len(sentiments)
                
                # Count categories
                positive = sum(1 for s in sentiments if s > 0.2)
                neutral = sum(1 for s in sentiments if -0.2 <= s <= 0.2)
                negative = sum(1 for s in sentiments if s < -0.2)
                
                logger.info(
                    f'[NEWS] 📊 Analysis complete: {len(all_news)} items | '
                    f'Avg sentiment: {avg_sentiment:.2f} | '
                    f'😊 {positive} | 😐 {neutral} | ☹️ {negative}'
                )
                
                # Call callback with results
                if self.callback:
                    self.callback({
                        'news': all_news,
                        'avg_sentiment': avg_sentiment,
                        'counts': {
                            'positive': positive,
                            'neutral': neutral,
                            'negative': negative
                        },
                        'timestamp': self._last_update.isoformat()
                    })
            else:
                logger.warning('[NEWS] ⚠️ No news items to analyze')
                
        except Exception as e:
            logger.error(f'[NEWS] ❌ Error fetching/analyzing news: {e}', exc_info=True)
    
    def _fetch_news_for_symbol(self, symbol: str) -> list:
        """Fetch news for a specific symbol"""
        try:
            # Get news headlines from internal methods
            news_titles = []
            source_used = None
            
            # Try CryptoPanic
            if self.news_analyzer.cryptopanic_key:
                try:
                    cp_titles = self.news_analyzer._fetch_cryptopanic(symbol, hours_back=24)
                    if cp_titles:
                        news_titles = cp_titles
                        source_used = 'CryptoPanic'
                        logger.debug(f'[NEWS] Got {len(cp_titles)} from CryptoPanic')
                except Exception as e:
                    logger.warning(f'[NEWS] CryptoPanic failed: {e}')
            
            # Try NewsAPI as fallback
            if not news_titles and self.news_analyzer.newsapi_key:
                try:
                    na_titles = self.news_analyzer._fetch_newsapi(symbol, hours_back=24)
                    if na_titles:
                        news_titles = na_titles
                        source_used = 'NewsAPI'
                        logger.debug(f'[NEWS] Got {len(na_titles)} from NewsAPI')
                except Exception as e:
                    logger.warning(f'[NEWS] NewsAPI failed: {e}')
            
            # Convert to dict format
            formatted_news = []
            for title in news_titles[:10]:  # Limit to 10 items
                formatted_news.append({
                    'title': title,
                    'source': source_used or 'Unknown',
                    'published_at': datetime.now().isoformat()
                })
            
            return formatted_news
            
        except Exception as e:
            logger.error(f'[NEWS] Error fetching news for {symbol}: {e}')
            return []
    
    def _analyze_sentiment(self, text: str) -> tuple:
        """
        Analyze sentiment of text
        
        Returns:
            tuple: (sentiment_score, category)
        """
        try:
            if self.finbert_analyzer:
                # Use FinBERT
                score = self.finbert_analyzer.analyze_sentiment(text)
            else:
                # Fallback to TextBlob
                from textblob import TextBlob
                blob = TextBlob(text)
                score = blob.sentiment.polarity
            
            # Categorize
            if score > 0.2:
                category = 'positive'
            elif score < -0.2:
                category = 'negative'
            else:
                category = 'neutral'
            
            return score, category
            
        except Exception as e:
            logger.error(f'[NEWS] Error analyzing sentiment: {e}')
            return 0.0, 'neutral'
    
    def get_last_update(self) -> Optional[datetime]:
        """Get timestamp of last update"""
        return self._last_update
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._running
    
    def force_update(self):
        """Force immediate news update"""
        if not self._running:
            logger.warning('[NEWS] Cannot force update - scheduler not running')
            return
        
        logger.info('[NEWS] 🔄 Forcing immediate update...')
        threading.Thread(target=self._fetch_and_analyze, daemon=True).start()


if __name__ == '__main__':
    # Test scheduler
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    def on_news_update(data):
        print(f"\n📰 NEWS UPDATE:")
        print(f"  Items: {len(data['news'])}")
        print(f"  Avg Sentiment: {data['avg_sentiment']:.2f}")
        print(f"  Positive: {data['counts']['positive']}")
        print(f"  Neutral: {data['counts']['neutral']}")
        print(f"  Negative: {data['counts']['negative']}")
        print(f"\nLatest news:")
        for news in data['news'][:3]:
            print(f"  - {news['title'][:60]}... (sentiment: {news['sentiment']:.2f})")
    
    scheduler = NewsScheduler(
        interval_minutes=1,  # Test with 1 minute
        symbols=['BTC', 'ETH'],
        callback=on_news_update
    )
    
    scheduler.start()
    
    try:
        print("Scheduler running... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
        print("Done!")
