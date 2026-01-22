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
        # In-memory metrics storage (use Redis or DB in production)
        self._metrics: Dict[str, Dict[str, Dict[str, Any]]] = {}

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

        return {
            "test_id": test_config.test_id,
            "control_policy_id": str(test_config.control_policy_id),
            "variant_policy_id": str(test_config.variant_policy_id),
            "traffic_percentage": test_config.traffic_percentage,
            "start_time": test_config.start_time,
            "end_time": test_config.end_time,
            "status": "active",
        }

    def get_active_tests(self, org_id: str) -> List[Dict[str, Any]]:
        """Get all active A/B tests for an organization"""
        # Get tests from database via policies with ab_test_config
        tests = []
        policies = self.db.query(Policy).filter(
            Policy.org_id == org_id,
            Policy.status == "testing",
            Policy.ab_test_config.isnot(None),
        ).all()

        for policy in policies:
            config = policy.ab_test_config
            if config:
                tests.append({
                    "test_id": config.get("test_id", ""),
                    "control_policy_id": config.get("control_policy_id", ""),
                    "variant_policy_id": str(policy.policy_id),
                    "traffic_percentage": config.get("traffic_percentage", 10),
                    "start_time": config.get("start_time"),
                    "end_time": config.get("end_time"),
                    "status": "active",
                })

        # Also include in-memory tests
        for test in self._active_tests.values():
            if self._test_is_active(test):
                tests.append({
                    "test_id": test.test_id,
                    "control_policy_id": str(test.control_policy_id),
                    "variant_policy_id": str(test.variant_policy_id),
                    "traffic_percentage": test.traffic_percentage,
                    "start_time": test.start_time,
                    "end_time": test.end_time,
                    "status": "active",
                })

        return tests

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
        # Initialize metrics structure if needed
        if test_id not in self._metrics:
            self._metrics[test_id] = {
                "control": {
                    "total_evaluations": 0,
                    "blocked_count": 0,
                    "false_positive_reports": 0,
                    "total_latency_ms": 0.0,
                    "detections": 0,
                },
                "variant": {
                    "total_evaluations": 0,
                    "blocked_count": 0,
                    "false_positive_reports": 0,
                    "total_latency_ms": 0.0,
                    "detections": 0,
                },
            }

        if group not in self._metrics[test_id]:
            return

        metrics = self._metrics[test_id][group]

        # Update counts
        metrics["total_evaluations"] += 1

        if result.get("blocked", False):
            metrics["blocked_count"] += 1
            metrics["detections"] += 1

        if result.get("false_positive", False):
            metrics["false_positive_reports"] += 1

        # Track latency
        latency = result.get("latency_ms", 0)
        metrics["total_latency_ms"] += latency

        # Note: In production, persist to Redis or database
        # Example Redis key: ab_test:{test_id}:{group}:metrics

    async def get_test_results(
        self,
        test_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current results for an A/B test

        Returns metrics for both control and variant groups
        """
        test = self._active_tests.get(test_id)
        if not test:
            # Try to find test from database
            policies = self.db.query(Policy).filter(
                Policy.status == "testing",
                Policy.ab_test_config.isnot(None),
            ).all()

            for policy in policies:
                config = policy.ab_test_config
                if config and config.get("test_id") == test_id:
                    # Found test - create from config
                    return {
                        "control": {
                            "policy_id": config.get("control_policy_id", ""),
                            "total_evaluations": 0,
                            "blocked_count": 0,
                            "false_positive_reports": 0,
                            "detection_rate": 0.0,
                        },
                        "variant": {
                            "policy_id": str(policy.policy_id),
                            "total_evaluations": 0,
                            "blocked_count": 0,
                            "false_positive_reports": 0,
                            "detection_rate": 0.0,
                        },
                        "recommendation": None,
                    }

            return None

        # Get stored metrics or empty defaults
        stored = self._metrics.get(test_id, {})

        def build_metrics(group: str, policy_id: UUID) -> Dict[str, Any]:
            data = stored.get(group, {})
            total = data.get("total_evaluations", 0) or 1  # Avoid division by zero
            blocked = data.get("blocked_count", 0)
            fp = data.get("false_positive_reports", 0)
            total_latency = data.get("total_latency_ms", 0)

            return {
                "policy_id": str(policy_id),
                "total_evaluations": data.get("total_evaluations", 0),
                "blocked_count": blocked,
                "false_positive_reports": fp,
                "avg_latency_ms": total_latency / total if total > 0 else 0.0,
                "detection_rate": blocked / total if total > 0 else 0.0,
            }

        control_metrics = build_metrics("control", test.control_policy_id)
        variant_metrics = build_metrics("variant", test.variant_policy_id)

        # Determine recommendation based on metrics
        recommendation = None
        if control_metrics["total_evaluations"] > 100 and variant_metrics["total_evaluations"] > 100:
            if variant_metrics["detection_rate"] > control_metrics["detection_rate"]:
                recommendation = "Variant shows higher detection rate"
            elif control_metrics["detection_rate"] > variant_metrics["detection_rate"]:
                recommendation = "Control shows better detection rate"

        return {
            "control": control_metrics,
            "variant": variant_metrics,
            "recommendation": recommendation,
        }

    async def conclude_test(
        self,
        test_id: str,
        winner: str,  # 'control' or 'variant'
    ) -> Dict[str, Any]:
        """
        Conclude an A/B test and optionally promote variant

        Args:
            test_id: Test to conclude
            winner: Which variant won ('control' keeps status quo)
        """
        test = self._active_tests.get(test_id)
        variant_policy_id = None
        control_policy_id = None

        if test:
            variant_policy_id = test.variant_policy_id
            control_policy_id = test.control_policy_id
        else:
            # Try to find test from database
            policies = self.db.query(Policy).filter(
                Policy.status == "testing",
                Policy.ab_test_config.isnot(None),
            ).all()

            for policy in policies:
                config = policy.ab_test_config
                if config and config.get("test_id") == test_id:
                    variant_policy_id = policy.policy_id
                    control_policy_id = config.get("control_policy_id")
                    break

        if not variant_policy_id:
            raise ValueError(f"Test {test_id} not found")

        variant = self.db.query(Policy).filter(
            Policy.policy_id == variant_policy_id
        ).first()

        if winner == "variant":
            # Promote variant to active
            variant.status = "active"
            variant.test_mode = False
            variant.test_percentage = 100
            variant.deployed_at = datetime.utcnow()
            variant.ab_test_config = None  # Clear test config

            # Archive control
            if control_policy_id:
                control = self.db.query(Policy).filter(
                    Policy.policy_id == control_policy_id
                ).first()
                if control:
                    control.status = "archived"
        else:
            # Archive variant
            variant.status = "archived"
            variant.test_mode = False
            variant.ab_test_config = None  # Clear test config

        self.db.commit()

        # Remove from active tests if present
        if test_id in self._active_tests:
            del self._active_tests[test_id]

        return {
            "test_id": test_id,
            "winner": winner,
            "variant_policy_id": str(variant_policy_id),
            "control_policy_id": str(control_policy_id) if control_policy_id else None,
        }

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