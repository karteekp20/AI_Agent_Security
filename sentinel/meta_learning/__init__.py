"""
Meta-Learning Module: Self-Improving Security
Automatically discovers new attack patterns and adapts defenses
"""

from .pattern_discoverer import MetaLearningAgent
from .rule_manager import RuleManager, DeploymentStrategy
from .threat_intelligence import ThreatIntelligence
from .approval_workflow import ApprovalWorkflow, ReviewAction, ReviewPriority
from .reports import MetaLearningReports
from .schemas import (
    DiscoveredPattern,
    RuleVersion,
    ThreatFeed,
    ThreatIndicator,
    PatternType,
    PatternStatus,
    ThreatSeverity,
    MetaLearningConfig,
)

__all__ = [
    # Core agents
    'MetaLearningAgent',
    'RuleManager',
    'ThreatIntelligence',
    'ApprovalWorkflow',
    'MetaLearningReports',

    # Data models
    'DiscoveredPattern',
    'RuleVersion',
    'ThreatFeed',
    'ThreatIndicator',

    # Enums
    'PatternType',
    'PatternStatus',
    'ThreatSeverity',
    'DeploymentStrategy',
    'ReviewAction',
    'ReviewPriority',

    # Config
    'MetaLearningConfig',
]
