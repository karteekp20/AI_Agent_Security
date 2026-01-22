from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)


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

    def __init__(self, storage_backend: str = "postgres", db_session=None):
        self.storage_backend = storage_backend
        self.db = db_session
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
        """
        Calculate metrics for a single time bucket.

        Queries the audit_logs table for the specified time range and calculates
        requested metrics.
        """
        result: Dict[str, float] = {}

        if self.db is None:
            # Return zeros when no database available
            for metric in metrics:
                result[metric] = 0.0
            return result

        try:
            # Import here to avoid circular imports
            from sqlalchemy import func, and_

            # Try to import the AuditLog model (may not exist yet)
            try:
                from sentinel.saas.models.audit_log import AuditLog
            except ImportError:
                # AuditLog model doesn't exist - return defaults
                logger.warning("AuditLog model not found, returning default metrics")
                return {metric: 0.0 for metric in metrics}

            # Build base query for this time bucket
            base_filter = and_(
                AuditLog.org_id == org_id,
                AuditLog.created_at >= start,
                AuditLog.created_at < end,
            )

            # Calculate each requested metric
            for metric in metrics:
                if metric == "total_requests":
                    count = self.db.query(func.count(AuditLog.log_id)).filter(
                        base_filter
                    ).scalar() or 0
                    result[metric] = float(count)

                elif metric == "blocked_requests":
                    count = self.db.query(func.count(AuditLog.log_id)).filter(
                        base_filter,
                        AuditLog.blocked == True,
                    ).scalar() or 0
                    result[metric] = float(count)

                elif metric == "avg_risk_score":
                    avg = self.db.query(func.avg(AuditLog.risk_score)).filter(
                        base_filter
                    ).scalar() or 0.0
                    result[metric] = float(avg)

                elif metric == "pii_detections":
                    # Count logs that have PII entities detected
                    count = self.db.query(func.count(AuditLog.log_id)).filter(
                        base_filter,
                        AuditLog.pii_detected == True,
                    ).scalar() or 0
                    result[metric] = float(count)

                elif metric == "injection_attempts":
                    count = self.db.query(func.count(AuditLog.log_id)).filter(
                        base_filter,
                        AuditLog.injection_detected == True,
                    ).scalar() or 0
                    result[metric] = float(count)

                elif metric == "unique_users":
                    count = self.db.query(
                        func.count(func.distinct(AuditLog.user_id))
                    ).filter(base_filter).scalar() or 0
                    result[metric] = float(count)

                else:
                    # Unknown metric - default to 0
                    result[metric] = 0.0

        except Exception as e:
            logger.error(f"Error calculating bucket metrics: {e}")
            # Return zeros on error
            for metric in metrics:
                result[metric] = 0.0

        return result


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