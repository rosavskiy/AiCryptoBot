"""
ML Predictor Module
===================
Machine Learning model for price prediction using RandomForest.
Includes Walk-Forward Validation to prevent data leakage.
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Tuple, List, Optional, Dict
from datetime import datetime, timedelta
import logging

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

from ..config.config_loader import get_config


logger = logging.getLogger(__name__)


class MLPredictor:
    """Machine Learning predictor for cryptocurrency price movements"""
    
    def __init__(self, model_path: str = None):
        """
        Initialize ML predictor
        
        Args:
            model_path: Path to save/load trained model
        """
        self.config = get_config()
        self.model = None
        self.feature_names = None
        self.model_metrics = {}
        
        # Set model path
        if model_path is None:
            project_root = Path(__file__).parent.parent.parent
            model_dir = project_root / "models"
            model_dir.mkdir(exist_ok=True)
            model_path = model_dir / "random_forest_model.joblib"
        
        self.model_path = Path(model_path)
        
        # Initialize model
        self._init_model()
    
    def _init_model(self):
        """Initialize RandomForest model with config parameters"""
        ml_config = self.config.get('ml', default={})
        
        self.model = RandomForestClassifier(
            n_estimators=ml_config.get('n_estimators', 100),
            min_samples_split=ml_config.get('min_samples_split', 10),
            max_depth=ml_config.get('max_depth', 15),
            random_state=ml_config.get('random_state', 42),
            n_jobs=-1,  # Use all CPU cores
            class_weight='balanced'  # Handle imbalanced data
        )
        
        logger.info(f"[ML] RandomForest initialized with {ml_config.get('n_estimators', 100)} estimators")
    
    def prepare_data(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """
        Prepare features and target from dataframe
        
        Args:
            df: DataFrame with features and target
        
        Returns:
            Tuple of (X_features, y_target, feature_names)
        """
        # Remove duplicate columns first
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Get feature list from config
        feature_list = self.config.get('ml', 'features', default=[
            'RSI', 'ATR', 'volume', 'SMA_50', 'SMA_200',
            'MACD', 'MACD_signal', 'BB_upper', 'BB_lower', 'volume_sma_ratio'
        ])
        
        # Filter available features
        available_features = [f for f in feature_list if f in df.columns]
        
        if not available_features:
            raise ValueError("No valid features found in dataframe")
        
        # Prepare X and y
        X = df[available_features].copy()
        y = df['Target'].copy() if 'Target' in df.columns else None
        
        # Handle infinite values
        X.replace([np.inf, -np.inf], np.nan, inplace=True)
        X.ffill(inplace=True)
        X.fillna(0, inplace=True)
        
        self.feature_names = available_features
        logger.info(f"[ML] Prepared {len(available_features)} features: {available_features}")
        
        return X, y, available_features
    
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        validation_split: float = 0.2
    ) -> Dict[str, float]:
        """
        Train the model with time-series cross-validation
        
        Args:
            X: Feature matrix
            y: Target vector
            validation_split: Fraction of data for validation
        
        Returns:
            Dictionary of training metrics
        """
        logger.info(f"[ML] Training model on {len(X)} samples...")
        
        # Time-series split for cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        
        # Cross-validation scores
        cv_scores = cross_val_score(
            self.model, X, y,
            cv=tscv,
            scoring='accuracy',
            n_jobs=-1
        )
        
        logger.info(f"[ML] Cross-validation accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
        
        # Split data for final validation
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Train on full training set
        self.model.fit(X_train, y_train)
        
        # Save feature names for later predictions
        self.feature_names = list(X_train.columns)
        
        # Evaluate on validation set
        y_pred = self.model.predict(X_val)
        y_pred_proba = self.model.predict_proba(X_val)
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_val, y_pred),
            'precision': precision_score(y_val, y_pred, zero_division=0),
            'recall': recall_score(y_val, y_pred, zero_division=0),
            'f1_score': f1_score(y_val, y_pred, zero_division=0),
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'train_samples': len(X_train),
            'val_samples': len(X_val)
        }
        
        self.model_metrics = metrics
        
        # Log results
        logger.info("="*80)
        logger.info("[ML] MODEL PERFORMANCE")
        logger.info("="*80)
        logger.info(f"Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"Precision: {metrics['precision']:.4f}")
        logger.info(f"Recall:    {metrics['recall']:.4f}")
        logger.info(f"F1-Score:  {metrics['f1_score']:.4f}")
        logger.info("="*80)
        
        # Classification report
        logger.info("\n" + classification_report(y_val, y_pred, target_names=['Down', 'Up']))
        
        # Feature importance
        self._log_feature_importance()
        
        return metrics
    
    def _log_feature_importance(self):
        """Log feature importance from trained model"""
        if self.model is None or self.feature_names is None:
            return
        
        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        logger.info("\n" + "="*80)
        logger.info("[ML] FEATURE IMPORTANCE (Top 10)")
        logger.info("="*80)
        
        # Show only available features (in case of mismatch)
        max_features = min(10, len(self.feature_names), len(indices))
        for i in range(max_features):
            idx = indices[i]
            if idx < len(self.feature_names):
                logger.info(f"{i+1:2d}. {self.feature_names[idx]:20s}: {importances[idx]:.4f}")
        
        logger.info("="*80 + "\n")
    
    def predict(
        self,
        X: pd.DataFrame,
        return_proba: bool = True
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Make predictions
        
        Args:
            X: Feature matrix
            return_proba: Return probability estimates
        
        Returns:
            Tuple of (predictions, probabilities)
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        # Ensure features match training - select only the features used during training
        if self.feature_names is not None:
            # Make sure we only use features that were in training, in the same order
            X = X[self.feature_names].copy()
        
        # Handle NaN values (inf handling not needed for our clean data)
        X = X.ffill().fillna(0)
        
        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X) if return_proba else None
        
        return predictions, probabilities
    
    def predict_single(
        self,
        features: pd.Series
    ) -> Tuple[int, float]:
        """
        Predict for a single data point
        
        Args:
            features: Feature values as Series or dict-like
        
        Returns:
            Tuple of (prediction, confidence)
        """
        # Ensure we have the right features in the right order
        if self.feature_names is None:
            raise ValueError("Model not trained - feature names not available")
        
        # Remove duplicate indices if any (like duplicate 'volume')
        if features.index.duplicated().any():
            # Keep only first occurrence of each feature
            features = features[~features.index.duplicated(keep='first')]
        
        # Extract only the features we need, in the correct order
        feature_values = []
        for fname in self.feature_names:
            if fname in features.index:
                feature_values.append(features[fname])
            else:
                feature_values.append(0)  # Default value for missing features
        
        # Create DataFrame with correct structure
        X = pd.DataFrame([feature_values], columns=self.feature_names)
        
        # Predict
        pred, proba = self.predict(X, return_proba=True)
        
        prediction = pred[0]
        confidence = proba[0][prediction]
        
        return prediction, confidence
    
    def walk_forward_validation(
        self,
        df: pd.DataFrame,
        train_days: int = None,
        test_days: int = None,
        step_days: int = None
    ) -> List[Dict]:
        """
        Walk-Forward Validation to prevent data leakage
        
        This is critical for time-series ML:
        - Train on period A
        - Test on period B (immediately after A)
        - Retrain on A+B
        - Test on period C
        - And so on...
        
        Args:
            df: Full dataset with datetime index
            train_days: Training window size
            test_days: Test window size
            step_days: How many days to move forward
        
        Returns:
            List of validation results
        """
        # Get config defaults
        wf_config = self.config.get('ml', 'walk_forward', default={})
        
        if train_days is None:
            train_days = wf_config.get('train_period_days', 90)
        if test_days is None:
            test_days = wf_config.get('test_period_days', 30)
        if step_days is None:
            step_days = wf_config.get('step_days', 15)
        
        logger.info("[ML] Starting Walk-Forward Validation...")
        logger.info(f"   Train: {train_days} days | Test: {test_days} days | Step: {step_days} days")
        
        results = []
        
        # Prepare features
        X, y, features = self.prepare_data(df)
        
        # Convert days to number of samples (approximate)
        # Assuming we have 96 bars per day for 15m timeframe
        bars_per_day = 96  # 24h * 4 bars/hour for 15m
        train_samples = train_days * bars_per_day
        test_samples = test_days * bars_per_day
        step_samples = step_days * bars_per_day
        
        start_idx = 0
        fold = 1
        
        while start_idx + train_samples + test_samples <= len(X):
            train_end = start_idx + train_samples
            test_end = train_end + test_samples
            
            # Split data
            X_train = X.iloc[start_idx:train_end]
            y_train = y.iloc[start_idx:train_end]
            X_test = X.iloc[train_end:test_end]
            y_test = y.iloc[train_end:test_end]
            
            # Train model
            logger.info(f"\n[ML] Fold {fold}: Training on {len(X_train)} samples...")
            self.model.fit(X_train, y_train)
            
            # Test model
            y_pred = self.model.predict(X_test)
            y_proba = self.model.predict_proba(X_test)
            
            # Calculate metrics
            fold_metrics = {
                'fold': fold,
                'train_start': X_train.index[0],
                'train_end': X_train.index[-1],
                'test_start': X_test.index[0],
                'test_end': X_test.index[-1],
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, zero_division=0),
                'recall': recall_score(y_test, y_pred, zero_division=0),
                'f1_score': f1_score(y_test, y_pred, zero_division=0),
                'train_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
            results.append(fold_metrics)
            
            logger.info(f"[SUCCESS] Fold {fold} - Accuracy: {fold_metrics['accuracy']:.4f}, "
                       f"Precision: {fold_metrics['precision']:.4f}")
            
            # Move forward
            start_idx += step_samples
            fold += 1
        
        # Summary statistics
        avg_metrics = {
            'avg_accuracy': np.mean([r['accuracy'] for r in results]),
            'avg_precision': np.mean([r['precision'] for r in results]),
            'avg_recall': np.mean([r['recall'] for r in results]),
            'avg_f1': np.mean([r['f1_score'] for r in results]),
            'std_accuracy': np.std([r['accuracy'] for r in results])
        }
        
        logger.info("\n" + "="*80)
        logger.info("[ML] WALK-FORWARD VALIDATION SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Folds: {len(results)}")
        logger.info(f"Avg Accuracy:  {avg_metrics['avg_accuracy']:.4f} (+/- {avg_metrics['std_accuracy']:.4f})")
        logger.info(f"Avg Precision: {avg_metrics['avg_precision']:.4f}")
        logger.info(f"Avg Recall:    {avg_metrics['avg_recall']:.4f}")
        logger.info(f"Avg F1-Score:  {avg_metrics['avg_f1']:.4f}")
        logger.info("="*80 + "\n")
        
        return results
    
    def save_model(self, path: str = None):
        """Save trained model to disk"""
        if path is None:
            path = self.model_path
        
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'metrics': self.model_metrics,
            'timestamp': datetime.now()
        }
        
        joblib.dump(model_data, path)
        logger.info(f"[SUCCESS] Model saved to {path}")
    
    def load_model(self, path: str = None):
        """Load trained model from disk"""
        if path is None:
            path = self.model_path
        
        if not Path(path).exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        
        model_data = joblib.load(path)
        
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        self.model_metrics = model_data.get('metrics', {})
        
        logger.info(f"[SUCCESS] Model loaded from {path}")
        logger.info(f"   Trained: {model_data.get('timestamp', 'Unknown')}")
        
        if self.model_metrics:
            logger.info(f"   Accuracy: {self.model_metrics.get('accuracy', 0):.4f}")


def main():
    """Test ML predictor"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Import data fetcher
    from ..data.market_data import MarketDataFetcher
    
    # Fetch data
    fetcher = MarketDataFetcher()
    df = fetcher.get_market_data(symbol='BTC/USDT', timeframe='15m', limit=2000)
    
    # Initialize predictor
    predictor = MLPredictor()
    
    # Prepare data
    X, y, features = predictor.prepare_data(df)
    
    # Train model
    print("\n" + "="*80)
    print("🎯 TRAINING MODEL")
    print("="*80)
    metrics = predictor.train(X, y, validation_split=0.2)
    
    # Save model
    predictor.save_model()
    
    # Test prediction on last row
    last_features = X.iloc[-1]
    prediction, confidence = predictor.predict_single(last_features)
    
    print("\n" + "="*80)
    print("🔮 PREDICTION TEST")
    print("="*80)
    print(f"Direction: {'UP ⬆️' if prediction == 1 else 'DOWN ⬇️'}")
    print(f"Confidence: {confidence:.2%}")
    print("="*80)


if __name__ == "__main__":
    main()
