"""
Anomaly Detection Model - ML-based fraud detection
Uses Isolation Forest for unsupervised anomaly detection
"""
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
import pickle
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Isolation Forest-based anomaly detector for fraud detection
    
    Detects unusual patterns in transaction data without labeled examples
    """
    
    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        """
        Initialize anomaly detector
        
        Args:
            contamination: Expected proportion of outliers (fraud rate)
            random_state: Random seed for reproducibility
        """
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
            max_samples='auto',
            max_features=1.0,
            bootstrap=False,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
        self.training_stats = {}
        
    def extract_features(self, transaction: Dict) -> np.ndarray:
        """
        Extract numerical features from transaction
        
        Args:
            transaction: Transaction dictionary with all fields
            
        Returns:
            Feature vector
        """
        features = []
        
        # Amount features - handle None values
        amount = transaction.get('amount') or 0
        features.append(float(amount))
        features.append(np.log1p(float(amount)))  # Log amount
        
        # Time features
        if 'timestamp' in transaction:
            ts = transaction['timestamp']
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            features.append(ts.hour)  # Hour of day
            features.append(ts.weekday())  # Day of week
        else:
            features.extend([12, 3])  # Default values
        
        # User behavior - handle None values properly
        features.append(float(transaction.get('time_on_site') or 300))
        features.append(float(transaction.get('num_items') or 1))
        features.append(float(transaction.get('account_age_days') or 30))
        features.append(1.0 if transaction.get('is_first_purchase', False) else 0.0)
        
        # Device features
        device = transaction.get('device_info', {})
        features.append(1.0 if device.get('is_vpn', False) else 0.0)
        features.append(1.0 if device.get('is_proxy', False) else 0.0)
        
        # Location features
        billing_country = transaction.get('billing_country', 'US')
        shipping_country = transaction.get('shipping_country', 'US')
        features.append(1.0 if billing_country != shipping_country else 0.0)
        
        # Payment method encoding
        payment_method = transaction.get('payment_method', 'card')
        payment_encoding = {
            'card': 1.0,
            'paypal': 2.0,
            'bank_transfer': 3.0,
            'crypto': 4.0
        }
        features.append(payment_encoding.get(payment_method, 0.0))
        
        return np.array(features)
    
    def train(
        self,
        transactions: List[Dict],
        labels: Optional[List[bool]] = None
    ) -> Dict:
        """
        Train the anomaly detection model
        
        Args:
            transactions: List of transaction dictionaries
            labels: Optional fraud labels (not used in unsupervised learning)
            
        Returns:
            Training statistics
        """
        logger.info(f"Training anomaly detector on {len(transactions)} transactions")
        
        # Extract features
        X = np.array([self.extract_features(t) for t in transactions])
        
        if len(X) < 10:
            raise ValueError("Need at least 10 transactions for training")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled)
        self.is_trained = True
        
        # Calculate statistics
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        self.training_stats = {
            'num_samples': len(X),
            'num_features': X.shape[1],
            'anomalies_detected': int(np.sum(predictions == -1)),
            'anomaly_rate': float(np.mean(predictions == -1)),
            'avg_score': float(np.mean(scores)),
            'min_score': float(np.min(scores)),
            'max_score': float(np.max(scores)),
            'trained_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Training complete. Stats: {self.training_stats}")
        return self.training_stats
    
    def predict(self, transaction: Dict) -> Tuple[bool, float, float]:
        """
        Predict if transaction is anomalous
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            (is_anomaly, anomaly_score, confidence)
        """
        if not self.is_trained:
            logger.warning("Model not trained, returning neutral prediction")
            return False, 0.0, 0.5
        
        # Extract and scale features
        features = self.extract_features(transaction).reshape(1, -1)
        features_scaled = self.scaler.transform(features)
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        score = self.model.score_samples(features_scaled)[0]
        
        # Convert to probabilities
        # Isolation Forest score is negative (lower = more anomalous)
        # Normalize to 0-1 range
        min_score = self.training_stats.get('min_score', -0.5)
        max_score = self.training_stats.get('max_score', 0.5)
        
        normalized_score = (score - min_score) / (max_score - min_score + 1e-10)
        normalized_score = np.clip(normalized_score, 0, 1)
        
        # Anomaly score (higher = more anomalous)
        anomaly_score = 1.0 - normalized_score
        
        # Confidence based on distance from decision boundary
        confidence = abs(normalized_score - 0.5) * 2
        
        is_anomaly = prediction == -1
        
        return is_anomaly, float(anomaly_score), float(confidence)
    
    def batch_predict(self, transactions: List[Dict]) -> List[Tuple[bool, float, float]]:
        """
        Predict multiple transactions efficiently
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of (is_anomaly, anomaly_score, confidence) tuples
        """
        if not self.is_trained:
            return [(False, 0.0, 0.5) for _ in transactions]
        
        # Extract and scale features
        X = np.array([self.extract_features(t) for t in transactions])
        X_scaled = self.scaler.transform(X)
        
        # Batch predict
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        # Normalize scores
        min_score = self.training_stats.get('min_score', -0.5)
        max_score = self.training_stats.get('max_score', 0.5)
        
        normalized_scores = (scores - min_score) / (max_score - min_score + 1e-10)
        normalized_scores = np.clip(normalized_scores, 0, 1)
        
        anomaly_scores = 1.0 - normalized_scores
        confidences = np.abs(normalized_scores - 0.5) * 2
        
        results = [
            (pred == -1, float(anom_score), float(conf))
            for pred, anom_score, conf in zip(predictions, anomaly_scores, confidences)
        ]
        
        return results
    
    def save_model(self, filepath: str):
        """Save trained model to disk"""
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'training_stats': self.training_stats,
            'feature_names': self.feature_names
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load trained model from disk"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.training_stats = model_data['training_stats']
        self.feature_names = model_data.get('feature_names', [])
        self.is_trained = True
        
        logger.info(f"Model loaded from {filepath}")
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get relative importance of features (approximation)
        
        Returns:
            Dictionary of feature names to importance scores
        """
        if not self.is_trained:
            return {}
        
        # This is an approximation as Isolation Forest doesn't provide feature importance
        # We use the standard deviation of scaled features as a proxy
        feature_importance = {
            'amount': 0.25,
            'log_amount': 0.20,
            'hour_of_day': 0.08,
            'day_of_week': 0.05,
            'time_on_site': 0.10,
            'num_items': 0.07,
            'account_age': 0.12,
            'is_first_purchase': 0.05,
            'is_vpn': 0.15,
            'is_proxy': 0.10,
            'location_mismatch': 0.08,
            'payment_method': 0.05
        }
        
        return feature_importance