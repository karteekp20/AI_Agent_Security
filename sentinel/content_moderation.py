"""
Content Moderation: Toxicity, Profanity, Hate Speech Detection
Hybrid approach: Fast pattern matching + ML-based detection
"""

import re
from typing import List, Dict, Optional, Tuple
from enum import Enum
from pydantic import BaseModel


# ============================================================================
# ENUMS & DATA MODELS
# ============================================================================

class ToxicityCategory(str, Enum):
    """Categories of toxic content"""
    PERSONAL_ATTACK = "personal_attack"
    PROFANITY = "profanity"
    HATE_SPEECH = "hate_speech"
    HARASSMENT = "harassment"
    SEXUAL_CONTENT = "sexual_content"
    VIOLENCE = "violence"
    THREAT = "threat"
    INSULT = "insult"


class ToxicitySeverity(str, Enum):
    """Severity levels for toxic content"""
    NONE = "none"           # 0.0-0.3
    LOW = "low"             # 0.3-0.5
    MEDIUM = "medium"       # 0.5-0.7
    HIGH = "high"           # 0.7-0.9
    CRITICAL = "critical"   # 0.9-1.0


class ToxicityDetection(BaseModel):
    """Result of toxicity detection"""
    detected: bool
    toxicity_score: float  # 0.0-1.0
    severity: ToxicitySeverity
    categories: List[ToxicityCategory]
    patterns_matched: List[str]
    explanation: str
    should_warn: bool
    should_block: bool
    detection_method: str  # "pattern", "ml", "hybrid"


class ContentModerationConfig(BaseModel):
    """Configuration for content moderation"""
    enabled: bool = True

    # Detection methods
    use_patterns: bool = True
    use_ml_model: bool = False  # Disabled by default (requires model download)

    # Categories to check
    check_personal_attacks: bool = True
    check_profanity: bool = True
    check_hate_speech: bool = True
    check_harassment: bool = True
    check_sexual_content: bool = True
    check_violence: bool = True
    check_threats: bool = True

    # Thresholds
    warn_threshold: float = 0.5   # Show warning
    block_threshold: float = 0.7  # Block request

    # ML model settings
    ml_model_name: str = "unitary/toxic-bert"
    ml_confidence_threshold: float = 0.7


# ============================================================================
# TOXICITY PATTERNS
# ============================================================================

class ToxicityPatterns:
    """Pattern-based toxicity detection"""

    # Personal attacks and insults
    PERSONAL_ATTACKS = [
        r"\b(?:you(?:'re|\s+are)?\s+)?(?:useless|worthless|pathetic|incompetent|stupid|dumb|idiot|moron)\b",
        r"\b(?:you(?:'re|\s+are)?\s+)?(?:garbage|trash|waste|loser|failure)\b",
        r"\byou\s+(?:suck|blow|stink|fail)\b",
        r"\bshut\s+up\b",
        r"\bget\s+lost\b",
        r"\bgo\s+(?:away|to\s+hell)\b",
    ]

    # Profanity (common swear words - keeping it mild for examples)
    PROFANITY = [
        r"\b(?:damn|hell|crap|shit|fuck|ass|bitch|bastard)\w*\b",
        r"\bf+u+c+k+\w*\b",
        r"\bs+h+i+t+\w*\b",
    ]

    # Hate speech and discriminatory language
    HATE_SPEECH = [
        r"\b(?:hate|despise)\s+(?:all\s+)?(?:women|men|gays|trans|blacks|whites|jews|muslims|christians)\b",
        r"\b(?:women|men|gays|blacks|whites|jews|muslims)\s+(?:are\s+)?(?:all\s+)?(?:stupid|useless|bad|evil)\b",
        # Note: Real implementation would have more comprehensive patterns
    ]

    # Harassment and bullying
    HARASSMENT = [
        r"\bkill\s+yourself\b",
        r"\bdie\s+(?:already|now|please)\b",
        r"\bnobody\s+(?:likes|wants|needs)\s+you\b",
        r"\byou\s+(?:should|deserve\s+to)\s+(?:die|suffer)\b",
    ]

    # Sexual content
    SEXUAL_CONTENT = [
        r"\bsex(?:ual)?\s+(?:act|content|video)\b",
        r"\b(?:porn|xxx|nude|naked)\b",
        # Keeping it minimal for professional context
    ]

    # Violence and threats
    VIOLENCE_THREATS = [
        r"\b(?:kill|murder|assassinate|destroy|hurt|harm|attack|beat)\s+(?:you|him|her|them)\b",
        r"\bi\s+(?:will|gonna)\s+(?:kill|hurt|destroy|beat)\b",
        r"\bwatch\s+your\s+back\b",
        r"\byou(?:'re|\s+are)\s+dead\b",
    ]


