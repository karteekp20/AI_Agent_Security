# Month 3-4: Backend Implementation Guide

**Objective:** Detailed backend implementation for advanced security features
**Timeline:** September-October 2025
**Target:** ~800 lines of implementation specifications

---

## Table of Contents

1. [Advanced Threat Detection](#1-advanced-threat-detection)
2. [Advanced Policy Engine](#2-advanced-policy-engine)
3. [Security Analytics](#3-security-analytics)
4. [Integration Platform](#4-integration-platform)
5. [Database Schema Changes](#5-database-schema-changes)
6. [API Endpoint Specifications](#6-api-endpoint-specifications)
7. [Service Layer Design](#7-service-layer-design)

---

## 1. Advanced Threat Detection

### 1.1 ML Anomaly Detection Service

#### Architecture

```
sentinel/
├── ml/
│   ├── __init__.py
│   ├── anomaly_detector.py      # Main detection service
│   ├── feature_engineering.py   # Feature extraction
│   ├── models/
│   │   ├── isolation_forest.py  # Isolation Forest model
│   │   └── autoencoder.py       # Autoencoder model
│   └── training/
│       ├── pipeline.py          # Training pipeline
│       └── scheduler.py         # Scheduled retraining
```

#### Feature Engineering

Extract features from audit logs for anomaly detection:

```python
# sentinel/ml/feature_engineering.py
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np

@dataclass
class UserFeatures:
    """Feature vector for user behavior analysis"""
    # Request patterns
    requests_per_hour: float
    requests_per_day: float
    avg_request_length: float
    max_request_length: float

    # Timing patterns
    hour_of_day: int  # 0-23
    day_of_week: int  # 0-6
    time_since_last_request: float  # seconds

    # Content patterns
    unique_token_ratio: float
    special_char_ratio: float
    numeric_ratio: float
    uppercase_ratio: float

    # Risk indicators
    pii_mention_count: int
    injection_keyword_count: int
    avg_risk_score: float

    # Session patterns
    session_duration: float
    requests_in_session: int
    unique_endpoints: int


class FeatureExtractor:
    """Extract features from audit logs for ML models"""

    # Keywords associated with injection attempts
    INJECTION_KEYWORDS = [
        "ignore", "forget", "override", "system", "admin",
        "sudo", "root", "password", "secret", "bypass"
    ]

    def extract_user_features(
        self,
        user_id: str,
        audit_logs: List[Dict[str, Any]],
        window_hours: int = 24
    ) -> UserFeatures:
        """
        Extract feature vector for a user from recent audit logs

        Args:
            user_id: User identifier
            audit_logs: Recent audit log entries
            window_hours: Time window for feature calculation
        """
        # Filter to user's logs within window
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        user_logs = [
            log for log in audit_logs
            if log.get("user_id") == user_id
            and datetime.fromisoformat(log.get("timestamp", "")) > cutoff
        ]

        if not user_logs:
            return self._empty_features()

        # Calculate request patterns
        requests_per_hour = len(user_logs) / window_hours
        requests_per_day = len(user_logs) / (window_hours / 24)

        # Input length statistics
        input_lengths = [
            len(log.get("user_input", ""))
            for log in user_logs
        ]
        avg_request_length = np.mean(input_lengths)
        max_request_length = np.max(input_lengths)

        # Timing patterns (from most recent request)
        latest = max(user_logs, key=lambda x: x.get("timestamp", ""))
        latest_time = datetime.fromisoformat(latest["timestamp"])
        hour_of_day = latest_time.hour
        day_of_week = latest_time.weekday()

        # Time since previous request
        if len(user_logs) > 1:
            sorted_logs = sorted(user_logs, key=lambda x: x.get("timestamp", ""))
            times = [datetime.fromisoformat(l["timestamp"]) for l in sorted_logs]
            time_diffs = [(times[i+1] - times[i]).total_seconds()
                          for i in range(len(times)-1)]
            time_since_last = np.mean(time_diffs)
        else:
            time_since_last = 0

        # Content analysis
        all_inputs = " ".join(log.get("user_input", "") for log in user_logs)
        tokens = all_inputs.split()
        unique_tokens = set(tokens)

        unique_token_ratio = len(unique_tokens) / max(len(tokens), 1)
        special_char_ratio = sum(1 for c in all_inputs if not c.isalnum()) / max(len(all_inputs), 1)
        numeric_ratio = sum(1 for c in all_inputs if c.isdigit()) / max(len(all_inputs), 1)
        uppercase_ratio = sum(1 for c in all_inputs if c.isupper()) / max(len(all_inputs), 1)

        # Risk indicators
        pii_count = sum(
            len(log.get("pii_entities", []) or [])
            for log in user_logs
        )
        injection_count = sum(
            1 for kw in self.INJECTION_KEYWORDS
            if kw.lower() in all_inputs.lower()
        )
        risk_scores = [
            log.get("risk_score", 0) or 0
            for log in user_logs
        ]
        avg_risk = np.mean(risk_scores) if risk_scores else 0

        # Session patterns (simplified - would use session_id in production)
        unique_sessions = len(set(log.get("session_id") for log in user_logs))

        return UserFeatures(
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day,
            avg_request_length=avg_request_length,
            max_request_length=max_request_length,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            time_since_last_request=time_since_last,
            unique_token_ratio=unique_token_ratio,
            special_char_ratio=special_char_ratio,
            numeric_ratio=numeric_ratio,
            uppercase_ratio=uppercase_ratio,
            pii_mention_count=pii_count,
            injection_keyword_count=injection_count,
            avg_risk_score=avg_risk,
            session_duration=window_hours * 3600,  # Simplified
            requests_in_session=len(user_logs),
            unique_endpoints=unique_sessions,
        )

    def _empty_features(self) -> UserFeatures:
        """Return empty feature vector for new users"""
        return UserFeatures(
            requests_per_hour=0, requests_per_day=0,
            avg_request_length=0, max_request_length=0,
            hour_of_day=12, day_of_week=0,
            time_since_last_request=0,
            unique_token_ratio=0, special_char_ratio=0,
            numeric_ratio=0, uppercase_ratio=0,
            pii_mention_count=0, injection_keyword_count=0,
            avg_risk_score=0, session_duration=0,
            requests_in_session=0, unique_endpoints=0,
        )

    def to_vector(self, features: UserFeatures) -> np.ndarray:
        """Convert UserFeatures to numpy array for ML models"""
        return np.array([
            features.requests_per_hour,
            features.requests_per_day,
            features.avg_request_length,
            features.max_request_length,
            features.hour_of_day / 24,  # Normalize
            features.day_of_week / 7,
            np.log1p(features.time_since_last_request),  # Log transform
            features.unique_token_ratio,
            features.special_char_ratio,
            features.numeric_ratio,
            features.uppercase_ratio,
            features.pii_mention_count,
            features.injection_keyword_count,
            features.avg_risk_score,
            np.log1p(features.session_duration),
            features.requests_in_session,
            features.unique_endpoints,
        ])
```

#### Isolation Forest Model

```python
# sentinel/ml/models/isolation_forest.py
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
```

#### Real-time Inference API

```python
# sentinel/ml/anomaly_detector.py
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

from .feature_engineering import FeatureExtractor
from .models.isolation_forest import AnomalyDetector
from ..storage.postgres_adapter import PostgreSQLAdapter

class AnomalyDetectionService:
    """
    Real-time anomaly detection service

    Integrates with the existing Sentinel pipeline to provide
    ML-based threat detection in addition to rule-based detection.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        db_adapter: Optional[PostgreSQLAdapter] = None,
        anomaly_threshold: float = 0.7,
    ):
        self.feature_extractor = FeatureExtractor()
        self.anomaly_detector = AnomalyDetector()
        self.db_adapter = db_adapter
        self.anomaly_threshold = anomaly_threshold

        # Load pre-trained model if available
        if model_path:
            self.anomaly_detector.load(model_path)

    async def analyze_request(
        self,
        user_id: str,
        user_input: str,
        request_context: Dict[str, Any],
        org_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze a request for anomalous behavior

        Args:
            user_id: User identifier
            user_input: The input being analyzed
            request_context: Additional context (IP, session, etc.)
            org_id: Organization ID for tenant isolation

        Returns:
            Analysis result with anomaly score and explanation
        """
        # Fetch recent user history
        recent_logs = await self._get_user_history(user_id, org_id)

        # Extract features
        features = self.feature_extractor.extract_user_features(
            user_id=user_id,
            audit_logs=recent_logs,
            window_hours=24,
        )

        # Add current request features
        current_features = self._add_current_request_features(
            features, user_input, request_context
        )

        # Get anomaly prediction
        feature_vector = self.feature_extractor.to_vector(current_features)

        if not self.anomaly_detector.is_fitted:
            # Model not trained - return neutral score
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "status": "model_not_trained",
                "explanation": "Anomaly detection model not yet trained"
            }

        is_anomaly, anomaly_score = self.anomaly_detector.predict(feature_vector)

        # Generate explanation
        explanation = self._generate_explanation(
            features, current_features, anomaly_score
        )

        return {
            "is_anomaly": is_anomaly and anomaly_score >= self.anomaly_threshold,
            "anomaly_score": anomaly_score,
            "threshold": self.anomaly_threshold,
            "features": {
                "requests_per_hour": current_features.requests_per_hour,
                "avg_risk_score": current_features.avg_risk_score,
                "injection_keyword_count": current_features.injection_keyword_count,
            },
            "explanation": explanation,
        }

    async def _get_user_history(
        self,
        user_id: str,
        org_id: str
    ) -> list:
        """Fetch recent audit logs for user"""
        if not self.db_adapter:
            return []

        from datetime import timedelta
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)

        return self.db_adapter.get_audit_logs(
            start_time=start_time,
            end_time=end_time,
            org_id=org_id,
            user_id=user_id,
            limit=1000,
        )

    def _add_current_request_features(
        self,
        baseline_features,
        user_input: str,
        context: Dict[str, Any],
    ):
        """Add features from current request to baseline"""
        # This would update features based on current request
        # For now, return baseline (real implementation would modify)
        return baseline_features

    def _generate_explanation(
        self,
        baseline,
        current,
        score: float,
    ) -> str:
        """Generate human-readable explanation of anomaly"""
        if score < 0.3:
            return "Behavior appears normal"
        elif score < 0.5:
            return "Slightly unusual activity detected"
        elif score < 0.7:
            return "Moderately anomalous behavior - elevated request rate or unusual patterns"
        else:
            return "Highly anomalous behavior - significant deviation from baseline"
```

### 1.2 Behavioral Analysis Engine

```python
# sentinel/ml/behavioral_analysis.py
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np

@dataclass
class UserBaseline:
    """Baseline behavior profile for a user"""
    user_id: str
    org_id: str

    # Activity patterns
    typical_hours: List[int]  # Active hours (0-23)
    typical_days: List[int]   # Active days (0-6)
    avg_requests_per_session: float
    avg_session_duration_minutes: float

    # Content patterns
    avg_input_length: float
    vocabulary_fingerprint: Dict[str, float]  # Top words and frequencies

    # Risk patterns
    historical_risk_avg: float
    historical_risk_std: float

    # Metadata
    sample_count: int
    last_updated: datetime


class BehavioralAnalyzer:
    """
    Analyzes user behavior over time to detect deviations

    Creates and maintains baseline profiles for users, then
    compares current behavior to detect anomalies.
    """

    def __init__(self, baseline_window_days: int = 30):
        self.baseline_window_days = baseline_window_days
        self._baselines: Dict[str, UserBaseline] = {}

    def update_baseline(
        self,
        user_id: str,
        org_id: str,
        audit_logs: List[Dict[str, Any]],
    ) -> UserBaseline:
        """
        Update or create baseline for a user

        Args:
            user_id: User identifier
            org_id: Organization ID
            audit_logs: Recent audit logs for user
        """
        if not audit_logs:
            return self._empty_baseline(user_id, org_id)

        # Extract activity hours
        hours = [
            datetime.fromisoformat(log["timestamp"]).hour
            for log in audit_logs
            if log.get("timestamp")
        ]
        typical_hours = list(set(hours)) if hours else list(range(9, 18))

        # Extract activity days
        days = [
            datetime.fromisoformat(log["timestamp"]).weekday()
            for log in audit_logs
            if log.get("timestamp")
        ]
        typical_days = list(set(days)) if days else list(range(5))

        # Calculate session metrics
        session_ids = set(log.get("session_id") for log in audit_logs if log.get("session_id"))
        avg_requests_per_session = len(audit_logs) / max(len(session_ids), 1)

        # Calculate input length stats
        input_lengths = [len(log.get("user_input", "")) for log in audit_logs]
        avg_input_length = np.mean(input_lengths) if input_lengths else 0

        # Build vocabulary fingerprint (top 50 words)
        all_words = []
        for log in audit_logs:
            words = log.get("user_input", "").lower().split()
            all_words.extend(words)

        word_counts = {}
        for word in all_words:
            word_counts[word] = word_counts.get(word, 0) + 1

        total_words = len(all_words) or 1
        vocabulary_fingerprint = {
            word: count / total_words
            for word, count in sorted(
                word_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:50]
        }

        # Calculate risk statistics
        risk_scores = [
            log.get("risk_score", 0) or 0
            for log in audit_logs
        ]
        historical_risk_avg = np.mean(risk_scores) if risk_scores else 0
        historical_risk_std = np.std(risk_scores) if len(risk_scores) > 1 else 0.1

        baseline = UserBaseline(
            user_id=user_id,
            org_id=org_id,
            typical_hours=typical_hours,
            typical_days=typical_days,
            avg_requests_per_session=avg_requests_per_session,
            avg_session_duration_minutes=30,  # Would calculate from session data
            avg_input_length=avg_input_length,
            vocabulary_fingerprint=vocabulary_fingerprint,
            historical_risk_avg=historical_risk_avg,
            historical_risk_std=historical_risk_std,
            sample_count=len(audit_logs),
            last_updated=datetime.utcnow(),
        )

        self._baselines[f"{org_id}:{user_id}"] = baseline
        return baseline

    def analyze_deviation(
        self,
        user_id: str,
        org_id: str,
        current_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze how much current request deviates from baseline

        Returns deviation scores for different behavioral dimensions
        """
        baseline_key = f"{org_id}:{user_id}"
        baseline = self._baselines.get(baseline_key)

        if not baseline:
            return {
                "has_baseline": False,
                "overall_deviation": 0.0,
                "message": "No baseline established for user",
            }

        deviations = {}

        # Time deviation
        current_hour = datetime.utcnow().hour
        if current_hour not in baseline.typical_hours:
            deviations["time_deviation"] = 0.8
        else:
            deviations["time_deviation"] = 0.0

        # Day deviation
        current_day = datetime.utcnow().weekday()
        if current_day not in baseline.typical_days:
            deviations["day_deviation"] = 0.6
        else:
            deviations["day_deviation"] = 0.0

        # Input length deviation
        current_length = len(current_request.get("user_input", ""))
        length_deviation = abs(current_length - baseline.avg_input_length) / max(baseline.avg_input_length, 1)
        deviations["length_deviation"] = min(length_deviation, 1.0)

        # Vocabulary deviation (check for unusual words)
        current_words = set(current_request.get("user_input", "").lower().split())
        known_words = set(baseline.vocabulary_fingerprint.keys())
        new_word_ratio = len(current_words - known_words) / max(len(current_words), 1)
        deviations["vocabulary_deviation"] = new_word_ratio

        # Risk score deviation
        current_risk = current_request.get("risk_score", 0) or 0
        if baseline.historical_risk_std > 0:
            z_score = (current_risk - baseline.historical_risk_avg) / baseline.historical_risk_std
            risk_deviation = min(abs(z_score) / 3, 1.0)  # Normalize to 0-1
        else:
            risk_deviation = 0.0
        deviations["risk_deviation"] = risk_deviation

        # Calculate overall deviation (weighted average)
        weights = {
            "time_deviation": 0.15,
            "day_deviation": 0.10,
            "length_deviation": 0.20,
            "vocabulary_deviation": 0.25,
            "risk_deviation": 0.30,
        }

        overall = sum(
            deviations[k] * weights[k]
            for k in weights
        )

        return {
            "has_baseline": True,
            "baseline_sample_count": baseline.sample_count,
            "deviations": deviations,
            "overall_deviation": overall,
            "is_significant": overall > 0.5,
            "message": self._deviation_message(overall),
        }

    def _empty_baseline(self, user_id: str, org_id: str) -> UserBaseline:
        """Create empty baseline for new users"""
        return UserBaseline(
            user_id=user_id,
            org_id=org_id,
            typical_hours=list(range(9, 18)),
            typical_days=list(range(5)),
            avg_requests_per_session=10,
            avg_session_duration_minutes=30,
            avg_input_length=100,
            vocabulary_fingerprint={},
            historical_risk_avg=0.2,
            historical_risk_std=0.1,
            sample_count=0,
            last_updated=datetime.utcnow(),
        )

    def _deviation_message(self, score: float) -> str:
        """Generate message based on deviation score"""
        if score < 0.2:
            return "Behavior consistent with historical patterns"
        elif score < 0.4:
            return "Minor deviation from typical behavior"
        elif score < 0.6:
            return "Moderate behavioral deviation detected"
        elif score < 0.8:
            return "Significant behavioral anomaly"
        else:
            return "Extreme deviation - potential account compromise"
```

### 1.3 Threat Intelligence Integration

Extending the existing `sentinel/meta_learning/threat_intelligence.py`:

```python
# sentinel/meta_learning/feed_connectors.py
from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
from datetime import datetime

from .schemas import ThreatIndicator, ThreatSeverity, ThreatFeed


class BaseFeedConnector(ABC):
    """Abstract base class for threat feed connectors"""

    @abstractmethod
    async def fetch_indicators(self, since: Optional[datetime] = None) -> List[ThreatIndicator]:
        """Fetch threat indicators from the feed"""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate feed configuration"""
        pass


class AlienVaultOTXConnector(BaseFeedConnector):
    """
    AlienVault OTX (Open Threat Exchange) connector

    Documentation: https://otx.alienvault.com/api
    """

    BASE_URL = "https://otx.alienvault.com/api/v1"

    def __init__(self, api_key: str, pulse_days: int = 7):
        self.api_key = api_key
        self.pulse_days = pulse_days
        self.headers = {"X-OTX-API-KEY": api_key}

    def validate_config(self) -> bool:
        return bool(self.api_key)

    async def fetch_indicators(
        self,
        since: Optional[datetime] = None
    ) -> List[ThreatIndicator]:
        """Fetch indicators from subscribed pulses"""
        indicators = []

        async with httpx.AsyncClient() as client:
            # Get subscribed pulses
            response = await client.get(
                f"{self.BASE_URL}/pulses/subscribed",
                headers=self.headers,
                params={"modified_since": since.isoformat() if since else None},
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()

            for pulse in data.get("results", []):
                for indicator_data in pulse.get("indicators", []):
                    indicator = self._parse_indicator(indicator_data, pulse)
                    if indicator:
                        indicators.append(indicator)

        return indicators

    def _parse_indicator(
        self,
        data: dict,
        pulse: dict
    ) -> Optional[ThreatIndicator]:
        """Parse OTX indicator format"""
        indicator_type_map = {
            "domain": "domain",
            "hostname": "domain",
            "IPv4": "ip",
            "IPv6": "ip",
            "URL": "url",
            "FileHash-MD5": "hash",
            "FileHash-SHA256": "hash",
        }

        otx_type = data.get("type", "")
        mapped_type = indicator_type_map.get(otx_type, "pattern")

        # Map pulse TLP to severity
        tlp = pulse.get("TLP", "white")
        severity_map = {
            "white": ThreatSeverity.LOW,
            "green": ThreatSeverity.MEDIUM,
            "amber": ThreatSeverity.HIGH,
            "red": ThreatSeverity.CRITICAL,
        }

        return ThreatIndicator(
            indicator_id=f"otx_{data.get('id', '')}",
            indicator_type=mapped_type,
            indicator_value=data.get("indicator", ""),
            severity=severity_map.get(tlp, ThreatSeverity.MEDIUM),
            confidence=0.85,  # OTX community-validated
            source_feed="AlienVault OTX",
            first_seen=datetime.fromisoformat(
                data.get("created", datetime.utcnow().isoformat())
            ),
            last_seen=datetime.utcnow(),
            description=pulse.get("description", ""),
            tags=pulse.get("tags", []),
            references=[pulse.get("id", "")],
        )


class MISPConnector(BaseFeedConnector):
    """
    MISP (Malware Information Sharing Platform) connector

    Documentation: https://www.misp-project.org/documentation/
    """

    def __init__(self, url: str, api_key: str, verify_ssl: bool = True):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.headers = {
            "Authorization": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def validate_config(self) -> bool:
        return bool(self.url and self.api_key)

    async def fetch_indicators(
        self,
        since: Optional[datetime] = None
    ) -> List[ThreatIndicator]:
        """Fetch indicators from MISP events"""
        indicators = []

        # Build search query
        search_body = {
            "returnFormat": "json",
            "enforceWarninglist": True,
            "includeDecayScore": True,
        }

        if since:
            search_body["timestamp"] = int(since.timestamp())

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.post(
                f"{self.url}/attributes/restSearch",
                headers=self.headers,
                json=search_body,
                timeout=60.0,
            )
            response.raise_for_status()

            data = response.json()

            for attr in data.get("response", {}).get("Attribute", []):
                indicator = self._parse_attribute(attr)
                if indicator:
                    indicators.append(indicator)

        return indicators

    def _parse_attribute(self, attr: dict) -> Optional[ThreatIndicator]:
        """Parse MISP attribute to ThreatIndicator"""
        # MISP type mapping
        type_map = {
            "ip-src": "ip",
            "ip-dst": "ip",
            "domain": "domain",
            "hostname": "domain",
            "url": "url",
            "md5": "hash",
            "sha256": "hash",
            "pattern-in-traffic": "pattern",
            "yara": "signature",
        }

        misp_type = attr.get("type", "")
        mapped_type = type_map.get(misp_type, "pattern")

        # Calculate confidence from decay score
        decay_score = attr.get("decay_score", {})
        confidence = decay_score.get("score", 80) / 100

        return ThreatIndicator(
            indicator_id=f"misp_{attr.get('uuid', '')}",
            indicator_type=mapped_type,
            indicator_value=attr.get("value", ""),
            severity=self._map_threat_level(attr.get("event", {}).get("threat_level_id")),
            confidence=confidence,
            source_feed="MISP",
            first_seen=datetime.fromtimestamp(int(attr.get("timestamp", 0))),
            last_seen=datetime.utcnow(),
            description=attr.get("comment", ""),
            tags=[tag.get("name", "") for tag in attr.get("Tag", [])],
            references=[attr.get("event_id", "")],
        )

    def _map_threat_level(self, level: Optional[str]) -> ThreatSeverity:
        """Map MISP threat level to severity"""
        levels = {
            "1": ThreatSeverity.CRITICAL,  # High
            "2": ThreatSeverity.HIGH,       # Medium
            "3": ThreatSeverity.MEDIUM,     # Low
            "4": ThreatSeverity.LOW,        # Undefined
        }
        return levels.get(level or "4", ThreatSeverity.MEDIUM)


class AbuseCHConnector(BaseFeedConnector):
    """
    abuse.ch threat feeds connector

    Supports: URLhaus, Feodo Tracker, SSL Blacklist
    """

    FEEDS = {
        "urlhaus": "https://urlhaus.abuse.ch/downloads/json_recent/",
        "feodo": "https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.json",
        "sslbl": "https://sslbl.abuse.ch/blacklist/sslipblacklist.json",
    }

    def __init__(self, enabled_feeds: List[str] = None):
        self.enabled_feeds = enabled_feeds or ["urlhaus", "feodo"]

    def validate_config(self) -> bool:
        return len(self.enabled_feeds) > 0

    async def fetch_indicators(
        self,
        since: Optional[datetime] = None
    ) -> List[ThreatIndicator]:
        """Fetch indicators from enabled abuse.ch feeds"""
        indicators = []

        async with httpx.AsyncClient() as client:
            for feed_name in self.enabled_feeds:
                if feed_name not in self.FEEDS:
                    continue

                try:
                    response = await client.get(
                        self.FEEDS[feed_name],
                        timeout=30.0,
                    )
                    response.raise_for_status()

                    data = response.json()
                    feed_indicators = self._parse_feed(feed_name, data)
                    indicators.extend(feed_indicators)

                except Exception as e:
                    print(f"Error fetching {feed_name}: {e}")

        return indicators

    def _parse_feed(self, feed_name: str, data: dict) -> List[ThreatIndicator]:
        """Parse abuse.ch feed data"""
        indicators = []

        if feed_name == "urlhaus":
            for entry in data.get("urls", [])[:1000]:  # Limit
                indicators.append(ThreatIndicator(
                    indicator_id=f"urlhaus_{entry.get('id', '')}",
                    indicator_type="url",
                    indicator_value=entry.get("url", ""),
                    severity=ThreatSeverity.HIGH,
                    confidence=0.9,
                    source_feed="URLhaus",
                    first_seen=datetime.fromisoformat(
                        entry.get("date_added", datetime.utcnow().isoformat())
                    ),
                    last_seen=datetime.utcnow(),
                    description=f"Malware: {entry.get('threat', 'unknown')}",
                    tags=entry.get("tags", []),
                    references=[entry.get("urlhaus_reference", "")],
                ))

        elif feed_name == "feodo":
            for entry in data.get("ipblocklist", []):
                indicators.append(ThreatIndicator(
                    indicator_id=f"feodo_{entry.get('ip_address', '')}",
                    indicator_type="ip",
                    indicator_value=entry.get("ip_address", ""),
                    severity=ThreatSeverity.CRITICAL,
                    confidence=0.95,
                    source_feed="Feodo Tracker",
                    first_seen=datetime.fromisoformat(
                        entry.get("first_seen", datetime.utcnow().isoformat())
                    ),
                    last_seen=datetime.utcnow(),
                    description=f"Botnet C2: {entry.get('malware', 'unknown')}",
                    tags=[entry.get("malware", "")],
                    references=[],
                ))

        return indicators
```

---

## 2. Advanced Policy Engine

### 2.1 Policy Version Control System

```python
# sentinel/saas/services/policy_versioning.py
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID, uuid4
import difflib
import json

from sqlalchemy.orm import Session
from ..models.policy import Policy


class PolicyVersionControl:
    """
    Git-like version control for security policies

    Features:
    - Version history with parent tracking
    - Diff between versions
    - Branching for A/B tests
    - Rollback capability
    """

    def __init__(self, db: Session):
        self.db = db

    def create_version(
        self,
        policy_id: UUID,
        changes: Dict[str, Any],
        commit_message: str,
        author_id: UUID,
    ) -> Policy:
        """
        Create a new version of a policy

        Args:
            policy_id: ID of policy to version
            changes: Dictionary of field changes
            commit_message: Description of changes
            author_id: User making the change
        """
        # Get current policy
        current = self.db.query(Policy).filter(
            Policy.policy_id == policy_id
        ).first()

        if not current:
            raise ValueError(f"Policy {policy_id} not found")

        # Create new version
        new_version = Policy(
            policy_id=uuid4(),
            org_id=current.org_id,
            workspace_id=current.workspace_id,
            policy_name=changes.get("policy_name", current.policy_name),
            policy_type=changes.get("policy_type", current.policy_type),
            description=changes.get("description", current.description),
            policy_config=changes.get("policy_config", current.policy_config),
            version=current.version + 1,
            parent_policy_id=current.policy_id,  # Link to previous version
            status="draft",
            created_by=author_id,
        )

        # Store commit message in config
        if "metadata" not in new_version.policy_config:
            new_version.policy_config["metadata"] = {}
        new_version.policy_config["metadata"]["commit_message"] = commit_message

        self.db.add(new_version)
        self.db.commit()
        self.db.refresh(new_version)

        return new_version

    def get_version_history(
        self,
        policy_id: UUID,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a policy chain

        Traverses parent_policy_id links to build history
        """
        history = []
        current_id = policy_id

        while current_id and len(history) < limit:
            policy = self.db.query(Policy).filter(
                Policy.policy_id == current_id
            ).first()

            if not policy:
                break

            history.append({
                "policy_id": str(policy.policy_id),
                "version": policy.version,
                "status": policy.status,
                "created_at": policy.created_at.isoformat(),
                "created_by": str(policy.created_by) if policy.created_by else None,
                "commit_message": (
                    policy.policy_config.get("metadata", {}).get("commit_message", "")
                ),
            })

            current_id = policy.parent_policy_id

        return history

    def diff_versions(
        self,
        version_a_id: UUID,
        version_b_id: UUID,
    ) -> Dict[str, Any]:
        """
        Generate diff between two policy versions

        Returns structured diff showing what changed
        """
        policy_a = self.db.query(Policy).filter(
            Policy.policy_id == version_a_id
        ).first()
        policy_b = self.db.query(Policy).filter(
            Policy.policy_id == version_b_id
        ).first()

        if not policy_a or not policy_b:
            raise ValueError("One or both policy versions not found")

        diffs = {
            "version_a": policy_a.version,
            "version_b": policy_b.version,
            "changes": [],
        }

        # Compare basic fields
        fields_to_compare = ["policy_name", "policy_type", "description", "status"]
        for field in fields_to_compare:
            val_a = getattr(policy_a, field)
            val_b = getattr(policy_b, field)
            if val_a != val_b:
                diffs["changes"].append({
                    "field": field,
                    "old": val_a,
                    "new": val_b,
                })

        # Compare policy_config (JSON diff)
        config_a = json.dumps(policy_a.policy_config, indent=2, sort_keys=True)
        config_b = json.dumps(policy_b.policy_config, indent=2, sort_keys=True)

        if config_a != config_b:
            diff_lines = list(difflib.unified_diff(
                config_a.splitlines(),
                config_b.splitlines(),
                fromfile=f"v{policy_a.version}",
                tofile=f"v{policy_b.version}",
                lineterm="",
            ))
            diffs["config_diff"] = "\n".join(diff_lines)

        return diffs

    def rollback_to_version(
        self,
        policy_id: UUID,
        target_version: int,
        author_id: UUID,
    ) -> Policy:
        """
        Rollback a policy to a previous version

        Creates a new version that copies the target version's config
        """
        # Find target version in history
        current = self.db.query(Policy).filter(
            Policy.policy_id == policy_id
        ).first()

        if not current:
            raise ValueError(f"Policy {policy_id} not found")

        # Traverse history to find target
        target = None
        current_id = policy_id

        while current_id:
            policy = self.db.query(Policy).filter(
                Policy.policy_id == current_id
            ).first()

            if not policy:
                break

            if policy.version == target_version:
                target = policy
                break

            current_id = policy.parent_policy_id

        if not target:
            raise ValueError(f"Version {target_version} not found in history")

        # Create rollback version
        return self.create_version(
            policy_id=policy_id,
            changes={
                "policy_config": target.policy_config,
            },
            commit_message=f"Rollback to version {target_version}",
            author_id=author_id,
        )
```

### 2.2 A/B Testing Framework

```python
# sentinel/saas/services/ab_testing.py
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID
import random
import hashlib

from sqlalchemy.orm import Session
from ..models.policy import Policy


@dataclass
class ABTestConfig:
    """Configuration for an A/B test"""
    test_id: str
    control_policy_id: UUID
    variant_policy_id: UUID
    traffic_percentage: int  # Percentage sent to variant (0-100)
    start_time: datetime
    end_time: Optional[datetime]
    targeting_rules: Dict[str, Any]  # Optional targeting


@dataclass
class ABTestMetrics:
    """Metrics for an A/B test variant"""
    policy_id: UUID
    total_evaluations: int
    blocked_count: int
    false_positive_reports: int
    avg_latency_ms: float
    detection_rate: float


class ABTestingService:
    """
    A/B testing framework for policy evaluation

    Allows controlled rollout of new policies by splitting
    traffic between control and variant groups.
    """

    def __init__(self, db: Session):
        self.db = db
        self._active_tests: Dict[str, ABTestConfig] = {}

    def create_test(
        self,
        org_id: UUID,
        control_policy_id: UUID,
        variant_policy_id: UUID,
        traffic_percentage: int = 10,
        duration_days: int = 7,
        targeting_rules: Optional[Dict[str, Any]] = None,
    ) -> ABTestConfig:
        """
        Create a new A/B test

        Args:
            org_id: Organization running the test
            control_policy_id: Current/baseline policy
            variant_policy_id: New policy to test
            traffic_percentage: % of traffic to variant (default 10%)
            duration_days: Test duration (default 7 days)
            targeting_rules: Optional rules to target specific users/requests
        """
        # Validate policies exist and belong to org
        control = self.db.query(Policy).filter(
            Policy.policy_id == control_policy_id,
            Policy.org_id == org_id,
        ).first()

        variant = self.db.query(Policy).filter(
            Policy.policy_id == variant_policy_id,
            Policy.org_id == org_id,
        ).first()

        if not control or not variant:
            raise ValueError("Policies not found or don't belong to organization")

        # Update variant policy with test config
        variant.test_mode = True
        variant.test_percentage = traffic_percentage
        variant.status = "testing"

        test_config = ABTestConfig(
            test_id=f"ab_{control_policy_id}_{variant_policy_id}",
            control_policy_id=control_policy_id,
            variant_policy_id=variant_policy_id,
            traffic_percentage=traffic_percentage,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(days=duration_days),
            targeting_rules=targeting_rules or {},
        )

        # Store test config in variant's ab_test_config
        variant.ab_test_config = {
            "test_id": test_config.test_id,
            "control_policy_id": str(control_policy_id),
            "traffic_percentage": traffic_percentage,
            "start_time": test_config.start_time.isoformat(),
            "end_time": test_config.end_time.isoformat() if test_config.end_time else None,
            "targeting_rules": targeting_rules or {},
        }

        self.db.commit()

        self._active_tests[test_config.test_id] = test_config

        return test_config

    def select_policy(
        self,
        org_id: UUID,
        user_id: str,
        request_context: Dict[str, Any],
    ) -> Tuple[UUID, str]:
        """
        Select which policy to use for a request

        Uses consistent hashing to ensure same user always
        sees same variant during a test.

        Returns:
            Tuple of (policy_id, group) where group is 'control' or 'variant'
        """
        # Get active tests for org
        active_tests = [
            test for test in self._active_tests.values()
            if self._test_is_active(test)
        ]

        if not active_tests:
            # No active tests - return default policy
            return self._get_default_policy(org_id), "default"

        # Use first applicable test
        for test in active_tests:
            if self._request_matches_targeting(test, user_id, request_context):
                # Consistent hashing based on user_id + test_id
                hash_input = f"{user_id}:{test.test_id}"
                hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
                bucket = hash_value % 100

                if bucket < test.traffic_percentage:
                    return test.variant_policy_id, "variant"
                else:
                    return test.control_policy_id, "control"

        return self._get_default_policy(org_id), "default"

    def record_evaluation(
        self,
        test_id: str,
        policy_id: UUID,
        group: str,
        result: Dict[str, Any],
    ) -> None:
        """
        Record a policy evaluation result for test analysis

        Args:
            test_id: A/B test identifier
            policy_id: Policy that was evaluated
            group: 'control' or 'variant'
            result: Evaluation result (blocked, latency, etc.)
        """
        # Would store in metrics table for analysis
        # This is a simplified placeholder
        pass

    def get_test_results(
        self,
        test_id: str,
    ) -> Dict[str, ABTestMetrics]:
        """
        Get current results for an A/B test

        Returns metrics for both control and variant groups
        """
        test = self._active_tests.get(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")

        # Would query metrics from database
        # Placeholder with sample structure
        return {
            "control": ABTestMetrics(
                policy_id=test.control_policy_id,
                total_evaluations=10000,
                blocked_count=500,
                false_positive_reports=25,
                avg_latency_ms=15.5,
                detection_rate=0.05,
            ),
            "variant": ABTestMetrics(
                policy_id=test.variant_policy_id,
                total_evaluations=1000,
                blocked_count=60,
                false_positive_reports=2,
                avg_latency_ms=18.2,
                detection_rate=0.06,
            ),
        }

    def conclude_test(
        self,
        test_id: str,
        winner: str,  # 'control' or 'variant'
    ) -> None:
        """
        Conclude an A/B test and optionally promote variant

        Args:
            test_id: Test to conclude
            winner: Which variant won ('control' keeps status quo)
        """
        test = self._active_tests.get(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")

        variant = self.db.query(Policy).filter(
            Policy.policy_id == test.variant_policy_id
        ).first()

        if winner == "variant":
            # Promote variant to active
            variant.status = "active"
            variant.test_mode = False
            variant.test_percentage = 100
            variant.deployed_at = datetime.utcnow()

            # Archive control
            control = self.db.query(Policy).filter(
                Policy.policy_id == test.control_policy_id
            ).first()
            if control:
                control.status = "archived"
        else:
            # Archive variant
            variant.status = "archived"
            variant.test_mode = False

        self.db.commit()

        # Remove from active tests
        del self._active_tests[test_id]

    def _test_is_active(self, test: ABTestConfig) -> bool:
        """Check if test is currently active"""
        now = datetime.utcnow()
        if now < test.start_time:
            return False
        if test.end_time and now > test.end_time:
            return False
        return True

    def _request_matches_targeting(
        self,
        test: ABTestConfig,
        user_id: str,
        context: Dict[str, Any],
    ) -> bool:
        """Check if request matches test targeting rules"""
        rules = test.targeting_rules
        if not rules:
            return True  # No targeting = all requests

        # Example targeting: specific user segments
        if "user_ids" in rules and user_id not in rules["user_ids"]:
            return False

        if "workspaces" in rules:
            if context.get("workspace_id") not in rules["workspaces"]:
                return False

        return True

    def _get_default_policy(self, org_id: UUID) -> UUID:
        """Get default active policy for org"""
        policy = self.db.query(Policy).filter(
            Policy.org_id == org_id,
            Policy.status == "active",
        ).first()

        if policy:
            return policy.policy_id
        raise ValueError(f"No active policy for org {org_id}")
```

### 2.3 Custom DSL (Domain-Specific Language)

```python
# sentinel/policy/dsl/__init__.py
"""
Sentinel Policy DSL

A domain-specific language for defining security policies.

Example policy:
```
policy "Block PII in prompts" {
    when {
        input.contains_pii("ssn", "credit_card")
        or input.risk_score > 0.7
    }
    then {
        action: block
        reason: "PII detected in input"
        log_level: warning
    }
}
```
"""

# sentinel/policy/dsl/grammar.py
# Using PLY (Python Lex-Yacc) for parsing

import ply.lex as lex
import ply.yacc as yacc
from typing import Dict, Any, List
from dataclasses import dataclass


# ============================================================================
# LEXER
# ============================================================================

# Reserved words
reserved = {
    'policy': 'POLICY',
    'when': 'WHEN',
    'then': 'THEN',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
    'true': 'TRUE',
    'false': 'FALSE',
    'action': 'ACTION',
    'block': 'BLOCK',
    'allow': 'ALLOW',
    'log': 'LOG',
    'alert': 'ALERT',
    'reason': 'REASON',
    'input': 'INPUT',
    'output': 'OUTPUT',
    'context': 'CONTEXT',
    'user': 'USER',
}

# Token list
tokens = [
    'STRING',
    'NUMBER',
    'FLOAT',
    'IDENTIFIER',
    'LPAREN',
    'RPAREN',
    'LBRACE',
    'RBRACE',
    'COMMA',
    'COLON',
    'DOT',
    'GT',
    'LT',
    'GTE',
    'LTE',
    'EQ',
    'NEQ',
] + list(reserved.values())

# Token rules
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_COMMA = r','
t_COLON = r':'
t_DOT = r'\.'
t_GT = r'>'
t_LT = r'<'
t_GTE = r'>='
t_LTE = r'<='
t_EQ = r'=='
t_NEQ = r'!='

def t_FLOAT(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_STRING(t):
    r'"[^"]*"'
    t.value = t.value[1:-1]  # Remove quotes
    return t

def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value.lower(), 'IDENTIFIER')
    return t

t_ignore = ' \t'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_COMMENT(t):
    r'\#.*'
    pass  # Ignore comments

def t_error(t):
    raise SyntaxError(f"Illegal character '{t.value[0]}' at line {t.lineno}")


# ============================================================================
# AST NODES
# ============================================================================

@dataclass
class PolicyAST:
    """Root AST node for a policy"""
    name: str
    conditions: 'ConditionNode'
    actions: List['ActionNode']


@dataclass
class ConditionNode:
    """AST node for conditions"""
    type: str  # 'and', 'or', 'not', 'comparison', 'function_call'
    left: Any = None
    right: Any = None
    operator: str = None
    value: Any = None


@dataclass
class ActionNode:
    """AST node for actions"""
    action_type: str  # 'block', 'allow', 'log', 'alert'
    params: Dict[str, Any] = None


@dataclass
class FunctionCallNode:
    """AST node for function calls"""
    object: str  # 'input', 'output', 'context', 'user'
    method: str
    args: List[Any]


# ============================================================================
# PARSER
# ============================================================================

def p_policy(p):
    '''policy : POLICY STRING LBRACE when_clause then_clause RBRACE'''
    p[0] = PolicyAST(name=p[2], conditions=p[4], actions=p[5])

def p_when_clause(p):
    '''when_clause : WHEN LBRACE condition RBRACE'''
    p[0] = p[3]

def p_then_clause(p):
    '''then_clause : THEN LBRACE action_list RBRACE'''
    p[0] = p[3]

def p_condition_and(p):
    '''condition : condition AND condition'''
    p[0] = ConditionNode(type='and', left=p[1], right=p[3])

def p_condition_or(p):
    '''condition : condition OR condition'''
    p[0] = ConditionNode(type='or', left=p[1], right=p[3])

def p_condition_not(p):
    '''condition : NOT condition'''
    p[0] = ConditionNode(type='not', left=p[2])

def p_condition_comparison(p):
    '''condition : expression comparison_op expression'''
    p[0] = ConditionNode(
        type='comparison',
        left=p[1],
        operator=p[2],
        right=p[3]
    )

def p_condition_function(p):
    '''condition : function_call'''
    p[0] = ConditionNode(type='function_call', value=p[1])

def p_condition_paren(p):
    '''condition : LPAREN condition RPAREN'''
    p[0] = p[2]

def p_comparison_op(p):
    '''comparison_op : GT
                     | LT
                     | GTE
                     | LTE
                     | EQ
                     | NEQ'''
    p[0] = p[1]

def p_expression_property(p):
    '''expression : INPUT DOT IDENTIFIER
                  | OUTPUT DOT IDENTIFIER
                  | CONTEXT DOT IDENTIFIER
                  | USER DOT IDENTIFIER'''
    p[0] = FunctionCallNode(object=p[1], method=p[3], args=[])

def p_expression_number(p):
    '''expression : NUMBER
                  | FLOAT'''
    p[0] = p[1]

def p_expression_string(p):
    '''expression : STRING'''
    p[0] = p[1]

def p_expression_bool(p):
    '''expression : TRUE
                  | FALSE'''
    p[0] = p[1].lower() == 'true'

def p_function_call(p):
    '''function_call : INPUT DOT IDENTIFIER LPAREN arg_list RPAREN
                     | OUTPUT DOT IDENTIFIER LPAREN arg_list RPAREN
                     | CONTEXT DOT IDENTIFIER LPAREN arg_list RPAREN
                     | USER DOT IDENTIFIER LPAREN arg_list RPAREN'''
    p[0] = FunctionCallNode(object=p[1], method=p[3], args=p[5])

def p_arg_list(p):
    '''arg_list : arg_list COMMA expression
               | expression
               | empty'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif len(p) == 2 and p[1] is not None:
        p[0] = [p[1]]
    else:
        p[0] = []

def p_action_list(p):
    '''action_list : action_list action
                   | action'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_action(p):
    '''action : ACTION COLON action_type
              | REASON COLON STRING
              | IDENTIFIER COLON expression'''
    if p[1] == 'action':
        p[0] = ActionNode(action_type=p[3])
    elif p[1] == 'reason':
        p[0] = ActionNode(action_type='reason', params={'message': p[3]})
    else:
        p[0] = ActionNode(action_type='param', params={p[1]: p[3]})

def p_action_type(p):
    '''action_type : BLOCK
                   | ALLOW
                   | LOG
                   | ALERT'''
    p[0] = p[1]

def p_empty(p):
    '''empty :'''
    p[0] = None

def p_error(p):
    if p:
        raise SyntaxError(f"Syntax error at '{p.value}', line {p.lineno}")
    else:
        raise SyntaxError("Syntax error at end of input")


class DSLParser:
    """Parser for Sentinel Policy DSL"""

    def __init__(self):
        self.lexer = lex.lex()
        self.parser = yacc.yacc()

    def parse(self, source: str) -> PolicyAST:
        """Parse DSL source code into AST"""
        return self.parser.parse(source, lexer=self.lexer)

    def compile(self, source: str) -> Dict[str, Any]:
        """Compile DSL to JSON policy config"""
        ast = self.parse(source)
        return self._ast_to_config(ast)

    def _ast_to_config(self, ast: PolicyAST) -> Dict[str, Any]:
        """Convert AST to policy_config JSON"""
        return {
            "name": ast.name,
            "dsl_version": "1.0",
            "conditions": self._condition_to_json(ast.conditions),
            "actions": [self._action_to_json(a) for a in ast.actions],
        }

    def _condition_to_json(self, cond: ConditionNode) -> Dict[str, Any]:
        """Convert condition node to JSON"""
        if cond.type in ('and', 'or'):
            return {
                "type": cond.type,
                "conditions": [
                    self._condition_to_json(cond.left),
                    self._condition_to_json(cond.right),
                ]
            }
        elif cond.type == 'not':
            return {
                "type": "not",
                "condition": self._condition_to_json(cond.left),
            }
        elif cond.type == 'comparison':
            return {
                "type": "comparison",
                "left": self._value_to_json(cond.left),
                "operator": cond.operator,
                "right": self._value_to_json(cond.right),
            }
        elif cond.type == 'function_call':
            return {
                "type": "function",
                "object": cond.value.object,
                "method": cond.value.method,
                "args": cond.value.args,
            }
        return {}

    def _value_to_json(self, value: Any) -> Any:
        """Convert value to JSON-serializable form"""
        if isinstance(value, FunctionCallNode):
            return {
                "type": "property",
                "object": value.object,
                "property": value.method,
            }
        return value

    def _action_to_json(self, action: ActionNode) -> Dict[str, Any]:
        """Convert action node to JSON"""
        result = {"type": action.action_type}
        if action.params:
            result["params"] = action.params
        return result
```

### 2.4 Policy Templates

```python
# sentinel/saas/services/policy_templates.py
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.orm import Session


# Built-in templates
BUILTIN_TEMPLATES = [
    {
        "template_id": "tpl_pii_basic",
        "name": "Basic PII Protection",
        "description": "Blocks requests containing common PII (SSN, credit cards, emails)",
        "category": "pii",
        "policy_type": "pii_pattern",
        "policy_config": {
            "patterns": ["ssn", "credit_card", "email", "phone"],
            "action": "block",
            "threshold": 0.8,
        },
        "variables": {
            "threshold": {
                "type": "float",
                "default": 0.8,
                "description": "Confidence threshold for detection",
            },
            "action": {
                "type": "enum",
                "options": ["block", "warn", "log"],
                "default": "block",
            },
        },
    },
    {
        "template_id": "tpl_injection_strict",
        "name": "Strict Injection Prevention",
        "description": "Aggressive detection of prompt injection attempts",
        "category": "injection",
        "policy_type": "injection_rule",
        "policy_config": {
            "patterns": [
                r"ignore\s+(previous|all)\s+instructions",
                r"(you\s+are|act\s+as)\s+a\s+",
                r"disregard\s+.*\s+rules",
                r"system:\s*",
            ],
            "action": "block",
            "case_sensitive": False,
        },
        "variables": {
            "action": {
                "type": "enum",
                "options": ["block", "warn"],
                "default": "block",
            },
        },
    },
    {
        "template_id": "tpl_rate_limit",
        "name": "Request Rate Limiting",
        "description": "Limit requests per user per time window",
        "category": "rate_limit",
        "policy_type": "custom_filter",
        "policy_config": {
            "type": "rate_limit",
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "burst_limit": 10,
        },
        "variables": {
            "requests_per_minute": {
                "type": "int",
                "default": 60,
                "min": 1,
                "max": 1000,
            },
            "requests_per_hour": {
                "type": "int",
                "default": 1000,
                "min": 1,
                "max": 10000,
            },
        },
    },
    {
        "template_id": "tpl_content_safety",
        "name": "Content Safety Filter",
        "description": "Block harmful, violent, or inappropriate content",
        "category": "content_moderation",
        "policy_type": "content_moderation",
        "policy_config": {
            "categories": ["violence", "hate_speech", "adult_content", "self_harm"],
            "threshold": 0.7,
            "action": "block",
        },
        "variables": {
            "categories": {
                "type": "multi_select",
                "options": ["violence", "hate_speech", "adult_content", "self_harm", "spam"],
                "default": ["violence", "hate_speech"],
            },
            "threshold": {
                "type": "float",
                "default": 0.7,
                "min": 0.5,
                "max": 1.0,
            },
        },
    },
    {
        "template_id": "tpl_hipaa_compliant",
        "name": "HIPAA Compliance",
        "description": "Detect and protect PHI (Protected Health Information)",
        "category": "compliance",
        "policy_type": "pii_pattern",
        "policy_config": {
            "patterns": ["medical_record", "diagnosis", "treatment", "patient_id"],
            "action": "block",
            "logging": {
                "enabled": True,
                "redact_pii": True,
            },
        },
        "compliance_frameworks": ["HIPAA"],
    },
]


class PolicyTemplateService:
    """
    Service for managing policy templates

    Templates provide pre-configured policies that users can
    quickly apply with optional customization.
    """

    def __init__(self, db: Session):
        self.db = db
        self._templates = {t["template_id"]: t for t in BUILTIN_TEMPLATES}

    def list_templates(
        self,
        category: Optional[str] = None,
        compliance_framework: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List available templates

        Args:
            category: Filter by category (pii, injection, etc.)
            compliance_framework: Filter by compliance (HIPAA, GDPR, etc.)
        """
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.get("category") == category]

        if compliance_framework:
            templates = [
                t for t in templates
                if compliance_framework in t.get("compliance_frameworks", [])
            ]

        return templates

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID"""
        return self._templates.get(template_id)

    def instantiate_template(
        self,
        template_id: str,
        org_id: UUID,
        policy_name: str,
        variable_values: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Create a new policy from a template

        Args:
            template_id: Template to instantiate
            org_id: Organization creating the policy
            policy_name: Name for the new policy
            variable_values: Custom values for template variables
            created_by: User creating the policy
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Start with template config
        policy_config = template["policy_config"].copy()

        # Apply variable overrides
        if variable_values:
            for var_name, var_value in variable_values.items():
                var_spec = template.get("variables", {}).get(var_name)
                if var_spec:
                    # Validate value
                    if not self._validate_variable(var_spec, var_value):
                        raise ValueError(f"Invalid value for variable {var_name}")
                    # Apply to config
                    policy_config[var_name] = var_value

        # Create policy data
        return {
            "policy_id": str(uuid4()),
            "org_id": str(org_id),
            "policy_name": policy_name,
            "policy_type": template["policy_type"],
            "description": template["description"],
            "policy_config": policy_config,
            "template_id": template_id,
            "status": "draft",
            "version": 1,
            "created_by": str(created_by) if created_by else None,
            "created_at": datetime.utcnow().isoformat(),
        }

    def _validate_variable(
        self,
        spec: Dict[str, Any],
        value: Any
    ) -> bool:
        """Validate a variable value against its spec"""
        var_type = spec.get("type")

        if var_type == "int":
            if not isinstance(value, int):
                return False
            if "min" in spec and value < spec["min"]:
                return False
            if "max" in spec and value > spec["max"]:
                return False

        elif var_type == "float":
            if not isinstance(value, (int, float)):
                return False
            if "min" in spec and value < spec["min"]:
                return False
            if "max" in spec and value > spec["max"]:
                return False

        elif var_type == "enum":
            if value not in spec.get("options", []):
                return False

        elif var_type == "multi_select":
            if not isinstance(value, list):
                return False
            if not all(v in spec.get("options", []) for v in value):
                return False

        return True
```

---

## 3. Security Analytics

### 3.1 Analytics Data Pipeline

```python
# sentinel/analytics/pipeline.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

@dataclass
class TimeSeriesDataPoint:
    """Single data point in time series"""
    timestamp: datetime
    value: float
    dimensions: Dict[str, str]


class AnalyticsPipeline:
    """
    Data pipeline for security analytics

    Aggregates audit logs into time-series data for analysis.
    Supports multiple storage backends (ClickHouse, TimescaleDB, PostgreSQL).
    """

    def __init__(self, storage_backend: str = "postgres"):
        self.storage_backend = storage_backend
        self._aggregation_intervals = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "1h": timedelta(hours=1),
            "1d": timedelta(days=1),
        }

    async def aggregate_metrics(
        self,
        org_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1h",
        metrics: List[str] = None,
    ) -> List[TimeSeriesDataPoint]:
        """
        Aggregate audit logs into time-series metrics

        Args:
            org_id: Organization to aggregate for
            start_time: Start of time range
            end_time: End of time range
            interval: Aggregation interval (1m, 5m, 1h, 1d)
            metrics: List of metrics to calculate
        """
        if metrics is None:
            metrics = [
                "total_requests",
                "blocked_requests",
                "avg_risk_score",
                "pii_detections",
                "injection_attempts",
            ]

        interval_delta = self._aggregation_intervals.get(interval, timedelta(hours=1))

        # Generate time buckets
        data_points = []
        current = start_time

        while current < end_time:
            bucket_end = min(current + interval_delta, end_time)

            # Calculate metrics for this bucket
            bucket_metrics = await self._calculate_bucket_metrics(
                org_id, current, bucket_end, metrics
            )

            for metric_name, value in bucket_metrics.items():
                data_points.append(TimeSeriesDataPoint(
                    timestamp=current,
                    value=value,
                    dimensions={"metric": metric_name, "org_id": org_id},
                ))

            current = bucket_end

        return data_points

    async def _calculate_bucket_metrics(
        self,
        org_id: str,
        start: datetime,
        end: datetime,
        metrics: List[str],
    ) -> Dict[str, float]:
        """Calculate metrics for a single time bucket"""
        # This would query the appropriate database
        # Placeholder implementation
        return {
            "total_requests": 100,
            "blocked_requests": 5,
            "avg_risk_score": 0.23,
            "pii_detections": 3,
            "injection_attempts": 1,
        }


class TrendAnalyzer:
    """
    Analyzes trends in security metrics

    Detects:
    - Increasing/decreasing trends
    - Seasonality patterns
    - Anomalous spikes
    """

    def analyze_trend(
        self,
        data_points: List[TimeSeriesDataPoint],
        sensitivity: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Analyze trend in time series data

        Args:
            data_points: Time series data
            sensitivity: Threshold for detecting significant changes
        """
        if len(data_points) < 3:
            return {"trend": "insufficient_data"}

        values = [p.value for p in data_points]

        # Calculate trend direction
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)

        change_rate = (second_half - first_half) / max(first_half, 0.001)

        if change_rate > sensitivity:
            trend = "increasing"
        elif change_rate < -sensitivity:
            trend = "decreasing"
        else:
            trend = "stable"

        # Detect anomalies (simple z-score)
        import numpy as np
        mean = np.mean(values)
        std = np.std(values)

        anomalies = []
        for i, point in enumerate(data_points):
            if std > 0:
                z_score = abs(point.value - mean) / std
                if z_score > 2.5:  # 2.5 standard deviations
                    anomalies.append({
                        "timestamp": point.timestamp.isoformat(),
                        "value": point.value,
                        "z_score": z_score,
                    })

        return {
            "trend": trend,
            "change_rate": change_rate,
            "mean": mean,
            "std": std,
            "anomalies": anomalies,
            "data_points": len(data_points),
        }
```

### 3.2 Risk Scoring by Organization

```python
# sentinel/analytics/risk_scoring.py
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class OrgRiskScore:
    """Risk score for an organization"""
    org_id: str
    overall_score: float  # 0-100
    threat_score: float
    vulnerability_score: float
    compliance_score: float
    trend: str  # improving, stable, worsening
    last_calculated: datetime


class OrgRiskScorer:
    """
    Calculates risk scores at the organization level

    Combines multiple factors:
    - Threat activity (blocked attacks, anomalies)
    - Vulnerability indicators (policy gaps, false positives)
    - Compliance status (audit findings, policy coverage)
    """

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            "threat": 0.4,
            "vulnerability": 0.3,
            "compliance": 0.3,
        }

    def calculate_risk_score(
        self,
        org_id: str,
        metrics: Dict[str, Any],
        historical_data: List[Dict[str, Any]] = None,
    ) -> OrgRiskScore:
        """
        Calculate comprehensive risk score for an organization

        Args:
            org_id: Organization identifier
            metrics: Current security metrics
            historical_data: Historical metrics for trend analysis
        """
        # Calculate component scores
        threat_score = self._calculate_threat_score(metrics)
        vulnerability_score = self._calculate_vulnerability_score(metrics)
        compliance_score = self._calculate_compliance_score(metrics)

        # Weighted average
        overall = (
            threat_score * self.weights["threat"] +
            vulnerability_score * self.weights["vulnerability"] +
            compliance_score * self.weights["compliance"]
        )

        # Determine trend
        trend = "stable"
        if historical_data and len(historical_data) >= 2:
            prev_score = historical_data[-2].get("overall_score", overall)
            if overall < prev_score - 5:
                trend = "improving"
            elif overall > prev_score + 5:
                trend = "worsening"

        return OrgRiskScore(
            org_id=org_id,
            overall_score=round(overall, 1),
            threat_score=round(threat_score, 1),
            vulnerability_score=round(vulnerability_score, 1),
            compliance_score=round(compliance_score, 1),
            trend=trend,
            last_calculated=datetime.utcnow(),
        )

    def _calculate_threat_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate threat score (0-100, higher = more risk)

        Factors:
        - Blocked attack rate
        - Anomaly detection rate
        - High severity incidents
        """
        total_requests = metrics.get("total_requests", 1)
        blocked = metrics.get("blocked_requests", 0)
        anomalies = metrics.get("anomaly_count", 0)
        critical_incidents = metrics.get("critical_incidents", 0)

        # Normalize metrics
        block_rate = (blocked / max(total_requests, 1)) * 100
        anomaly_rate = (anomalies / max(total_requests, 1)) * 100

        # Weight and combine
        score = (
            min(block_rate * 10, 40) +  # Up to 40 points for blocks
            min(anomaly_rate * 20, 30) +  # Up to 30 points for anomalies
            min(critical_incidents * 10, 30)  # Up to 30 points for critical
        )

        return min(score, 100)

    def _calculate_vulnerability_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate vulnerability score (0-100, higher = more risk)

        Factors:
        - False positive rate (indicates policy gaps)
        - Unaddressed alerts
        - Policy coverage gaps
        """
        false_positives = metrics.get("false_positives", 0)
        total_alerts = metrics.get("total_alerts", 1)
        unaddressed_alerts = metrics.get("unaddressed_alerts", 0)
        policy_coverage = metrics.get("policy_coverage", 100)  # percentage

        fp_rate = (false_positives / max(total_alerts, 1)) * 100
        unaddressed_rate = (unaddressed_alerts / max(total_alerts, 1)) * 100
        coverage_gap = 100 - policy_coverage

        score = (
            min(fp_rate * 2, 30) +
            min(unaddressed_rate * 2, 40) +
            min(coverage_gap, 30)
        )

        return min(score, 100)

    def _calculate_compliance_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate compliance score (0-100, higher = more risk)

        Factors:
        - Audit findings
        - Missing required policies
        - Overdue reviews
        """
        audit_findings = metrics.get("audit_findings", 0)
        missing_policies = metrics.get("missing_required_policies", 0)
        overdue_reviews = metrics.get("overdue_policy_reviews", 0)

        score = (
            min(audit_findings * 15, 40) +
            min(missing_policies * 20, 40) +
            min(overdue_reviews * 5, 20)
        )

        return min(score, 100)
```

---

## 4. Integration Platform

### 4.1 Webhook System

```python
# sentinel/integrations/webhooks.py
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4
import hmac
import hashlib
import json
import asyncio
import httpx

from dataclasses import dataclass


@dataclass
class WebhookConfig:
    """Webhook configuration"""
    webhook_id: UUID
    org_id: UUID
    url: str
    secret: str
    events: List[str]
    enabled: bool = True
    failure_count: int = 0
    max_retries: int = 3


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt"""
    delivery_id: UUID
    webhook_id: UUID
    event_type: str
    payload: Dict[str, Any]
    status: str  # pending, success, failed
    response_code: Optional[int]
    retry_count: int
    created_at: datetime
    delivered_at: Optional[datetime]


class WebhookService:
    """
    Webhook delivery service with retry and signing

    Features:
    - HMAC-SHA256 signing for payload verification
    - Exponential backoff retry
    - Dead letter queue for failed deliveries
    """

    # Event types
    EVENT_TYPES = [
        "threat.detected",
        "threat.blocked",
        "policy.created",
        "policy.updated",
        "policy.deployed",
        "anomaly.detected",
        "compliance.alert",
    ]

    def __init__(self, db=None, max_retries: int = 3):
        self.db = db
        self.max_retries = max_retries
        self._delivery_queue: asyncio.Queue = asyncio.Queue()

    def create_webhook(
        self,
        org_id: UUID,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> WebhookConfig:
        """
        Create a new webhook configuration

        Args:
            org_id: Organization owning the webhook
            url: Endpoint URL to deliver to
            events: List of event types to subscribe to
            secret: Optional secret for HMAC signing (generated if not provided)
        """
        # Validate events
        for event in events:
            if event not in self.EVENT_TYPES:
                raise ValueError(f"Unknown event type: {event}")

        # Generate secret if not provided
        if not secret:
            secret = self._generate_secret()

        config = WebhookConfig(
            webhook_id=uuid4(),
            org_id=org_id,
            url=url,
            secret=secret,
            events=events,
            enabled=True,
        )

        # Would save to database here
        return config

    async def trigger_event(
        self,
        org_id: UUID,
        event_type: str,
        payload: Dict[str, Any],
    ) -> List[UUID]:
        """
        Trigger webhooks for an event

        Args:
            org_id: Organization the event belongs to
            event_type: Type of event
            payload: Event data

        Returns:
            List of delivery IDs for tracking
        """
        # Get all webhooks subscribed to this event for this org
        webhooks = self._get_webhooks_for_event(org_id, event_type)

        delivery_ids = []
        for webhook in webhooks:
            if not webhook.enabled:
                continue

            delivery = WebhookDelivery(
                delivery_id=uuid4(),
                webhook_id=webhook.webhook_id,
                event_type=event_type,
                payload=payload,
                status="pending",
                response_code=None,
                retry_count=0,
                created_at=datetime.utcnow(),
                delivered_at=None,
            )

            # Queue for delivery
            await self._delivery_queue.put((webhook, delivery))
            delivery_ids.append(delivery.delivery_id)

        return delivery_ids

    async def process_deliveries(self):
        """Background task to process webhook deliveries"""
        while True:
            try:
                webhook, delivery = await self._delivery_queue.get()
                await self._deliver(webhook, delivery)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing delivery: {e}")

    async def _deliver(
        self,
        webhook: WebhookConfig,
        delivery: WebhookDelivery,
    ) -> bool:
        """
        Deliver a webhook with retry logic
        """
        payload_json = json.dumps(delivery.payload, default=str)

        # Sign the payload
        signature = self._sign_payload(payload_json, webhook.secret)

        headers = {
            "Content-Type": "application/json",
            "X-Sentinel-Signature": signature,
            "X-Sentinel-Event": delivery.event_type,
            "X-Sentinel-Delivery-ID": str(delivery.delivery_id),
            "X-Sentinel-Timestamp": datetime.utcnow().isoformat(),
        }

        async with httpx.AsyncClient() as client:
            while delivery.retry_count <= self.max_retries:
                try:
                    response = await client.post(
                        webhook.url,
                        content=payload_json,
                        headers=headers,
                        timeout=30.0,
                    )

                    delivery.response_code = response.status_code

                    if response.status_code < 300:
                        delivery.status = "success"
                        delivery.delivered_at = datetime.utcnow()
                        # Save delivery record
                        return True

                    # Non-success response
                    delivery.retry_count += 1

                except Exception as e:
                    print(f"Webhook delivery failed: {e}")
                    delivery.retry_count += 1

                # Exponential backoff
                if delivery.retry_count <= self.max_retries:
                    backoff = 2 ** delivery.retry_count
                    await asyncio.sleep(backoff)

        # All retries exhausted
        delivery.status = "failed"
        webhook.failure_count += 1

        # Disable webhook if too many failures
        if webhook.failure_count >= 10:
            webhook.enabled = False

        return False

    def _sign_payload(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for payload"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def _generate_secret(self) -> str:
        """Generate a random webhook secret"""
        import secrets
        return secrets.token_hex(32)

    def _get_webhooks_for_event(
        self,
        org_id: UUID,
        event_type: str
    ) -> List[WebhookConfig]:
        """Get webhooks subscribed to an event"""
        # Would query database
        # Placeholder implementation
        return []

    @staticmethod
    def verify_signature(
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify webhook signature (for webhook receivers)

        Consumers of webhooks can use this to verify authenticity
        """
        expected = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)
```

### 4.2 Slack Integration

```python
# sentinel/integrations/slack.py
from typing import Dict, Any, Optional, List
from datetime import datetime
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError


class SlackIntegration:
    """
    Slack integration for security alerts

    Supports:
    - Direct messages to users
    - Channel notifications
    - Interactive message actions
    - Block kit formatted messages
    """

    def __init__(
        self,
        bot_token: str,
        default_channel: Optional[str] = None,
    ):
        self.client = AsyncWebClient(token=bot_token)
        self.default_channel = default_channel

    async def send_alert(
        self,
        channel: Optional[str],
        alert_type: str,
        title: str,
        details: Dict[str, Any],
        severity: str = "medium",
    ) -> bool:
        """
        Send a security alert to Slack

        Args:
            channel: Channel ID (uses default if not provided)
            alert_type: Type of alert (threat, anomaly, policy, etc.)
            title: Alert title
            details: Alert details
            severity: Alert severity (low, medium, high, critical)
        """
        channel = channel or self.default_channel
        if not channel:
            raise ValueError("No channel specified")

        # Build Block Kit message
        blocks = self._build_alert_blocks(alert_type, title, details, severity)

        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=f"Security Alert: {title}",  # Fallback text
            )
            return response["ok"]
        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            return False

    def _build_alert_blocks(
        self,
        alert_type: str,
        title: str,
        details: Dict[str, Any],
        severity: str,
    ) -> List[Dict[str, Any]]:
        """Build Slack Block Kit blocks for alert message"""

        severity_emoji = {
            "low": ":white_circle:",
            "medium": ":large_yellow_circle:",
            "high": ":large_orange_circle:",
            "critical": ":red_circle:",
        }

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji.get(severity, ':warning:')} {title}",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{alert_type}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity.upper()}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    },
                ]
            },
        ]

        # Add details section
        if details:
            detail_text = "\n".join(
                f"• *{k}:* {v}" for k, v in details.items()
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Details:*\n{detail_text}",
                }
            })

        # Add action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Dashboard",
                        "emoji": True,
                    },
                    "url": details.get("dashboard_url", "https://sentinel.example.com"),
                    "action_id": "view_dashboard",
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Acknowledge",
                        "emoji": True,
                    },
                    "style": "primary",
                    "action_id": "acknowledge_alert",
                },
            ]
        })

        return blocks

    async def send_daily_digest(
        self,
        channel: str,
        metrics: Dict[str, Any],
    ) -> bool:
        """
        Send daily security digest to Slack
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":shield: Daily Security Digest",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Requests:*\n{metrics.get('total_requests', 0):,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Threats Blocked:*\n{metrics.get('blocked_requests', 0):,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*PII Detections:*\n{metrics.get('pii_detections', 0):,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Avg Risk Score:*\n{metrics.get('avg_risk_score', 0):.2f}",
                    },
                ]
            },
            {
                "type": "divider",
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Report generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    }
                ]
            },
        ]

        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text="Daily Security Digest",
            )
            return response["ok"]
        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            return False
```

### 4.3 SIEM Integration

```python
# sentinel/integrations/siem.py
from typing import Dict, Any, Optional
from datetime import datetime
import socket
import json


class SIEMExporter:
    """
    Export security events to SIEM systems

    Supports:
    - Syslog (RFC 5424)
    - CEF (Common Event Format)
    - Splunk HEC (HTTP Event Collector)
    """

    # CEF severity mapping
    CEF_SEVERITY = {
        "low": 3,
        "medium": 5,
        "high": 7,
        "critical": 10,
    }

    def __init__(
        self,
        siem_type: str,  # syslog, cef, splunk
        config: Dict[str, Any],
    ):
        self.siem_type = siem_type
        self.config = config
        self._socket = None

    async def export_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str = "medium",
    ) -> bool:
        """
        Export a security event to SIEM

        Args:
            event_type: Type of event
            event_data: Event details
            severity: Event severity
        """
        if self.siem_type == "syslog":
            return await self._export_syslog(event_type, event_data, severity)
        elif self.siem_type == "cef":
            return await self._export_cef(event_type, event_data, severity)
        elif self.siem_type == "splunk":
            return await self._export_splunk(event_type, event_data, severity)
        else:
            raise ValueError(f"Unknown SIEM type: {self.siem_type}")

    async def _export_syslog(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str,
    ) -> bool:
        """Export event via Syslog (RFC 5424)"""
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 514)
        protocol = self.config.get("protocol", "udp")

        # Build syslog message
        # PRI = facility * 8 + severity
        # Using LOCAL0 (16) facility
        syslog_severity = {"low": 6, "medium": 4, "high": 3, "critical": 2}
        pri = 16 * 8 + syslog_severity.get(severity, 4)

        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        hostname = socket.gethostname()
        app_name = "sentinel"

        # Structured data
        sd = f'[sentinel@12345 eventType="{event_type}" severity="{severity}"]'

        # Message
        msg = json.dumps(event_data)

        syslog_msg = f"<{pri}>1 {timestamp} {hostname} {app_name} - - {sd} {msg}"

        try:
            if protocol == "udp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(syslog_msg.encode(), (host, port))
                sock.close()
            else:  # TCP
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))
                sock.sendall((syslog_msg + "\n").encode())
                sock.close()
            return True
        except Exception as e:
            print(f"Syslog export failed: {e}")
            return False

    async def _export_cef(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str,
    ) -> bool:
        """Export event in CEF format"""
        # CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension

        cef_severity = self.CEF_SEVERITY.get(severity, 5)

        # Build extension (key=value pairs)
        extension_parts = []
        for key, value in event_data.items():
            # CEF key mapping
            cef_key = self._map_to_cef_key(key)
            clean_value = str(value).replace("\\", "\\\\").replace("=", "\\=")
            extension_parts.append(f"{cef_key}={clean_value}")

        extension = " ".join(extension_parts)

        cef_message = (
            f"CEF:0|Sentinel|SecurityPlatform|1.0|{event_type}|"
            f"{event_type}|{cef_severity}|{extension}"
        )

        # Send via syslog
        return await self._export_syslog(event_type, {"cef": cef_message}, severity)

    async def _export_splunk(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str,
    ) -> bool:
        """Export event to Splunk HEC"""
        import httpx

        hec_url = self.config.get("hec_url")
        hec_token = self.config.get("hec_token")

        if not hec_url or not hec_token:
            raise ValueError("Splunk HEC URL and token required")

        # Build HEC event
        hec_event = {
            "time": datetime.utcnow().timestamp(),
            "sourcetype": "sentinel:security",
            "source": "sentinel",
            "event": {
                "event_type": event_type,
                "severity": severity,
                **event_data,
            }
        }

        headers = {
            "Authorization": f"Splunk {hec_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    hec_url,
                    json=hec_event,
                    headers=headers,
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Splunk export failed: {e}")
            return False

    def _map_to_cef_key(self, key: str) -> str:
        """Map internal keys to CEF standard keys"""
        cef_mapping = {
            "user_id": "suser",
            "source_ip": "src",
            "destination_ip": "dst",
            "risk_score": "cn1",
            "event_type": "cat",
            "message": "msg",
            "request_url": "request",
        }
        return cef_mapping.get(key, f"cs1{key}")  # Custom string field
```

---

## 5. Database Schema Changes

See the schema definitions in `MONTH_3_4_ADVANCED_SECURITY_GUIDE.md` Appendix.

---

## 6. API Endpoint Specifications

### New REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ml/anomaly/analyze` | Real-time anomaly detection |
| GET | `/api/v1/ml/models` | List ML models |
| POST | `/api/v1/ml/models/train` | Trigger model training |
| GET | `/api/v1/policies/{id}/versions` | Get policy version history |
| POST | `/api/v1/policies/{id}/versions` | Create new version |
| GET | `/api/v1/policies/versions/{a}/diff/{b}` | Diff two versions |
| POST | `/api/v1/policies/templates/instantiate` | Create policy from template |
| GET | `/api/v1/policies/templates` | List available templates |
| POST | `/api/v1/ab-tests` | Create A/B test |
| GET | `/api/v1/ab-tests/{id}/results` | Get test results |
| POST | `/api/v1/ab-tests/{id}/conclude` | Conclude test |
| GET | `/api/v1/analytics/trends` | Get trend analysis |
| GET | `/api/v1/analytics/risk-scores` | Get org risk scores |
| POST | `/api/v1/webhooks` | Create webhook |
| GET | `/api/v1/webhooks` | List webhooks |
| DELETE | `/api/v1/webhooks/{id}` | Delete webhook |
| POST | `/api/v1/integrations/slack/test` | Test Slack connection |
| POST | `/api/v1/integrations/siem/export` | Manual SIEM export |

---

## 7. Service Layer Design

### Service Registry

```python
# sentinel/services/__init__.py
from typing import Dict, Any

class ServiceRegistry:
    """Central registry for all services"""

    _instances: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, service: Any) -> None:
        cls._instances[name] = service

    @classmethod
    def get(cls, name: str) -> Any:
        return cls._instances.get(name)


# Service initialization
def init_services(db, config):
    """Initialize all services"""
    from .ml.anomaly_detector import AnomalyDetectionService
    from .saas.services.policy_versioning import PolicyVersionControl
    from .saas.services.ab_testing import ABTestingService
    from .integrations.webhooks import WebhookService

    ServiceRegistry.register("anomaly", AnomalyDetectionService(
        model_path=config.get("ML_MODEL_PATH"),
        db_adapter=db,
    ))

    ServiceRegistry.register("policy_versions", PolicyVersionControl(db))
    ServiceRegistry.register("ab_testing", ABTestingService(db))
    ServiceRegistry.register("webhooks", WebhookService(db))
```

---

## Summary

This backend implementation guide covers:

1. **Advanced Threat Detection:** ML-based anomaly detection with Isolation Forest, behavioral analysis with user baselines, and threat intelligence feed integration
2. **Advanced Policy Engine:** Git-like version control, A/B testing framework, custom DSL with PLY parser, and policy templates
3. **Security Analytics:** Time-series data pipeline, trend analysis, and organization-level risk scoring
4. **Integration Platform:** Webhooks with HMAC signing, Slack integration with Block Kit, and SIEM export (Syslog/CEF/Splunk)

Estimated total implementation time: 6-8 weeks with 2-3 backend engineers.
