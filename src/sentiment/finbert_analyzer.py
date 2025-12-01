"""
Advanced Sentiment Analyzer with FinBERT
=========================================
Использует финансово-специфичную BERT модель для более точного анализа новостей
"""

import logging
from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

from ..config.config_loader import get_config

logger = logging.getLogger(__name__)


class FinBERTSentimentAnalyzer:
    """
    Advanced sentiment analyzer using FinBERT model
    """
    
    def __init__(self):
        """Initialize FinBERT sentiment analyzer"""
        self.config = get_config()
        
        # API configuration
        self.cryptopanic_api_key = self.config.get(
            'news', 'cryptopanic_api_key', 
            default=None
        )
        self.cryptopanic_url = 'https://cryptopanic.com/api/v1/posts/'
        
        # Sentiment thresholds
        self.sentiment_threshold = self.config.get(
            'news', 'sentiment_threshold', 
            default=0.1
        )
        self.max_news_age_hours = self.config.get(
            'news', 'max_news_age_hours', 
            default=24
        )
        
        # FinBERT model
        self.model_name = 'ProsusAI/finbert'
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        try:
            logger.info(f"[SENTIMENT] Loading FinBERT model on {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info("[SENTIMENT] FinBERT model loaded successfully")
            self.finbert_available = True
        except Exception as e:
            logger.warning(f"[SENTIMENT] FinBERT not available: {e}. Using fallback TextBlob")
            self.finbert_available = False
            
            # Fallback to TextBlob
            try:
                from textblob import TextBlob
                self.textblob = TextBlob
            except ImportError:
                logger.error("[SENTIMENT] TextBlob also not available!")
                self.textblob = None
    
    def analyze_sentiment_finbert(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment using FinBERT
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores: {positive, negative, neutral}
        """
        if not text or not self.finbert_available:
            return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
        
        try:
            # Tokenize and prepare input
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=512,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # FinBERT returns: [positive, negative, neutral]
            scores = predictions[0].cpu().numpy()
            
            return {
                'positive': float(scores[0]),
                'negative': float(scores[1]),
                'neutral': float(scores[2])
            }
            
        except Exception as e:
            logger.error(f"[SENTIMENT] FinBERT analysis error: {e}")
            return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
    
    def analyze_sentiment_textblob(self, text: str) -> Dict[str, float]:
        """
        Fallback sentiment analysis using TextBlob
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        if not text or not self.textblob:
            return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
        
        try:
            blob = self.textblob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            
            # Convert to positive/negative/neutral
            if polarity > 0.1:
                return {
                    'positive': polarity,
                    'negative': 0.0,
                    'neutral': 1 - polarity
                }
            elif polarity < -0.1:
                return {
                    'positive': 0.0,
                    'negative': abs(polarity),
                    'neutral': 1 - abs(polarity)
                }
            else:
                return {
                    'positive': 0.0,
                    'negative': 0.0,
                    'neutral': 1.0
                }
                
        except Exception as e:
            logger.error(f"[SENTIMENT] TextBlob analysis error: {e}")
            return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment using best available method
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        if self.finbert_available:
            return self.analyze_sentiment_finbert(text)
        else:
            return self.analyze_sentiment_textblob(text)
    
    def fetch_news(self, symbol: str = 'BTC', limit: int = 20) -> List[Dict]:
        """
        Fetch recent news for a symbol
        
        Args:
            symbol: Cryptocurrency symbol (BTC, ETH, etc.)
            limit: Maximum number of news to fetch
            
        Returns:
            List of news articles
        """
        if not self.cryptopanic_api_key:
            logger.warning("[SENTIMENT] CryptoPanic API key not configured")
            return []
        
        try:
            params = {
                'auth_token': self.cryptopanic_api_key,
                'currencies': symbol,
                'filter': 'hot',
                'public': 'true'
            }
            
            response = requests.get(self.cryptopanic_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                news = data.get('results', [])
                
                # Filter by age
                cutoff_time = datetime.utcnow() - timedelta(hours=self.max_news_age_hours)
                filtered_news = []
                
                for article in news[:limit]:
                    published_at = datetime.fromisoformat(
                        article['published_at'].replace('Z', '+00:00')
                    )
                    if published_at >= cutoff_time:
                        filtered_news.append({
                            'title': article.get('title', ''),
                            'published_at': article.get('published_at'),
                            'url': article.get('url', ''),
                            'source': article.get('source', {}).get('title', 'Unknown')
                        })
                
                logger.info(f"[SENTIMENT] Fetched {len(filtered_news)} news for {symbol}")
                return filtered_news
            else:
                logger.error(f"[SENTIMENT] CryptoPanic API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"[SENTIMENT] Error fetching news: {e}")
            return []
    
    def get_aggregated_sentiment(
        self, 
        symbol: str = 'BTC',
        limit: int = 20
    ) -> Dict[str, float]:
        """
        Get aggregated sentiment from recent news
        
        Args:
            symbol: Cryptocurrency symbol
            limit: Number of news articles to analyze
            
        Returns:
            Dictionary with aggregated sentiment scores and individual news sentiments
        """
        news_articles = self.fetch_news(symbol, limit)
        
        if not news_articles:
            return {
                'sentiment_score': 0.0,
                'positive': 0.0,
                'negative': 0.0,
                'neutral': 1.0,
                'confidence': 0.0,
                'news_count': 0,
                'news_sentiments': []
            }
        
        # Analyze each news article
        sentiments = []
        for article in news_articles:
            text = article['title']
            sentiment = self.analyze_sentiment(text)
            
            sentiments.append({
                'title': article['title'],
                'source': article['source'],
                'sentiment': sentiment,
                'published_at': article['published_at']
            })
        
        # Aggregate sentiments
        avg_positive = np.mean([s['sentiment']['positive'] for s in sentiments])
        avg_negative = np.mean([s['sentiment']['negative'] for s in sentiments])
        avg_neutral = np.mean([s['sentiment']['neutral'] for s in sentiments])
        
        # Calculate overall sentiment score (-1 to 1)
        sentiment_score = avg_positive - avg_negative
        
        # Apply threshold
        if abs(sentiment_score) < self.sentiment_threshold:
            sentiment_score = 0.0
        
        # Calculate confidence (inverse of neutral score)
        confidence = 1 - avg_neutral
        
        logger.info(
            f"[SENTIMENT] {symbol} sentiment: {sentiment_score:.3f} "
            f"(+{avg_positive:.2f}, -{avg_negative:.2f}, confidence: {confidence:.2f})"
        )
        
        return {
            'sentiment_score': sentiment_score,
            'positive': avg_positive,
            'negative': avg_negative,
            'neutral': avg_neutral,
            'confidence': confidence,
            'news_count': len(news_articles),
            'news_sentiments': sentiments
        }
    
    def get_sentiment_signal(self, symbol: str = 'BTC') -> int:
        """
        Get trading signal based on sentiment
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            1 (bullish), -1 (bearish), or 0 (neutral)
        """
        result = self.get_aggregated_sentiment(symbol)
        
        sentiment_score = result['sentiment_score']
        confidence = result['confidence']
        
        # Требуем минимальную уверенность для сигнала
        min_confidence = 0.3
        
        if confidence < min_confidence:
            return 0
        
        # Генерируем сигнал
        if sentiment_score > 0.2:
            return 1  # Bullish
        elif sentiment_score < -0.2:
            return -1  # Bearish
        else:
            return 0  # Neutral


def get_sentiment_analyzer() -> FinBERTSentimentAnalyzer:
    """
    Get singleton instance of sentiment analyzer
    
    Returns:
        FinBERTSentimentAnalyzer instance
    """
    if not hasattr(get_sentiment_analyzer, '_instance'):
        get_sentiment_analyzer._instance = FinBERTSentimentAnalyzer()
    return get_sentiment_analyzer._instance


if __name__ == '__main__':
    # Test the analyzer
    logging.basicConfig(level=logging.INFO)
    
    analyzer = get_sentiment_analyzer()
    
    # Test with BTC
    print("\n=== Testing FinBERT Sentiment Analyzer ===")
    result = analyzer.get_aggregated_sentiment('BTC', limit=10)
    
    print(f"\nOverall Sentiment Score: {result['sentiment_score']:.3f}")
    print(f"Positive: {result['positive']:.2f}")
    print(f"Negative: {result['negative']:.2f}")
    print(f"Neutral: {result['neutral']:.2f}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"News analyzed: {result['news_count']}")
    
    signal = analyzer.get_sentiment_signal('BTC')
    signal_str = {1: 'BULLISH 📈', -1: 'BEARISH 📉', 0: 'NEUTRAL ➡️'}[signal]
    print(f"\nTrading Signal: {signal_str}")
    
    print("\n=== Recent News Sentiments ===")
    for i, news in enumerate(result['news_sentiments'][:5], 1):
        print(f"\n{i}. {news['title'][:80]}...")
        print(f"   Source: {news['source']}")
        print(f"   Sentiment: +{news['sentiment']['positive']:.2f} "
              f"-{news['sentiment']['negative']:.2f} "
              f"neutral:{news['sentiment']['neutral']:.2f}")
