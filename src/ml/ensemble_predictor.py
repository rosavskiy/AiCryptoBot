"""
Ensemble Predictor
==================
Комбинирует RandomForest и LSTM для более точных предсказаний
"""

import logging
from typing import Tuple, Dict, List
import pandas as pd
import numpy as np

from .predictor import MLPredictor
from .lstm_predictor import LSTMPredictor
from ..sentiment.finbert_analyzer import get_sentiment_analyzer
from ..config.config_loader import get_config

logger = logging.getLogger(__name__)


class EnsemblePredictor:
    """
    Ensemble predictor combining RandomForest, LSTM, and sentiment analysis
    """
    
    def __init__(self):
        """Initialize ensemble predictor"""
        self.config = get_config()
        
        # Initialize models
        self.rf_predictor = MLPredictor()
        self.lstm_predictor = LSTMPredictor()
        self.sentiment_analyzer = get_sentiment_analyzer()
        
        # Weights for ensemble
        self.rf_weight = self.config.get('ml', 'ensemble_rf_weight', default=0.4)
        self.lstm_weight = self.config.get('ml', 'ensemble_lstm_weight', default=0.4)
        self.sentiment_weight = self.config.get('ml', 'ensemble_sentiment_weight', default=0.2)
        
        # Normalize weights
        total_weight = self.rf_weight + self.lstm_weight + self.sentiment_weight
        self.rf_weight /= total_weight
        self.lstm_weight /= total_weight
        self.sentiment_weight /= total_weight
        
        logger.info(
            f"[ENSEMBLE] Weights - RF: {self.rf_weight:.2f}, "
            f"LSTM: {self.lstm_weight:.2f}, Sentiment: {self.sentiment_weight:.2f}"
        )
        
        # Minimum confidence threshold
        self.min_confidence = self.config.get('trading', 'min_confidence', default=0.6)
        
        # Model status
        self.rf_trained = False
        self.lstm_trained = False
    
    def train(
        self,
        df: pd.DataFrame,
        feature_columns: List[str]
    ) -> Dict[str, bool]:
        """
        Train all models in ensemble
        
        Args:
            df: DataFrame with features and target
            feature_columns: List of feature column names
            
        Returns:
            Dictionary with training status for each model
        """
        results = {}
        
        # Train RandomForest
        logger.info("[ENSEMBLE] Training RandomForest...")
        self.rf_trained = self.rf_predictor.train(df, feature_columns)
        results['random_forest'] = self.rf_trained
        
        if self.rf_trained:
            logger.info("[ENSEMBLE] ✅ RandomForest trained successfully")
        else:
            logger.warning("[ENSEMBLE] ❌ RandomForest training failed")
        
        # Train LSTM
        logger.info("[ENSEMBLE] Training LSTM...")
        self.lstm_trained = self.lstm_predictor.train(df, feature_columns)
        results['lstm'] = self.lstm_trained
        
        if self.lstm_trained:
            logger.info("[ENSEMBLE] ✅ LSTM trained successfully")
        else:
            logger.warning("[ENSEMBLE] ❌ LSTM training failed")
        
        # Sentiment analyzer doesn't need training
        results['sentiment'] = True
        
        return results
    
    def predict(
        self,
        df: pd.DataFrame,
        symbol: str = 'BTC'
    ) -> Tuple[int, float, Dict]:
        """
        Make ensemble prediction
        
        Args:
            df: DataFrame with recent data
            symbol: Trading symbol for sentiment analysis
            
        Returns:
            Tuple of (signal, confidence, details)
            signal: -1 (sell), 0 (hold), 1 (buy)
            confidence: Prediction confidence (0-1)
            details: Dictionary with individual predictions
        """
        details = {
            'random_forest': {'signal': 0, 'confidence': 0.33},
            'lstm': {'signal': 0, 'confidence': 0.33},
            'sentiment': {'signal': 0, 'score': 0.0}
        }
        
        # Get RandomForest prediction
        if self.rf_trained and self.rf_predictor.model is not None:
            rf_signal, rf_conf = self.rf_predictor.predict_single(df)
            details['random_forest'] = {
                'signal': rf_signal,
                'confidence': rf_conf
            }
            logger.debug(f"[ENSEMBLE] RF: signal={rf_signal}, conf={rf_conf:.2%}")
        else:
            logger.warning("[ENSEMBLE] RandomForest not available")
        
        # Get LSTM prediction
        if self.lstm_trained and self.lstm_predictor.model is not None:
            lstm_signal, lstm_conf = self.lstm_predictor.predict(df)
            details['lstm'] = {
                'signal': lstm_signal,
                'confidence': lstm_conf
            }
            logger.debug(f"[ENSEMBLE] LSTM: signal={lstm_signal}, conf={lstm_conf:.2%}")
        else:
            logger.warning("[ENSEMBLE] LSTM not available")
        
        # Get sentiment
        try:
            sentiment_result = self.sentiment_analyzer.get_aggregated_sentiment(symbol)
            sentiment_signal = self.sentiment_analyzer.get_sentiment_signal(symbol)
            details['sentiment'] = {
                'signal': sentiment_signal,
                'score': sentiment_result['sentiment_score'],
                'confidence': sentiment_result['confidence']
            }
            logger.debug(
                f"[ENSEMBLE] Sentiment: signal={sentiment_signal}, "
                f"score={sentiment_result['sentiment_score']:.2f}"
            )
        except Exception as e:
            logger.error(f"[ENSEMBLE] Sentiment analysis error: {e}")
        
        # Combine predictions using weighted voting
        rf_signal = details['random_forest']['signal']
        rf_conf = details['random_forest']['confidence']
        
        lstm_signal = details['lstm']['signal']
        lstm_conf = details['lstm']['confidence']
        
        sentiment_signal = details['sentiment']['signal']
        
        # Calculate weighted scores for each direction
        buy_score = 0.0
        sell_score = 0.0
        hold_score = 0.0
        
        # RandomForest contribution
        if rf_signal == 1:
            buy_score += self.rf_weight * rf_conf
        elif rf_signal == -1:
            sell_score += self.rf_weight * rf_conf
        else:
            hold_score += self.rf_weight * rf_conf
        
        # LSTM contribution
        if lstm_signal == 1:
            buy_score += self.lstm_weight * lstm_conf
        elif lstm_signal == -1:
            sell_score += self.lstm_weight * lstm_conf
        else:
            hold_score += self.lstm_weight * lstm_conf
        
        # Sentiment contribution
        if sentiment_signal == 1:
            buy_score += self.sentiment_weight
        elif sentiment_signal == -1:
            sell_score += self.sentiment_weight
        else:
            hold_score += self.sentiment_weight
        
        # Determine final signal
        max_score = max(buy_score, sell_score, hold_score)
        
        if max_score == buy_score and buy_score > 0:
            final_signal = 1
            confidence = buy_score
        elif max_score == sell_score and sell_score > 0:
            final_signal = -1
            confidence = sell_score
        else:
            final_signal = 0
            confidence = hold_score
        
        # Apply confidence threshold
        if confidence < self.min_confidence:
            logger.info(
                f"[ENSEMBLE] Signal {final_signal} rejected due to low confidence "
                f"({confidence:.2%} < {self.min_confidence:.2%})"
            )
            final_signal = 0
        
        logger.info(
            f"[ENSEMBLE] Final prediction: signal={final_signal}, "
            f"confidence={confidence:.2%}"
        )
        logger.info(
            f"[ENSEMBLE] Scores - Buy: {buy_score:.3f}, "
            f"Sell: {sell_score:.3f}, Hold: {hold_score:.3f}"
        )
        
        details['ensemble'] = {
            'signal': final_signal,
            'confidence': confidence,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'hold_score': hold_score
        }
        
        return final_signal, confidence, details
    
    def save_models(self, base_path: str):
        """
        Save all models
        
        Args:
            base_path: Base directory for model files
        """
        from pathlib import Path
        base_path = Path(base_path)
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Save RandomForest
        if self.rf_trained:
            rf_path = base_path / 'random_forest.pkl'
            self.rf_predictor.save_model(str(rf_path))
            logger.info(f"[ENSEMBLE] RandomForest saved to {rf_path}")
        
        # Save LSTM
        if self.lstm_trained:
            lstm_path = base_path / 'lstm_model.pth'
            self.lstm_predictor.save_model(str(lstm_path))
            logger.info(f"[ENSEMBLE] LSTM saved to {lstm_path}")
    
    def load_models(self, base_path: str) -> Dict[str, bool]:
        """
        Load all models
        
        Args:
            base_path: Base directory for model files
            
        Returns:
            Dictionary with load status for each model
        """
        from pathlib import Path
        base_path = Path(base_path)
        
        results = {}
        
        # Load RandomForest
        rf_path = base_path / 'random_forest.pkl'
        if rf_path.exists():
            self.rf_trained = self.rf_predictor.load_model(str(rf_path))
            results['random_forest'] = self.rf_trained
            if self.rf_trained:
                logger.info("[ENSEMBLE] ✅ RandomForest loaded")
        else:
            logger.warning(f"[ENSEMBLE] RandomForest model not found at {rf_path}")
            results['random_forest'] = False
        
        # Load LSTM
        lstm_path = base_path / 'lstm_model.pth'
        if lstm_path.exists():
            self.lstm_trained = self.lstm_predictor.load_model(str(lstm_path))
            results['lstm'] = self.lstm_trained
            if self.lstm_trained:
                logger.info("[ENSEMBLE] ✅ LSTM loaded")
        else:
            logger.warning(f"[ENSEMBLE] LSTM model not found at {lstm_path}")
            results['lstm'] = False
        
        return results
    
    def get_model_status(self) -> Dict[str, bool]:
        """
        Get status of all models
        
        Returns:
            Dictionary with model availability status
        """
        return {
            'random_forest': self.rf_trained and self.rf_predictor.model is not None,
            'lstm': self.lstm_trained and self.lstm_predictor.model is not None,
            'sentiment': self.sentiment_analyzer.finbert_available or self.sentiment_analyzer.textblob is not None
        }


