"""
LSTM Neural Network for Time Series Prediction
===============================================
Дополняет RandomForest для прогнозирования ценовых движений
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, List, Optional
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path

from ..config.config_loader import get_config

logger = logging.getLogger(__name__)


class TimeSeriesDataset(Dataset):
    """PyTorch Dataset for time series data"""
    
    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.LongTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class LSTMModel(nn.Module):
    """
    LSTM Neural Network for time series classification
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        num_classes: int = 3
    ):
        super(LSTMModel, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        # Fully connected layers
        self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden_size // 2, num_classes)
    
    def forward(self, x):
        # LSTM forward pass
        lstm_out, _ = self.lstm(x)
        
        # Take the last output
        last_output = lstm_out[:, -1, :]
        
        # Fully connected layers
        out = self.fc1(last_output)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        
        return out


class LSTMPredictor:
    """
    LSTM-based predictor for cryptocurrency price movements
    """
    
    def __init__(self):
        """Initialize LSTM predictor"""
        self.config = get_config()
        
        # Model parameters
        self.sequence_length = self.config.get('ml', 'lstm_sequence_length', default=60)
        self.hidden_size = self.config.get('ml', 'lstm_hidden_size', default=128)
        self.num_layers = self.config.get('ml', 'lstm_num_layers', default=2)
        self.dropout = self.config.get('ml', 'lstm_dropout', default=0.2)
        self.learning_rate = self.config.get('ml', 'lstm_learning_rate', default=0.001)
        self.batch_size = self.config.get('ml', 'lstm_batch_size', default=32)
        self.epochs = self.config.get('ml', 'lstm_epochs', default=50)
        
        # Device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"[LSTM] Using device: {self.device}")
        
        # Model components
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.input_size = 0
        
    def create_sequences(
        self,
        data: np.ndarray,
        targets: np.ndarray,
        sequence_length: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM training
        
        Args:
            data: Feature data
            targets: Target values
            sequence_length: Length of each sequence
            
        Returns:
            Tuple of (sequences, targets)
        """
        sequences = []
        sequence_targets = []
        
        for i in range(len(data) - sequence_length):
            sequences.append(data[i:i + sequence_length])
            sequence_targets.append(targets[i + sequence_length])
        
        return np.array(sequences), np.array(sequence_targets)
    
    def train(
        self,
        df: pd.DataFrame,
        feature_columns: List[str],
        validation_split: float = 0.2
    ) -> bool:
        """
        Train LSTM model
        
        Args:
            df: DataFrame with features and target
            feature_columns: List of feature column names
            validation_split: Fraction of data for validation
            
        Returns:
            True if training successful, False otherwise
        """
        try:
            # Validate data
            if len(df) < self.sequence_length * 2:
                logger.error(f"[LSTM] Insufficient data: {len(df)} < {self.sequence_length * 2}")
                return False
            
            # Check for required columns
            missing_cols = [col for col in feature_columns if col not in df.columns]
            if missing_cols:
                logger.error(f"[LSTM] Missing columns: {missing_cols}")
                return False
            
            if 'target' not in df.columns:
                logger.error("[LSTM] 'target' column not found")
                return False
            
            # Store feature columns
            self.feature_columns = feature_columns
            self.input_size = len(feature_columns)
            
            # Prepare data
            df_clean = df[feature_columns + ['target']].dropna()
            
            if len(df_clean) < self.sequence_length * 2:
                logger.error("[LSTM] Insufficient data after removing NaN")
                return False
            
            X = df_clean[feature_columns].values
            y = df_clean['target'].values
            
            # Convert target to 0, 1, 2 (for -1, 0, 1)
            y = y + 1
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Create sequences
            X_seq, y_seq = self.create_sequences(X_scaled, y, self.sequence_length)
            
            logger.info(f"[LSTM] Created {len(X_seq)} sequences")
            
            # Train/validation split
            split_idx = int(len(X_seq) * (1 - validation_split))
            X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
            y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]
            
            # Create datasets
            train_dataset = TimeSeriesDataset(X_train, y_train)
            val_dataset = TimeSeriesDataset(X_val, y_val)
            
            train_loader = DataLoader(
                train_dataset,
                batch_size=self.batch_size,
                shuffle=True
            )
            val_loader = DataLoader(
                val_dataset,
                batch_size=self.batch_size,
                shuffle=False
            )
            
            # Initialize model
            self.model = LSTMModel(
                input_size=self.input_size,
                hidden_size=self.hidden_size,
                num_layers=self.num_layers,
                dropout=self.dropout,
                num_classes=3
            ).to(self.device)
            
            # Loss and optimizer
            criterion = nn.CrossEntropyLoss()
            optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
            
            # Training loop
            best_val_loss = float('inf')
            patience = 10
            patience_counter = 0
            
            logger.info(f"[LSTM] Starting training for {self.epochs} epochs...")
            
            for epoch in range(self.epochs):
                # Training phase
                self.model.train()
                train_loss = 0.0
                train_correct = 0
                train_total = 0
                
                for sequences, targets in train_loader:
                    sequences = sequences.to(self.device)
                    targets = targets.to(self.device)
                    
                    # Forward pass
                    outputs = self.model(sequences)
                    loss = criterion(outputs, targets)
                    
                    # Backward pass
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    
                    train_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    train_total += targets.size(0)
                    train_correct += (predicted == targets).sum().item()
                
                train_loss /= len(train_loader)
                train_acc = 100 * train_correct / train_total
                
                # Validation phase
                self.model.eval()
                val_loss = 0.0
                val_correct = 0
                val_total = 0
                
                with torch.no_grad():
                    for sequences, targets in val_loader:
                        sequences = sequences.to(self.device)
                        targets = targets.to(self.device)
                        
                        outputs = self.model(sequences)
                        loss = criterion(outputs, targets)
                        
                        val_loss += loss.item()
                        _, predicted = torch.max(outputs.data, 1)
                        val_total += targets.size(0)
                        val_correct += (predicted == targets).sum().item()
                
                val_loss /= len(val_loader)
                val_acc = 100 * val_correct / val_total
                
                # Log progress every 10 epochs
                if (epoch + 1) % 10 == 0:
                    logger.info(
                        f"[LSTM] Epoch {epoch+1}/{self.epochs} - "
                        f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}% - "
                        f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%"
                    )
                
                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        logger.info(f"[LSTM] Early stopping at epoch {epoch+1}")
                        break
            
            logger.info(f"[LSTM] Training completed. Best val loss: {best_val_loss:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"[LSTM] Training error: {e}")
            return False
    
    def predict(
        self,
        df: pd.DataFrame,
        return_probabilities: bool = False
    ) -> Tuple[int, float]:
        """
        Predict signal for the most recent data
        
        Args:
            df: DataFrame with recent data (at least sequence_length rows)
            return_probabilities: If True, return full probability distribution
            
        Returns:
            Tuple of (signal, confidence)
            signal: -1 (sell), 0 (hold), 1 (buy)
            confidence: Prediction confidence (0-1)
        """
        if self.model is None:
            logger.warning("[LSTM] Model not trained")
            return 0, 0.33
        
        try:
            # Prepare data
            if len(df) < self.sequence_length:
                logger.warning(f"[LSTM] Insufficient data: {len(df)} < {self.sequence_length}")
                return 0, 0.33
            
            # Get last sequence
            X = df[self.feature_columns].iloc[-self.sequence_length:].values
            X_scaled = self.scaler.transform(X)
            X_seq = X_scaled.reshape(1, self.sequence_length, self.input_size)
            
            # Convert to tensor
            X_tensor = torch.FloatTensor(X_seq).to(self.device)
            
            # Predict
            self.model.eval()
            with torch.no_grad():
                outputs = self.model(X_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                confidence, predicted = torch.max(probabilities, 1)
            
            # Convert back to -1, 0, 1
            signal = predicted.item() - 1
            confidence_val = confidence.item()
            
            if return_probabilities:
                probs = probabilities.cpu().numpy()[0]
                return signal, confidence_val, probs
            
            return signal, confidence_val
            
        except Exception as e:
            logger.error(f"[LSTM] Prediction error: {e}")
            return 0, 0.33
    
    def save_model(self, filepath: str):
        """Save model to file"""
        if self.model is None:
            logger.warning("[LSTM] No model to save")
            return
        
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            checkpoint = {
                'model_state_dict': self.model.state_dict(),
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'input_size': self.input_size,
                'hidden_size': self.hidden_size,
                'num_layers': self.num_layers,
                'sequence_length': self.sequence_length
            }
            
            torch.save(checkpoint, filepath)
            logger.info(f"[LSTM] Model saved to {filepath}")
            
        except Exception as e:
            logger.error(f"[LSTM] Error saving model: {e}")
    
    def load_model(self, filepath: str) -> bool:
        """Load model from file"""
        try:
            checkpoint = torch.load(filepath, map_location=self.device)
            
            # Restore parameters
            self.scaler = checkpoint['scaler']
            self.feature_columns = checkpoint['feature_columns']
            self.input_size = checkpoint['input_size']
            self.hidden_size = checkpoint['hidden_size']
            self.num_layers = checkpoint['num_layers']
            self.sequence_length = checkpoint['sequence_length']
            
            # Restore model
            self.model = LSTMModel(
                input_size=self.input_size,
                hidden_size=self.hidden_size,
                num_layers=self.num_layers,
                num_classes=3
            ).to(self.device)
            
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            
            logger.info(f"[LSTM] Model loaded from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"[LSTM] Error loading model: {e}")
            return False


if __name__ == '__main__':
    # Test LSTM predictor
    logging.basicConfig(level=logging.INFO)
    
    print("\n=== Testing LSTM Predictor ===")
    
    # Create dummy data
    n_samples = 1000
    n_features = 10
    
    np.random.seed(42)
    data = {
        f'feature_{i}': np.random.randn(n_samples) 
        for i in range(n_features)
    }
    data['target'] = np.random.choice([-1, 0, 1], n_samples)
    
    df = pd.DataFrame(data)
    feature_cols = [f'feature_{i}' for i in range(n_features)]
    
    # Train model
    predictor = LSTMPredictor()
    success = predictor.train(df, feature_cols, validation_split=0.2)
    
    if success:
        print("✅ Training successful!")
        
        # Test prediction
        signal, confidence = predictor.predict(df.tail(100))
        signal_str = {-1: 'SELL', 0: 'HOLD', 1: 'BUY'}[signal]
        print(f"\nPrediction: {signal_str} (confidence: {confidence:.2%})")
        
        # Save model
        predictor.save_model('models/lstm_test.pth')
        print("✅ Model saved")
    else:
        print("❌ Training failed")
