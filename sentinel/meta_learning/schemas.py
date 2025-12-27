"""
Meta-Learning Data Models
Schemas for pattern discovery, rule management, and threat intelligence
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# PATTERN DISCOVERY
# ============================================================================

class PatternType(str, Enum):
    """Types of discovered patterns"""
    INJECTION_VARIANT = "injection_variant"
    PII_PATTERN = "pii_pattern"
    ATTACK_SIGNATURE = "attack_signature"
    FALSE_POSITIVE = "false_positive"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"


class PatternStatus(str, Enum):
    """Status of discovered patterns"""
    DISCOVERED = "discovered"  # Just found
    PENDING_REVIEW = "pending_review"  # Awaiting human approval
    APPROVED = "approved"  # Approved for deployment
    REJECTED = "rejected"  # Rejected by human
    DEPLOYED = "deployed"  # Currently in production
    DEPRECATED = "deprecated"  # No longer used


class DiscoveredPattern(BaseModel):
    """A pattern discovered by meta-learning"""
    pattern_id: str
    pattern_type: PatternType
    pattern_value: str  # The actual regex or rule

    # Discovery metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    discovery_method: str  # "llm_analysis", "clustering", "frequency"
    confidence: float = Field(ge=0.0, le=1.0)

    # Evidence
    occurrence_count: int  # How many times seen
    example_inputs: List[str] = Field(default_factory=list)  # Sample attacks
    false_positive_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    # Status
    status: PatternStatus = PatternStatus.DISCOVERED
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

    # Deployment
    deployed_version: Optional[str] = None
    deployed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# ============================================================================
# RULE MANAGEMENT
# ============================================================================

class RuleVersion(BaseModel):
    """A versioned rule set"""
    version: str  # "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # "meta_learning_agent" or "admin@company.com"

    # Rules
    pii_patterns: Dict[str, List[str]] = Field(default_factory=dict)
    injection_patterns: List[str] = Field(default_factory=list)
    behavioral_rules: Dict[str, Any] = Field(default_factory=dict)

    # Changes from previous version
    changelog: str = ""
    patterns_added: List[str] = Field(default_factory=list)
    patterns_removed: List[str] = Field(default_factory=list)
    patterns_modified: List[str] = Field(default_factory=list)

    # Deployment status
    deployment_status: str = "pending"  # "pending", "canary", "stable", "deprecated"
    deployment_percentage: int = 0  # 0-100

    # Performance metrics
    detection_rate: Optional[float] = None
    false_positive_rate: Optional[float] = None
    average_latency_ms: Optional[float] = None


class DeploymentStrategy(str, Enum):
    """Deployment strategies for rule updates"""
    IMMEDIATE = "immediate"  # Deploy to 100% immediately (risky)
    CANARY = "canary"  # 10% → 50% → 100%
    BLUE_GREEN = "blue_green"  # Deploy to parallel environment first
    SHADOW = "shadow"  # Run in shadow mode (no blocking) first


# ============================================================================
# THREAT INTELLIGENCE
# ============================================================================

class ThreatSeverity(str, Enum):
    """Threat severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatFeed(BaseModel):
    """External threat intelligence feed"""
    feed_id: str
    feed_name: str
    feed_source: str  # "MISP", "AlienVault", "custom"
    feed_url: Optional[str] = None

    enabled: bool = True
    last_updated: Optional[datetime] = None
    update_frequency_hours: int = 24

    # Threat data
    total_threats: int = 0
    active_threats: int = 0

    class Config:
        use_enum_values = True


class ThreatIndicator(BaseModel):
    """A threat indicator from threat intelligence"""
    indicator_id: str
    indicator_type: str  # "ip", "domain", "pattern", "signature"
    indicator_value: str

    severity: ThreatSeverity
    confidence: float = Field(ge=0.0, le=1.0)

    # Metadata
    source_feed: str
    first_seen: datetime
    last_seen: datetime

    # Context
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)

    # Integration
    integrated: bool = False
    integrated_as_pattern: Optional[str] = None

    class Config:
        use_enum_values = True


# ============================================================================
# ANALYTICS
# ============================================================================

class PatternPerformanceMetrics(BaseModel):
    """Performance metrics for a pattern"""
    pattern_id: str
    version: str

    # Time window
    start_time: datetime
    end_time: datetime

    # Detection metrics
    total_matches: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    # Calculated metrics
    precision: Optional[float] = None  # TP / (TP + FP)
    recall: Optional[float] = None  # TP / (TP + FN)
    f1_score: Optional[float] = None  # 2 * (precision * recall) / (precision + recall)

    # Performance
    average_match_time_ms: Optional[float] = None

    def calculate_metrics(self):
        """Calculate precision, recall, F1"""
        if self.true_positives + self.false_positives > 0:
            self.precision = self.true_positives / (self.true_positives + self.false_positives)

        if self.true_positives + self.false_negatives > 0:
            self.recall = self.true_positives / (self.true_positives + self.false_negatives)

        if self.precision and self.recall and (self.precision + self.recall) > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)


class MetaLearningConfig(BaseModel):
    """Configuration for meta-learning system"""
    enabled: bool = True

    # Pattern discovery
    min_pattern_occurrences: int = 10  # Must see pattern 10+ times
    min_pattern_confidence: float = 0.8  # 80% confidence to suggest
    max_false_positive_rate: float = 0.05  # Max 5% FP rate

    # Analysis frequency
    analysis_schedule: str = "0 2 * * *"  # Cron: 2 AM daily
    lookback_hours: int = 24  # Analyze last 24 hours

    # Deployment
    require_human_approval: bool = True
    deployment_strategy: DeploymentStrategy = DeploymentStrategy.CANARY
    canary_duration_hours: int = 24  # Monitor canary for 24h

    # Rollback thresholds
    max_error_rate_increase: float = 0.1  # Max 10% error increase
    max_latency_increase_ms: float = 50  # Max 50ms latency increase

    # Threat intelligence
    enable_threat_feeds: bool = True
    threat_feed_update_hours: int = 12  # Update every 12 hours

    class Config:
        use_enum_values = True