def get_ensemble_predictor() -> EnsemblePredictor:
    """
    Get singleton instance of ensemble predictor
    
    Returns:
        EnsemblePredictor instance
    """
    if not hasattr(get_ensemble_predictor, '_instance'):
        get_ensemble_predictor._instance = EnsemblePredictor()
    return get_ensemble_predictor._instance


if __name__ == '__main__':
    # Test ensemble predictor
    logging.basicConfig(level=logging.INFO)
    
    print("\n=== Testing Ensemble Predictor ===")
    
    # Create dummy data
    n_samples = 1000
    feature_cols = [
        'open', 'high', 'low', 'close', 'volume',
        'sma_20', 'sma_50', 'ema_12', 'ema_26',
        'rsi', 'macd', 'atr'
    ]
    
    np.random.seed(42)
    data = {col: np.random.randn(n_samples) for col in feature_cols}
    data['target'] = np.random.choice([-1, 0, 1], n_samples)
    
    df = pd.DataFrame(data)
    
    # Train ensemble
    ensemble = get_ensemble_predictor()
    results = ensemble.train(df, feature_cols)
    
    print("\n📊 Training Results:")
    for model, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {model}: {'Success' if success else 'Failed'}")
    
    # Make prediction
    signal, confidence, details = ensemble.predict(df.tail(100), 'BTC')
    
    signal_str = {-1: '📉 SELL', 0: '➡️ HOLD', 1: '📈 BUY'}[signal]
    print(f"\n🎯 Ensemble Prediction: {signal_str} (confidence: {confidence:.2%})")
    
    print("\n📋 Model Details:")
    for model, info in details.items():
        if model != 'ensemble':
            print(f"  {model}: signal={info.get('signal', 0)}, "
                  f"confidence={info.get('confidence', 0):.2%}")
