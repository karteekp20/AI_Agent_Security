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