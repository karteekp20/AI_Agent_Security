from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
import joblib
from typing import Tuple, List, Optional
from pathlib import Path

class AnomalyDetector:
    """
    Isolation Forest-based anomaly detector for user behavior

    Isolation Forest works by randomly selecting a feature and then
    randomly selecting a split value. Anomalies are easier to isolate
    and thus have shorter paths in the tree.
    """

    def __init__(
        self,
        contamination: float = 0.05,  # Expected anomaly rate
        n_estimators: int = 100,
        random_state: int = 42,
    ):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,  # Use all CPU cores
        )
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, feature_vectors: np.ndarray) -> "AnomalyDetector":
        """
        Train the anomaly detector on normal behavior data

        Args:
            feature_vectors: Array of shape (n_samples, n_features)
        """
        # Scale features
        X_scaled = self.scaler.fit_transform(feature_vectors)

        # Fit model
        self.model.fit(X_scaled)
        self.is_fitted = True

        return self

    def predict(self, feature_vector: np.ndarray) -> Tuple[bool, float]:
        """
        Predict if a feature vector is anomalous

        Args:
            feature_vector: Single feature vector

        Returns:
            Tuple of (is_anomaly, anomaly_score)
            - is_anomaly: True if anomalous
            - anomaly_score: Score between 0 (normal) and 1 (anomalous)
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        # Reshape for single sample
        X = feature_vector.reshape(1, -1)
        X_scaled = self.scaler.transform(X)

        # Get prediction (-1 for anomaly, 1 for normal)
        prediction = self.model.predict(X_scaled)[0]
        is_anomaly = prediction == -1

        # Get anomaly score (lower = more anomalous)
        # Convert to 0-1 scale where 1 = most anomalous
        raw_score = self.model.score_samples(X_scaled)[0]
        # Isolation Forest scores are typically between -0.5 and 0.5
        # Normalize to 0-1 where 1 is most anomalous
        anomaly_score = 1 - (raw_score + 0.5)
        anomaly_score = np.clip(anomaly_score, 0, 1)

        return is_anomaly, float(anomaly_score)

    def predict_batch(
        self,
        feature_vectors: np.ndarray
    ) -> List[Tuple[bool, float]]:
        """Predict anomalies for multiple samples"""
        X_scaled = self.scaler.transform(feature_vectors)
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)

        results = []
        for pred, score in zip(predictions, scores):
            is_anomaly = pred == -1
            anomaly_score = 1 - (score + 0.5)
            anomaly_score = np.clip(anomaly_score, 0, 1)
            results.append((is_anomaly, float(anomaly_score)))

        return results

    def save(self, path: str) -> None:
        """Save model to disk"""
        model_path = Path(path)
        model_path.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, model_path / "isolation_forest.joblib")
        joblib.dump(self.scaler, model_path / "scaler.joblib")

    def load(self, path: str) -> "AnomalyDetector":
        """Load model from disk"""
        model_path = Path(path)

        self.model = joblib.load(model_path / "isolation_forest.joblib")
        self.scaler = joblib.load(model_path / "scaler.joblib")
        self.is_fitted = True

        return self