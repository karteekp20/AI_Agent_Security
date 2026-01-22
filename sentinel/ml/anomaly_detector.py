from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import replace
import asyncio

from .feature_engineering import FeatureExtractor, UserFeatures
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
    ) -> List[Dict[str, Any]]:
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
        baseline_features: UserFeatures,
        user_input: str,
        context: Dict[str, Any],
    ) -> UserFeatures:
        """
        Add features from current request to baseline.

        Updates the baseline features with information from the current request
        to provide real-time context for anomaly detection.

        Args:
            baseline_features: Features extracted from historical data
            user_input: The current user input being analyzed
            context: Additional context (IP, timestamp, session, etc.)

        Returns:
            Updated UserFeatures with current request information
        """
        # Current timing information
        now = datetime.utcnow()
        if "timestamp" in context:
            try:
                if isinstance(context["timestamp"], datetime):
                    now = context["timestamp"]
                else:
                    now = datetime.fromisoformat(str(context["timestamp"]))
            except (ValueError, TypeError):
                pass

        hour_of_day = now.hour
        day_of_week = now.weekday()

        # Content analysis of current input
        input_length = len(user_input)
        tokens = user_input.split()
        unique_tokens = set(tokens)

        # Calculate ratios for current input
        unique_token_ratio = len(unique_tokens) / max(len(tokens), 1) if tokens else 0
        special_char_ratio = sum(1 for c in user_input if not c.isalnum() and not c.isspace()) / max(input_length, 1)
        numeric_ratio = sum(1 for c in user_input if c.isdigit()) / max(input_length, 1)
        uppercase_ratio = sum(1 for c in user_input if c.isupper()) / max(input_length, 1)

        # Check for injection keywords in current input
        injection_keywords = [
            "ignore", "forget", "override", "system", "admin",
            "sudo", "root", "password", "secret", "bypass",
            "execute", "eval", "script", "<script", "javascript:",
        ]
        injection_count = sum(1 for kw in injection_keywords if kw.lower() in user_input.lower())

        # Check for code patterns
        code_patterns = ["import ", "def ", "class ", "function ", "exec(", "eval(", "os."]
        code_indicator = any(pattern in user_input for pattern in code_patterns)

        # Update the baseline with current request context
        # Use weighted average for continuous features
        alpha = 0.3  # Weight for current request

        updated_features = replace(
            baseline_features,
            # Update timing to current
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,

            # Update request length with weighted average
            avg_request_length=(
                (1 - alpha) * baseline_features.avg_request_length +
                alpha * input_length
            ),
            max_request_length=max(baseline_features.max_request_length, input_length),

            # Update content ratios with weighted average
            unique_token_ratio=(
                (1 - alpha) * baseline_features.unique_token_ratio +
                alpha * unique_token_ratio
            ),
            special_char_ratio=(
                (1 - alpha) * baseline_features.special_char_ratio +
                alpha * special_char_ratio
            ),
            numeric_ratio=(
                (1 - alpha) * baseline_features.numeric_ratio +
                alpha * numeric_ratio
            ),
            uppercase_ratio=(
                (1 - alpha) * baseline_features.uppercase_ratio +
                alpha * uppercase_ratio
            ),

            # Update risk indicators
            injection_keyword_count=baseline_features.injection_keyword_count + injection_count,
            avg_risk_score=max(
                baseline_features.avg_risk_score,
                context.get("risk_score", 0) or 0
            ),

            # Increment session counters
            requests_in_session=baseline_features.requests_in_session + 1,
        )

        return updated_features

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