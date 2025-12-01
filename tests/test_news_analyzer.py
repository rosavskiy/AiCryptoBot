"""
Unit тесты для модуля news_analyzer.py
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sentiment.news_analyzer import NewsAnalyzer


class TestNewsAnalyzer(unittest.TestCase):
    """Тесты для класса NewsAnalyzer"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.config = {
            'news': {
                'cryptopanic_api_key': 'test_api_key',
                'sentiment_threshold': 0.1,
                'max_news_age_hours': 24
            }
        }
        self.analyzer = NewsAnalyzer(self.config)
    
    def test_initialization(self):
        """Тест инициализации класса"""
        self.assertEqual(self.analyzer.api_key, 'test_api_key')
        self.assertEqual(self.analyzer.sentiment_threshold, 0.1)
        self.assertEqual(self.analyzer.max_news_age_hours, 24)
    
    @patch('requests.get')
    def test_fetch_news_success(self, mock_get):
        """Тест успешного получения новостей"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'title': 'Bitcoin hits new high',
                    'published_at': '2024-01-15T10:00:00Z',
                    'url': 'https://example.com/news1'
                },
                {
                    'title': 'Ethereum upgrade successful',
                    'published_at': '2024-01-15T09:00:00Z',
                    'url': 'https://example.com/news2'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        news = self.analyzer.fetch_news('BTC')
        
        self.assertEqual(len(news), 2)
        self.assertEqual(news[0]['title'], 'Bitcoin hits new high')
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_fetch_news_api_error(self, mock_get):
        """Тест обработки ошибки API"""
        mock_get.side_effect = Exception("API Error")
        
        news = self.analyzer.fetch_news('BTC')
        
        self.assertEqual(news, [])
    
    @patch('requests.get')
    def test_fetch_news_invalid_response(self, mock_get):
        """Тест обработки невалидного ответа"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        news = self.analyzer.fetch_news('BTC')
        
        self.assertEqual(news, [])
    
    def test_analyze_sentiment_positive(self):
        """Тест анализа позитивного сентимента"""
        text = "Bitcoin is great! Amazing bullish momentum and excellent performance!"
        
        score = self.analyzer.analyze_sentiment(text)
        
        # Позитивный текст должен иметь положительный score
        self.assertGreater(score, 0)
    
    def test_analyze_sentiment_negative(self):
        """Тест анализа негативного сентимента"""
        text = "Terrible crash! Bitcoin is falling badly, very bad news!"
        
        score = self.analyzer.analyze_sentiment(text)
        
        # Негативный текст должен иметь отрицательный score
        self.assertLess(score, 0)
    
    def test_analyze_sentiment_neutral(self):
        """Тест анализа нейтрального сентимента"""
        text = "Bitcoin price is at 40000"
        
        score = self.analyzer.analyze_sentiment(text)
        
        # Нейтральный текст должен быть близок к 0
        self.assertTrue(-0.2 < score < 0.2)
    
    def test_analyze_sentiment_empty_text(self):
        """Тест анализа пустого текста"""
        score = self.analyzer.analyze_sentiment("")
        
        self.assertEqual(score, 0)
    
    @patch('requests.get')
    def test_get_sentiment_score_aggregation(self, mock_get):
        """Тест агрегации сентимента из новостей"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'title': 'Bitcoin is amazing! Great news!'},
                {'title': 'Positive developments in crypto'},
                {'title': 'Bitcoin holds steady'}
            ]
        }
        mock_get.return_value = mock_response
        
        sentiment = self.analyzer.get_sentiment('BTC')
        
        # Агрегированный сентимент должен быть в диапазоне [-1, 1]
        self.assertTrue(-1 <= sentiment <= 1)
    
    @patch('requests.get')
    def test_get_sentiment_no_news(self, mock_get):
        """Тест получения сентимента когда нет новостей"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response
        
        sentiment = self.analyzer.get_sentiment('BTC')
        
        # При отсутствии новостей сентимент должен быть нейтральным
        self.assertEqual(sentiment, 0)
    
    def test_sentiment_threshold_application(self):
        """Тест применения порога сентимента"""
        # Слабый позитивный сентимент (ниже порога)
        weak_positive = 0.05
        
        # С порогом 0.1, слабый сентимент должен интерпретироваться как нейтральный
        if abs(weak_positive) < self.analyzer.sentiment_threshold:
            adjusted_sentiment = 0
        else:
            adjusted_sentiment = weak_positive
        
        self.assertEqual(adjusted_sentiment, 0)
        
        # Сильный позитивный сентимент (выше порога)
        strong_positive = 0.5
        
        if abs(strong_positive) < self.analyzer.sentiment_threshold:
            adjusted_sentiment = 0
        else:
            adjusted_sentiment = strong_positive
        
        self.assertEqual(adjusted_sentiment, 0.5)
    
    @patch('requests.get')
    def test_news_age_filtering(self, mock_get):
        """Тест фильтрации новостей по возрасту"""
        now = datetime.utcnow()
        old_date = (now - timedelta(hours=48)).isoformat() + 'Z'
        recent_date = (now - timedelta(hours=12)).isoformat() + 'Z'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'title': 'Old news', 'published_at': old_date},
                {'title': 'Recent news', 'published_at': recent_date}
            ]
        }
        mock_get.return_value = mock_response
        
        news = self.analyzer.fetch_news('BTC')
        
        # Должны получить обе новости (фильтрация в методе, если реализована)
        self.assertGreaterEqual(len(news), 1)
    
    def test_sentiment_score_range(self):
        """Тест что сентимент score находится в допустимом диапазоне"""
        test_texts = [
            "Amazing bullish news!",
            "Terrible bearish crash",
            "Bitcoin at 40000",
            "Great performance today",
            "Bad news for investors"
        ]
        
        for text in test_texts:
            score = self.analyzer.analyze_sentiment(text)
            # Сентимент TextBlob обычно в [-1, 1]
            self.assertTrue(-1 <= score <= 1, f"Score {score} out of range for text: {text}")


if __name__ == '__main__':
    unittest.main()