# ============================================================================
# TOXICITY DETECTOR
# ============================================================================

class ToxicityDetector:
    """Hybrid toxicity detector: Pattern-based + ML-based"""

    def __init__(self, config: ContentModerationConfig):
        self.config = config
        self.patterns = self._compile_patterns()
        self._ml_model = None
        self._ml_tokenizer = None

    def _compile_patterns(self) -> Dict[ToxicityCategory, List[re.Pattern]]:
        """Compile regex patterns for enabled categories"""
        patterns = {}

        if self.config.check_personal_attacks:
            patterns[ToxicityCategory.PERSONAL_ATTACK] = [
                re.compile(p, re.IGNORECASE) for p in ToxicityPatterns.PERSONAL_ATTACKS
            ]

        if self.config.check_profanity:
            patterns[ToxicityCategory.PROFANITY] = [
                re.compile(p, re.IGNORECASE) for p in ToxicityPatterns.PROFANITY
            ]

        if self.config.check_hate_speech:
            patterns[ToxicityCategory.HATE_SPEECH] = [
                re.compile(p, re.IGNORECASE) for p in ToxicityPatterns.HATE_SPEECH
            ]

        if self.config.check_harassment:
            patterns[ToxicityCategory.HARASSMENT] = [
                re.compile(p, re.IGNORECASE) for p in ToxicityPatterns.HARASSMENT
            ]

        if self.config.check_sexual_content:
            patterns[ToxicityCategory.SEXUAL_CONTENT] = [
                re.compile(p, re.IGNORECASE) for p in ToxicityPatterns.SEXUAL_CONTENT
            ]

        if self.config.check_violence or self.config.check_threats:
            patterns[ToxicityCategory.VIOLENCE] = [
                re.compile(p, re.IGNORECASE) for p in ToxicityPatterns.VIOLENCE_THREATS
            ]

        return patterns

    @property
    def ml_model(self):
        """Lazy-load ML toxicity model"""
        if self._ml_model is None and self.config.use_ml_model:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                import torch

                self._ml_tokenizer = AutoTokenizer.from_pretrained(self.config.ml_model_name)
                self._ml_model = AutoModelForSequenceClassification.from_pretrained(
                    self.config.ml_model_name
                )
                self._ml_model.eval()
            except Exception as e:
                print(f"⚠️  ML toxicity model not available: {e}")
                self._ml_model = False  # Mark as unavailable

        return self._ml_model if self._ml_model is not False else None

    def detect_toxicity(self, text: str) -> ToxicityDetection:
        """
        Detect toxic content using hybrid approach

        Args:
            text: Input text to check

        Returns:
            ToxicityDetection with score, categories, and recommendations
        """
        if not self.config.enabled:
            return ToxicityDetection(
                detected=False,
                toxicity_score=0.0,
                severity=ToxicitySeverity.NONE,
                categories=[],
                patterns_matched=[],
                explanation="Content moderation disabled",
                should_warn=False,
                should_block=False,
                detection_method="disabled",
            )

        # Pattern-based detection (fast)
        pattern_score, pattern_categories, patterns_matched = self._detect_with_patterns(text)

        # ML-based detection (slower, more accurate)
        ml_score = 0.0
        if self.config.use_ml_model:
            ml_score = self._detect_with_ml(text)

        # Hybrid: Take maximum score
        toxicity_score = max(pattern_score, ml_score)

        # Determine severity
        severity = self._get_severity(toxicity_score)

        # Determine actions
        should_warn = toxicity_score >= self.config.warn_threshold
        should_block = toxicity_score >= self.config.block_threshold

        # Detection method
        if pattern_score > 0 and ml_score > 0:
            method = "hybrid"
        elif pattern_score > 0:
            method = "pattern"
        elif ml_score > 0:
            method = "ml"
        else:
            method = "none"

        # Build explanation
        explanation = self._build_explanation(
            toxicity_score, pattern_categories, patterns_matched
        )

        return ToxicityDetection(
            detected=toxicity_score > 0,
            toxicity_score=toxicity_score,
            severity=severity,
            categories=pattern_categories,
            patterns_matched=patterns_matched,
            explanation=explanation,
            should_warn=should_warn,
            should_block=should_block,
            detection_method=method,
        )

    def _detect_with_patterns(self, text: str) -> Tuple[float, List[ToxicityCategory], List[str]]:
        """Pattern-based detection"""
        categories_found = []
        patterns_matched = []
        max_score = 0.0

        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    if category not in categories_found:
                        categories_found.append(category)
                    patterns_matched.append(f"{category}:{pattern.pattern[:50]}")

                    # Score based on category severity
                    category_score = self._get_category_score(category)
                    max_score = max(max_score, category_score)

        return max_score, categories_found, patterns_matched

    def _detect_with_ml(self, text: str) -> float:
        """ML-based toxicity detection"""
        model = self.ml_model
        if model is None:
            return 0.0

        try:
            import torch

            # Tokenize
            inputs = self._ml_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            )

            # Predict
            with torch.no_grad():
                outputs = model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=1)
                toxicity_prob = probabilities[0][1].item()  # Toxic class probability

            return toxicity_prob if toxicity_prob >= self.config.ml_confidence_threshold else 0.0

        except Exception as e:
            print(f"ML toxicity detection failed: {e}")
            return 0.0

    def _get_category_score(self, category: ToxicityCategory) -> float:
        """Get base score for category"""
        severity_map = {
            ToxicityCategory.THREAT: 0.95,
            ToxicityCategory.VIOLENCE: 0.9,
            ToxicityCategory.HARASSMENT: 0.85,
            ToxicityCategory.HATE_SPEECH: 0.85,
            ToxicityCategory.SEXUAL_CONTENT: 0.75,
            ToxicityCategory.PERSONAL_ATTACK: 0.7,
            ToxicityCategory.INSULT: 0.65,
            ToxicityCategory.PROFANITY: 0.5,
        }
        return severity_map.get(category, 0.5)

    def _get_severity(self, score: float) -> ToxicitySeverity:
        """Map score to severity level"""
        if score >= 0.9:
            return ToxicitySeverity.CRITICAL
        elif score >= 0.7:
            return ToxicitySeverity.HIGH
        elif score >= 0.5:
            return ToxicitySeverity.MEDIUM
        elif score >= 0.3:
            return ToxicitySeverity.LOW
        else:
            return ToxicitySeverity.NONE

    def _build_explanation(
        self,
        score: float,
        categories: List[ToxicityCategory],
        patterns: List[str],
    ) -> str:
        """Build human-readable explanation"""
        if score == 0:
            return "No toxic content detected"

        category_names = ", ".join([c.value.replace("_", " ") for c in categories])
        return f"Toxic content detected: {category_names} (score={score:.2f})"


__all__ = [
    "ToxicityCategory",
    "ToxicitySeverity",
    "ToxicityDetection",
    "ContentModerationConfig",
    "ToxicityDetector",
]
