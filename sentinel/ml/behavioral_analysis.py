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