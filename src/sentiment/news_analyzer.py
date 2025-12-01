"""
News Sentiment Analyzer
========================
Fetches crypto news from various sources and analyzes sentiment.
Supports: CryptoPanic API, NewsAPI
Sentiment: TextBlob (basic) with preparation for FinBERT migration.
"""

import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from textblob import TextBlob
import pandas as pd
from functools import lru_cache
import hashlib

from ..config.config_loader import get_config


logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """
    Analyzes sentiment from cryptocurrency news sources
    """
    
    def __init__(self, cache_duration_minutes: int = None):
        """
        Initialize news analyzer
        
        Args:
            cache_duration_minutes: How long to cache results (default from config)
        """
        self.config = get_config()
        self.cache_duration = cache_duration_minutes or \
            self.config.get('sentiment', 'cache_duration_minutes', default=30)
        
        # API endpoints
        self.cryptopanic_url = "https://cryptopanic.com/api/v1/posts/"
        self.newsapi_url = "https://newsapi.org/v2/everything"
        
        # Get API keys from environment
        import os
        self.cryptopanic_key = os.getenv('CRYPTOPANIC_API_KEY', '')
        self.newsapi_key = os.getenv('NEWSAPI_KEY', '')
        
        # Cache storage
        self._cache: Dict[str, Tuple[datetime, float]] = {}
        
        logger.info("[SENTIMENT] News Analyzer initialized")
    
    def get_sentiment(
        self,
        symbol: str = "BTC",
        hours_back: int = 24
    ) -> Dict[str, any]:
        """
        Get aggregated sentiment score for a symbol
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            hours_back: How many hours of news to analyze
        
        Returns:
            Dictionary with sentiment data:
            {
                'score': float (-1 to 1),
                'label': str ('positive', 'neutral', 'negative'),
                'confidence': float (0 to 1),
                'news_count': int,
                'sources': list,
                'cached': bool
            }
        """
        # Check cache first
        cache_key = f"{symbol}_{hours_back}"
        if cache_key in self._cache:
            cache_time, cached_score = self._cache[cache_key]
            if datetime.now() - cache_time < timedelta(minutes=self.cache_duration):
                logger.info(f"[CACHE] Using cached sentiment for {symbol}: {cached_score:.3f}")
                return {
                    'score': cached_score,
                    'label': self._score_to_label(cached_score),
                    'confidence': abs(cached_score),
                    'news_count': 0,
                    'sources': [],
                    'cached': True
                }
        
        # Fetch fresh news
        news_items = []
        sources_used = []
        
        # Try CryptoPanic first
        if self.cryptopanic_key:
            try:
                cp_news = self._fetch_cryptopanic(symbol, hours_back)
                news_items.extend(cp_news)
                sources_used.append('cryptopanic')
                logger.info(f"[CRYPTOPANIC] Fetched {len(cp_news)} news items")
            except Exception as e:
                logger.warning(f"[WARNING] CryptoPanic fetch failed: {e}")
        
        # Try NewsAPI as backup
        if self.newsapi_key and len(news_items) < 5:
            try:
                na_news = self._fetch_newsapi(symbol, hours_back)
                news_items.extend(na_news)
                sources_used.append('newsapi')
                logger.info(f"[NEWSAPI] Fetched {len(na_news)} news items")
            except Exception as e:
                logger.warning(f"[WARNING] NewsAPI fetch failed: {e}")
        
        # Analyze sentiment
        if not news_items:
            logger.warning(f"[WARNING] No news found for {symbol}, returning neutral sentiment")
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'news_count': 0,
                'sources': [],
                'cached': False
            }
        
        # Calculate aggregate sentiment
        sentiment_score = self._analyze_texts(news_items)
        
        # Cache result
        self._cache[cache_key] = (datetime.now(), sentiment_score)
        
        result = {
            'score': sentiment_score,
            'label': self._score_to_label(sentiment_score),
            'confidence': abs(sentiment_score),
            'news_count': len(news_items),
            'sources': sources_used,
            'cached': False
        }
        
        logger.info(f"[SENTIMENT] {symbol}: {result['label'].upper()} ({sentiment_score:.3f}) from {len(news_items)} articles")
        
        return result
    
    def _fetch_cryptopanic(self, symbol: str, hours_back: int) -> List[str]:
        """
        Fetch news from CryptoPanic API
        
        Args:
            symbol: Crypto symbol
            hours_back: Hours to look back
        
        Returns:
            List of news headlines/titles
        """
        if not self.cryptopanic_key:
            return []
        
        params = {
            'auth_token': self.cryptopanic_key,
            'currencies': symbol,
            'kind': 'news',  # news, media, all
            'filter': 'hot'  # rising, hot, bullish, bearish, important, saved, lol
        }
        
        try:
            response = requests.get(self.cryptopanic_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            news_items = []
            
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for post in data.get('results', []):
                # Parse timestamp
                pub_time = datetime.fromisoformat(post['published_at'].replace('Z', '+00:00'))
                
                if pub_time.replace(tzinfo=None) > cutoff_time:
                    title = post.get('title', '')
                    if title:
                        news_items.append(title)
            
            return news_items
            
        except Exception as e:
            logger.error(f"[ERROR] CryptoPanic API error: {e}")
            return []
    
    def _fetch_newsapi(self, symbol: str, hours_back: int) -> List[str]:
        """
        Fetch news from NewsAPI
        
        Args:
            symbol: Crypto symbol
            hours_back: Hours to look back
        
        Returns:
            List of news headlines
        """
        if not self.newsapi_key:
            return []
        
        # Map crypto symbols to search queries
        symbol_map = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'BNB': 'Binance',
            'SOL': 'Solana',
            'XRP': 'Ripple',
            'ADA': 'Cardano',
            'DOGE': 'Dogecoin'
        }
        
        search_term = symbol_map.get(symbol, symbol)
        
        # Calculate time range
        from_date = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        params = {
            'apiKey': self.newsapi_key,
            'q': f'{search_term} AND crypto',
            'language': 'en',
            'sortBy': 'publishedAt',
            'from': from_date,
            'pageSize': 20
        }
        
        try:
            response = requests.get(self.newsapi_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            news_items = []
            
            for article in data.get('articles', []):
                title = article.get('title', '')
                description = article.get('description', '')
                
                # Combine title and description for better analysis
                text = f"{title}. {description}" if description else title
                if text:
                    news_items.append(text)
            
            return news_items
            
        except Exception as e:
            logger.error(f"[ERROR] NewsAPI error: {e}")
            return []
    
    def _analyze_texts(self, texts: List[str]) -> float:
        """
        Analyze sentiment of multiple texts using TextBlob
        
        Args:
            texts: List of text strings to analyze
        
        Returns:
            Aggregated sentiment score (-1 to 1)
        """
        if not texts:
            return 0.0
        
        sentiments = []
        
        for text in texts:
            try:
                # TextBlob sentiment analysis
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity  # -1 (negative) to 1 (positive)
                sentiments.append(polarity)
                
            except Exception as e:
                logger.warning(f"[WARNING] Text analysis failed: {e}")
                continue
        
        if not sentiments:
            return 0.0
        
        # Calculate weighted average (more recent = higher weight)
        # For now, simple average. Can be improved with time-based weighting
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        return round(avg_sentiment, 4)
    
    def _score_to_label(self, score: float) -> str:
        """
        Convert numerical score to label
        
        Args:
            score: Sentiment score (-1 to 1)
        
        Returns:
            Label: 'positive', 'neutral', or 'negative'
        """
        if score > 0.1:
            return 'positive'
        elif score < -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def clear_cache(self):
        """Clear sentiment cache"""
        self._cache.clear()
        logger.info("[CACHE] Sentiment cache cleared")
    
    def should_trade(self, symbol: str = "BTC") -> Tuple[bool, float]:
        """
        Determine if sentiment allows trading
        
        Args:
            symbol: Crypto symbol
        
        Returns:
            Tuple of (should_trade: bool, sentiment_score: float)
        """
        sentiment = self.get_sentiment(symbol)
        score = sentiment['score']
        
        # Get threshold from config
        min_sentiment = self.config.get('sentiment', 'min_score', default=-0.1)
        
        should_trade = score >= min_sentiment
        
        if not should_trade:
            logger.warning(f"[FILTER] Sentiment too negative for {symbol}: {score:.3f} < {min_sentiment}")
        
        return should_trade, score
    
    # ==========================================
    # FUTURE: FinBERT Integration Placeholder
    # ==========================================
    
    def _analyze_with_finbert(self, texts: List[str]) -> float:
        """
        PLACEHOLDER: Analyze sentiment using FinBERT model
        
        FinBERT is a BERT model fine-tuned for financial sentiment analysis.
        Much more accurate than TextBlob for financial/crypto news.
        
        Migration steps:
        1. Install: pip install transformers torch
        2. Load model: AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        3. Process texts in batches
        4. Return aggregated sentiment
        
        Args:
            texts: List of news texts
        
        Returns:
            Sentiment score (-1 to 1)
        """
        # TODO: Implement FinBERT when ready for Phase 2
        logger.warning("[TODO] FinBERT not implemented yet, using TextBlob")
        return self._analyze_texts(texts)
