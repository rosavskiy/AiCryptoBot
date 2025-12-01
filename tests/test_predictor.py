"""
Unit тесты для модуля predictor.py
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
import sys
import os
import joblib
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ml.predictor import MLPredictor


class TestMLPredictor(unittest.TestCase):
    """Тесты для класса MLPredictor"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.config = {
            'ml': {
                'model_type': 'RandomForest',
                'n_estimators': 50,
                'max_depth': 10,
                'min_samples_split': 10,
                'random_state': 42,
                'test_size': 0.2
            }
        }
        self.predictor = MLPredictor(self.config)
        self.feature_columns = [
            'open', 'high', 'low', 'close', 'volume',
            'sma_20', 'sma_50', 'ema_12', 'ema_26',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_upper', 'bb_middle', 'bb_lower', 'atr'
        ]
    
    def _create_sample_data(self, n_samples=200):
        """Создание тестовых данных"""
        np.random.seed(42)
        data = {col: np.random.randn(n_samples) for col in self.feature_columns}
        data['target'] = np.random.choice([-1, 0, 1], n_samples)
        return pd.DataFrame(data)
    
    def test_initialization(self):
        """Тест инициализации класса"""
        self.assertIsNone(self.predictor.model)
        self.assertIsNone(self.predictor.scaler)
        self.assertEqual(self.predictor.feature_columns, [])
    
    def test_train_with_valid_data(self):
        """Тест обучения модели с валидными данными"""
        df = self._create_sample_data(n_samples=300)
        
        result = self.predictor.train(df, self.feature_columns)
        
        self.assertTrue(result)
        self.assertIsNotNone(self.predictor.model)
        self.assertIsNotNone(self.predictor.scaler)
        self.assertEqual(len(self.predictor.feature_columns), len(self.feature_columns))
    
    def test_train_with_insufficient_data(self):
        """Тест обучения с недостаточным количеством данных"""
        df = self._create_sample_data(n_samples=50)  # Мало данных
        
        result = self.predictor.train(df, self.feature_columns)
        
        self.assertFalse(result)
        self.assertIsNone(self.predictor.model)
    
    def test_train_with_missing_features(self):
        """Тест обучения с отсутствующими фичами"""
        df = self._create_sample_data(n_samples=300)
        df = df.drop(columns=['sma_20', 'rsi'])  # Удаляем некоторые фичи
        
        result = self.predictor.train(df, self.feature_columns)
        
        self.assertFalse(result)
    
    def test_predict_single_without_training(self):
        """Тест предсказания без обученной модели"""
        data = {col: [0.5] for col in self.feature_columns}
        df = pd.DataFrame(data)
        
        signal, proba = self.predictor.predict_single(df)
        
        self.assertEqual(signal, 0)
        self.assertEqual(proba, 0.33)
    
    def test_predict_single_after_training(self):
        """Тест предсказания после обучения модели"""
        # Обучаем модель
        df_train = self._create_sample_data(n_samples=300)
        self.predictor.train(df_train, self.feature_columns)
        
        # Делаем предсказание
        data = {col: [np.random.randn()] for col in self.feature_columns}
        df_test = pd.DataFrame(data)
        
        signal, proba = self.predictor.predict_single(df_test)
        
        self.assertIn(signal, [-1, 0, 1])
        self.assertTrue(0 <= proba <= 1)
    
    def test_save_and_load_model(self):
        """Тест сохранения и загрузки модели"""
        # Обучаем модель
        df = self._create_sample_data(n_samples=300)
        self.predictor.train(df, self.feature_columns)
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
            model_path = tmp.name
        
        try:
            self.predictor.save_model(model_path)
            
            # Создаём новый предиктор и загружаем модель
            new_predictor = MLPredictor(self.config)
            result = new_predictor.load_model(model_path)
            
            self.assertTrue(result)
            self.assertIsNotNone(new_predictor.model)
            self.assertIsNotNone(new_predictor.scaler)
            self.assertEqual(new_predictor.feature_columns, self.feature_columns)
            
            # Проверяем, что предсказания одинаковые
            data = {col: [np.random.randn()] for col in self.feature_columns}
            df_test = pd.DataFrame(data)
            
            signal1, proba1 = self.predictor.predict_single(df_test)
            signal2, proba2 = new_predictor.predict_single(df_test)
            
            self.assertEqual(signal1, signal2)
            self.assertAlmostEqual(proba1, proba2, places=5)
        finally:
            if os.path.exists(model_path):
                os.remove(model_path)
    
    def test_load_nonexistent_model(self):
        """Тест загрузки несуществующей модели"""
        result = self.predictor.load_model('nonexistent_model.pkl')
        
        self.assertFalse(result)
        self.assertIsNone(self.predictor.model)
    
    def test_feature_importance_after_training(self):
        """Тест получения важности фич после обучения"""
        df = self._create_sample_data(n_samples=300)
        self.predictor.train(df, self.feature_columns)
        
        # RandomForest должен иметь feature_importances_
        self.assertTrue(hasattr(self.predictor.model, 'feature_importances_'))
        importances = self.predictor.model.feature_importances_
        
        self.assertEqual(len(importances), len(self.feature_columns))
        self.assertTrue(np.all(importances >= 0))
        self.assertAlmostEqual(np.sum(importances), 1.0, places=5)
    
    def test_prediction_probabilities(self):
        """Тест корректности вероятностей предсказаний"""
        df = self._create_sample_data(n_samples=300)
        self.predictor.train(df, self.feature_columns)
        
        # Делаем несколько предсказаний
        for _ in range(10):
            data = {col: [np.random.randn()] for col in self.feature_columns}
            df_test = pd.DataFrame(data)
            
            signal, proba = self.predictor.predict_single(df_test)
            
            # Вероятность должна быть валидной
            self.assertTrue(0 <= proba <= 1)
            self.assertIn(signal, [-1, 0, 1])
    
    def test_class_balance_handling(self):
        """Тест обработки несбалансированных классов"""
        # Создаём несбалансированные данные (90% класс 1, 10% другие)
        df = self._create_sample_data(n_samples=300)
        df['target'] = 1
        df.loc[:30, 'target'] = -1
        df.loc[31:60, 'target'] = 0
        
        result = self.predictor.train(df, self.feature_columns)
        
        # Модель должна обучиться даже на несбалансированных данных
        self.assertTrue(result)
        self.assertIsNotNone(self.predictor.model)


if __name__ == '__main__':
    unittest.main()
