"""
Meta-Learning Agent: Rule Management
Handles versioning, deployment, and rollback of security rules
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
from pathlib import Path

from .schemas import (
    RuleVersion,
    DeploymentStrategy,
    DiscoveredPattern,
    PatternStatus,
    PatternType,
)


class DeploymentPhase(str, Enum):
    """Canary deployment phases"""
    INITIAL = "initial"  # 10% traffic
    EXPANDED = "expanded"  # 50% traffic
    FULL = "full"  # 100% traffic


class RuleManager:
    """
    Manages security rule versions and safe deployments

    Capabilities:
    1. Version control for security rules
    2. Canary deployments (10% → 50% → 100%)
    3. Automated rollback on performance degradation
    4. A/B testing for rule effectiveness
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        auto_rollback: bool = True
    ):
        """
        Initialize rule manager

        Args:
            storage_path: Path to store rule versions (default: ./rule_versions/)
            auto_rollback: Enable automatic rollback on issues
        """
        self.storage_path = Path(storage_path or "./rule_versions")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.auto_rollback = auto_rollback

        # Current deployed versions
        self._current_version: Optional[RuleVersion] = None
        self._canary_version: Optional[RuleVersion] = None

        # Load latest version
        self._load_latest_version()

    def create_new_version(
        self,
        patterns: List[DiscoveredPattern],
        created_by: str = "meta_learning_agent",
        changelog: str = ""
    ) -> RuleVersion:
        """
        Create a new rule version from discovered patterns

        Args:
            patterns: List of approved patterns to deploy
            created_by: Who created this version
            changelog: Description of changes

        Returns:
            New RuleVersion object
        """
        # Get current version number
        current_version = self._current_version.version if self._current_version else "0.0.0"
        new_version = self._increment_version(current_version)

        # Build rule sets from patterns
        pii_patterns = {}
        injection_patterns = []

        for pattern in patterns:
            if pattern.status != PatternStatus.APPROVED:
                continue

            if pattern.pattern_type == PatternType.PII_PATTERN:
                # Group by entity type (if available in pattern metadata)
                entity_type = "custom"
                if entity_type not in pii_patterns:
                    pii_patterns[entity_type] = []
                pii_patterns[entity_type].append(pattern.pattern_value)

            elif pattern.pattern_type == PatternType.INJECTION_VARIANT:
                injection_patterns.append(pattern.pattern_value)

        # Merge with existing rules if present
        if self._current_version:
            # Merge PII patterns
            for entity_type, current_patterns in self._current_version.pii_patterns.items():
                if entity_type not in pii_patterns:
                    pii_patterns[entity_type] = []
                pii_patterns[entity_type].extend(current_patterns)

            # Merge injection patterns
            injection_patterns.extend(self._current_version.injection_patterns)

        # Remove duplicates
        for entity_type in pii_patterns:
            pii_patterns[entity_type] = list(set(pii_patterns[entity_type]))
        injection_patterns = list(set(injection_patterns))

        # Track what changed
        patterns_added = []
        patterns_removed = []
        patterns_modified = []

        if self._current_version:
            # Detect additions
            old_injection_set = set(self._current_version.injection_patterns)
            new_injection_set = set(injection_patterns)
            patterns_added.extend(list(new_injection_set - old_injection_set))
            patterns_removed.extend(list(old_injection_set - new_injection_set))
        else:
            patterns_added.extend(injection_patterns)

        # Create version object
        version = RuleVersion(
            version=new_version,
            created_by=created_by,
            pii_patterns=pii_patterns,
            injection_patterns=injection_patterns,
            behavioral_rules={},
            changelog=changelog or f"Added {len(patterns_added)} new patterns",
            patterns_added=patterns_added,
            patterns_removed=patterns_removed,
            patterns_modified=patterns_modified,
            deployment_status="pending",
            deployment_percentage=0,
        )

        # Save to disk
        self._save_version(version)

        return version

    def deploy_canary(
        self,
        version: RuleVersion,
        initial_percentage: int = 10
    ) -> RuleVersion:
        """
        Deploy new version to canary (small percentage of traffic)

        Args:
            version: RuleVersion to deploy
            initial_percentage: Initial traffic percentage (default: 10%)

        Returns:
            Updated RuleVersion with canary status
        """
        version.deployment_status = "canary"
        version.deployment_percentage = initial_percentage

        self._canary_version = version
        self._save_version(version)

        return version

    def expand_canary(
        self,
        version: RuleVersion,
        new_percentage: int
    ) -> RuleVersion:
        """
        Expand canary deployment to more traffic

        Args:
            version: RuleVersion being deployed
            new_percentage: New traffic percentage (e.g., 50%)

        Returns:
            Updated RuleVersion
        """
        if version.deployment_status != "canary":
            raise ValueError("Can only expand canary deployments")

        version.deployment_percentage = new_percentage
        self._save_version(version)

        return version

    def promote_to_stable(
        self,
        version: RuleVersion
    ) -> RuleVersion:
        """
        Promote canary to stable (100% traffic)

        Args:
            version: RuleVersion to promote

        Returns:
            Updated RuleVersion
        """
        # Deprecate current stable version
        if self._current_version:
            self._current_version.deployment_status = "deprecated"
            self._save_version(self._current_version)

        # Promote canary to stable
        version.deployment_status = "stable"
        version.deployment_percentage = 100

        self._current_version = version
        self._canary_version = None
        self._save_version(version)

        return version

    def rollback(
        self,
        reason: str = "Performance degradation detected"
    ) -> Optional[RuleVersion]:
        """
        Rollback to previous stable version

        Args:
            reason: Reason for rollback

        Returns:
            Previous RuleVersion now restored, or None if no previous version
        """
        if not self._current_version:
            return None

        # Mark canary as deprecated
        if self._canary_version:
            self._canary_version.deployment_status = "deprecated"
            self._save_version(self._canary_version)
            self._canary_version = None

        # Find previous stable version
        all_versions = self._load_all_versions()
        stable_versions = [
            v for v in all_versions
            if v.deployment_status == "deprecated" and v.version != self._current_version.version
        ]

        if not stable_versions:
            return None

        # Sort by version number (semantic versioning)
        stable_versions.sort(key=lambda v: self._version_to_tuple(v.version), reverse=True)
        previous_version = stable_versions[0]

        # Restore previous version
        previous_version.deployment_status = "stable"
        previous_version.deployment_percentage = 100

        # Deprecate current
        self._current_version.deployment_status = "deprecated"
        self._save_version(self._current_version)

        self._current_version = previous_version
        self._save_version(previous_version)

        print(f"⚠️ ROLLBACK: {reason}")
        print(f"   Restored version: {previous_version.version}")

        return previous_version

    def should_rollback(
        self,
        version: RuleVersion,
        metrics: Dict[str, float]
    ) -> Tuple[bool, str]:
        """
        Check if deployment should be rolled back based on metrics

        Args:
            version: RuleVersion being monitored
            metrics: Performance metrics (false_positive_rate, latency_ms, etc.)

        Returns:
            (should_rollback: bool, reason: str)
        """
        if not self.auto_rollback:
            return False, ""

        reasons = []

        # Check false positive rate
        if "false_positive_rate" in metrics:
            fp_rate = metrics["false_positive_rate"]

            # Compare with baseline
            baseline_fp_rate = 0.03  # 3% baseline
            if self._current_version and self._current_version.false_positive_rate:
                baseline_fp_rate = self._current_version.false_positive_rate

            # Rollback if FP rate increased by >50%
            if fp_rate > baseline_fp_rate * 1.5:
                reasons.append(
                    f"False positive rate increased: {fp_rate:.2%} vs {baseline_fp_rate:.2%}"
                )

        # Check latency
        if "average_latency_ms" in metrics:
            latency = metrics["average_latency_ms"]

            baseline_latency = 100.0  # 100ms baseline
            if self._current_version and self._current_version.average_latency_ms:
                baseline_latency = self._current_version.average_latency_ms

            # Rollback if latency increased by >50ms
            if latency > baseline_latency + 50:
                reasons.append(
                    f"Latency increased: {latency:.1f}ms vs {baseline_latency:.1f}ms"
                )

        # Check detection rate (shouldn't decrease)
        if "detection_rate" in metrics:
            detection = metrics["detection_rate"]

            baseline_detection = 0.95  # 95% baseline
            if self._current_version and self._current_version.detection_rate:
                baseline_detection = self._current_version.detection_rate

            # Rollback if detection dropped by >5%
            if detection < baseline_detection - 0.05:
                reasons.append(
                    f"Detection rate dropped: {detection:.2%} vs {baseline_detection:.2%}"
                )

        if reasons:
            return True, "; ".join(reasons)

        return False, ""

    def update_metrics(
        self,
        version: RuleVersion,
        metrics: Dict[str, float]
    ) -> RuleVersion:
        """
        Update performance metrics for a deployed version

        Args:
            version: RuleVersion to update
            metrics: Performance metrics

        Returns:
            Updated RuleVersion
        """
        if "detection_rate" in metrics:
            version.detection_rate = metrics["detection_rate"]

        if "false_positive_rate" in metrics:
            version.false_positive_rate = metrics["false_positive_rate"]

        if "average_latency_ms" in metrics:
            version.average_latency_ms = metrics["average_latency_ms"]

        self._save_version(version)

        return version

    def get_active_rules(self) -> Dict[str, Any]:
        """
        Get currently active security rules

        Returns:
            Combined rules from stable + canary (if A/B testing)
        """
        if not self._current_version:
            return {
                "pii_patterns": {},
                "injection_patterns": [],
                "behavioral_rules": {},
                "version": "0.0.0",
            }

        return {
            "pii_patterns": self._current_version.pii_patterns,
            "injection_patterns": self._current_version.injection_patterns,
            "behavioral_rules": self._current_version.behavioral_rules,
            "version": self._current_version.version,
            "canary_version": self._canary_version.version if self._canary_version else None,
        }

    def get_version_history(self) -> List[RuleVersion]:
        """
        Get all rule versions ordered by creation date

        Returns:
            List of RuleVersion objects
        """
        versions = self._load_all_versions()
        versions.sort(key=lambda v: v.created_at, reverse=True)
        return versions

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _increment_version(self, current: str) -> str:
        """Increment semantic version (MAJOR.MINOR.PATCH)"""
        parts = current.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        # Increment patch version
        patch += 1

        return f"{major}.{minor}.{patch}"

    def _version_to_tuple(self, version: str) -> Tuple[int, int, int]:
        """Convert version string to tuple for sorting"""
        parts = version.split(".")
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    def _save_version(self, version: RuleVersion):
        """Save version to disk"""
        file_path = self.storage_path / f"v_{version.version}.json"

        with open(file_path, "w") as f:
            json.dump(version.model_dump(), f, indent=2, default=str)

    def _load_version(self, version_str: str) -> Optional[RuleVersion]:
        """Load specific version from disk"""
        file_path = self.storage_path / f"v_{version_str}.json"

        if not file_path.exists():
            return None

        with open(file_path, "r") as f:
            data = json.load(f)

        return RuleVersion(**data)

    def _load_all_versions(self) -> List[RuleVersion]:
        """Load all versions from disk"""
        versions = []

        for file_path in self.storage_path.glob("v_*.json"):
            with open(file_path, "r") as f:
                data = json.load(f)
            versions.append(RuleVersion(**data))

        return versions

    def _load_latest_version(self):
        """Load the latest stable version on startup"""
        versions = self._load_all_versions()

        if not versions:
            return

        # Find stable version
        stable_versions = [v for v in versions if v.deployment_status == "stable"]
        if stable_versions:
            stable_versions.sort(key=lambda v: v.created_at, reverse=True)
            self._current_version = stable_versions[0]

        # Find canary version
        canary_versions = [v for v in versions if v.deployment_status == "canary"]
        if canary_versions:
            canary_versions.sort(key=lambda v: v.created_at, reverse=True)
            self._canary_version = canary_versions[0]
