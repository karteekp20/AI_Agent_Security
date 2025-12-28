"""
Meta-Learning: Human-in-the-Loop Approval Workflow
Manages review and approval of discovered security patterns
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

from .schemas import (
    DiscoveredPattern,
    PatternStatus,
    PatternType,
)


class ReviewAction(str, Enum):
    """Actions reviewers can take"""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    DEFER = "defer"


class ReviewPriority(str, Enum):
    """Priority levels for pattern review"""
    CRITICAL = "critical"  # Needs immediate review (active attack)
    HIGH = "high"  # Review within 24h
    MEDIUM = "medium"  # Review within 1 week
    LOW = "low"  # Review when convenient


class PatternReview:
    """
    Review record for a discovered pattern

    Tracks who reviewed, when, and what decision was made
    """

    def __init__(
        self,
        pattern_id: str,
        reviewer: str,
        action: ReviewAction,
        notes: str = "",
        timestamp: Optional[datetime] = None
    ):
        self.pattern_id = pattern_id
        self.reviewer = reviewer
        self.action = action
        self.notes = notes
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "reviewer": self.reviewer,
            "action": self.action,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat(),
        }


class ApprovalWorkflow:
    """
    Manages human approval workflow for discovered patterns

    Capabilities:
    1. Queue patterns for review
    2. Track review status and history
    3. Support multi-reviewer approval (e.g., 2 approvals required)
    4. Automatic notifications for pending reviews
    5. Audit trail of all decisions
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        required_approvals: int = 1,
        enable_auto_approve: bool = False,
        auto_approve_confidence: float = 0.95
    ):
        """
        Initialize approval workflow

        Args:
            storage_path: Path to store review data
            required_approvals: Number of approvals needed (default: 1)
            enable_auto_approve: Auto-approve high-confidence patterns
            auto_approve_confidence: Confidence threshold for auto-approval (default: 0.95)
        """
        self.storage_path = Path(storage_path or "./pattern_reviews")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.required_approvals = required_approvals
        self.enable_auto_approve = enable_auto_approve
        self.auto_approve_confidence = auto_approve_confidence

        # In-memory cache
        self._pending_patterns: Dict[str, DiscoveredPattern] = {}
        self._review_history: Dict[str, List[PatternReview]] = {}

        # Load existing reviews
        self._load_reviews()

    def submit_for_review(
        self,
        pattern: DiscoveredPattern,
        priority: ReviewPriority = ReviewPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit a discovered pattern for human review

        Args:
            pattern: DiscoveredPattern to review
            priority: Urgency of review
            context: Additional context for reviewers

        Returns:
            Review ID
        """
        # Check if auto-approval applies
        if self.enable_auto_approve:
            if pattern.confidence >= self.auto_approve_confidence:
                # Auto-approve high-confidence patterns
                self._auto_approve(pattern)
                return pattern.pattern_id

        # Add to pending queue
        pattern.status = PatternStatus.PENDING_REVIEW
        self._pending_patterns[pattern.pattern_id] = pattern

        # Save pattern with metadata
        self._save_pattern_for_review(pattern, priority, context or {})

        return pattern.pattern_id

    def review_pattern(
        self,
        pattern_id: str,
        reviewer: str,
        action: ReviewAction,
        notes: str = ""
    ) -> DiscoveredPattern:
        """
        Review a pattern (approve/reject/etc.)

        Args:
            pattern_id: ID of pattern to review
            reviewer: Email/username of reviewer
            action: Review action (approve, reject, etc.)
            notes: Reviewer's notes/reasoning

        Returns:
            Updated DiscoveredPattern
        """
        if pattern_id not in self._pending_patterns:
            raise ValueError(f"Pattern {pattern_id} not found in pending queue")

        pattern = self._pending_patterns[pattern_id]

        # Create review record
        review = PatternReview(
            pattern_id=pattern_id,
            reviewer=reviewer,
            action=action,
            notes=notes,
        )

        # Add to history
        if pattern_id not in self._review_history:
            self._review_history[pattern_id] = []
        self._review_history[pattern_id].append(review)

        # Update pattern based on action
        if action == ReviewAction.APPROVE:
            # Check if enough approvals
            approval_count = sum(
                1 for r in self._review_history[pattern_id]
                if r.action == ReviewAction.APPROVE
            )

            if approval_count >= self.required_approvals:
                pattern.status = PatternStatus.APPROVED
                pattern.reviewed_by = reviewer
                pattern.reviewed_at = datetime.utcnow()
                pattern.review_notes = notes

                # Remove from pending
                del self._pending_patterns[pattern_id]

        elif action == ReviewAction.REJECT:
            pattern.status = PatternStatus.REJECTED
            pattern.reviewed_by = reviewer
            pattern.reviewed_at = datetime.utcnow()
            pattern.review_notes = notes

            # Remove from pending
            del self._pending_patterns[pattern_id]

        elif action == ReviewAction.REQUEST_CHANGES:
            # Keep in pending, mark for changes
            pattern.review_notes = notes

        # Save updated state
        self._save_review(review)
        self._save_pattern_for_review(pattern, ReviewPriority.MEDIUM, {})

        return pattern

    def get_pending_reviews(
        self,
        priority: Optional[ReviewPriority] = None,
        pattern_type: Optional[PatternType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get patterns pending review

        Args:
            priority: Filter by priority level
            pattern_type: Filter by pattern type

        Returns:
            List of pending review items with metadata
        """
        pending = []

        for pattern_id, pattern in self._pending_patterns.items():
            # Load metadata
            metadata = self._load_pattern_metadata(pattern_id)

            # Apply filters
            if priority and metadata.get("priority") != priority:
                continue

            if pattern_type and pattern.pattern_type != pattern_type:
                continue

            # Get review history
            reviews = self._review_history.get(pattern_id, [])
            approval_count = sum(1 for r in reviews if r.action == ReviewAction.APPROVE)

            pending.append({
                "pattern": pattern,
                "priority": metadata.get("priority", ReviewPriority.MEDIUM),
                "context": metadata.get("context", {}),
                "submitted_at": pattern.discovered_at,
                "review_count": len(reviews),
                "approval_count": approval_count,
                "approvals_needed": self.required_approvals - approval_count,
            })

        # Sort by priority and submission time
        priority_order = {
            ReviewPriority.CRITICAL: 4,
            ReviewPriority.HIGH: 3,
            ReviewPriority.MEDIUM: 2,
            ReviewPriority.LOW: 1,
        }

        pending.sort(
            key=lambda x: (
                priority_order.get(x["priority"], 0),
                x["submitted_at"]
            ),
            reverse=True
        )

        return pending

    def get_review_history(
        self,
        pattern_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get full review history for a pattern

        Args:
            pattern_id: Pattern ID

        Returns:
            List of review records
        """
        reviews = self._review_history.get(pattern_id, [])
        return [r.to_dict() for r in reviews]

    def get_reviewer_stats(
        self,
        reviewer: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get statistics for a reviewer

        Args:
            reviewer: Reviewer email/username
            days: Time window in days

        Returns:
            Reviewer statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Collect all reviews by this reviewer
        reviews = []
        for pattern_reviews in self._review_history.values():
            reviews.extend([
                r for r in pattern_reviews
                if r.reviewer == reviewer and r.timestamp > cutoff
            ])

        # Calculate stats
        total_reviews = len(reviews)
        approvals = sum(1 for r in reviews if r.action == ReviewAction.APPROVE)
        rejections = sum(1 for r in reviews if r.action == ReviewAction.REJECT)

        return {
            "reviewer": reviewer,
            "time_period_days": days,
            "total_reviews": total_reviews,
            "approvals": approvals,
            "rejections": rejections,
            "approval_rate": approvals / total_reviews if total_reviews > 0 else 0,
        }

    def get_workflow_summary(self) -> Dict[str, Any]:
        """
        Get overall workflow summary

        Returns:
            Summary statistics
        """
        # Count by priority
        by_priority = {}
        for pattern_id, pattern in self._pending_patterns.items():
            metadata = self._load_pattern_metadata(pattern_id)
            priority = metadata.get("priority", ReviewPriority.MEDIUM)

            if priority not in by_priority:
                by_priority[priority] = 0
            by_priority[priority] += 1

        # Count by type
        by_type = {}
        for pattern in self._pending_patterns.values():
            if pattern.pattern_type not in by_type:
                by_type[pattern.pattern_type] = 0
            by_type[pattern.pattern_type] += 1

        # Calculate average review time
        completed_reviews = []
        for pattern_id, reviews in self._review_history.items():
            if reviews:
                # Find approval/rejection
                final_review = next(
                    (r for r in reviews if r.action in [ReviewAction.APPROVE, ReviewAction.REJECT]),
                    None
                )
                if final_review:
                    # Load pattern to get submission time
                    metadata = self._load_pattern_metadata(pattern_id)
                    if metadata:
                        submitted = datetime.fromisoformat(metadata.get("submitted_at", ""))
                        review_time = (final_review.timestamp - submitted).total_seconds() / 3600
                        completed_reviews.append(review_time)

        avg_review_time = sum(completed_reviews) / len(completed_reviews) if completed_reviews else 0

        return {
            "pending_reviews": len(self._pending_patterns),
            "by_priority": {str(k): v for k, v in by_priority.items()},
            "by_type": {str(k): v for k, v in by_type.items()},
            "total_reviewed": sum(len(r) for r in self._review_history.values()),
            "average_review_time_hours": avg_review_time,
            "auto_approve_enabled": self.enable_auto_approve,
        }

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _auto_approve(self, pattern: DiscoveredPattern):
        """Auto-approve high-confidence pattern"""
        pattern.status = PatternStatus.APPROVED
        pattern.reviewed_by = "auto_approval_system"
        pattern.reviewed_at = datetime.utcnow()
        pattern.review_notes = f"Auto-approved: confidence={pattern.confidence:.2%}"

        # Record in history
        review = PatternReview(
            pattern_id=pattern.pattern_id,
            reviewer="auto_approval_system",
            action=ReviewAction.APPROVE,
            notes=pattern.review_notes,
        )

        if pattern.pattern_id not in self._review_history:
            self._review_history[pattern.pattern_id] = []
        self._review_history[pattern.pattern_id].append(review)

        self._save_review(review)

    def _save_pattern_for_review(
        self,
        pattern: DiscoveredPattern,
        priority: ReviewPriority,
        context: Dict[str, Any]
    ):
        """Save pattern with review metadata"""
        file_path = self.storage_path / f"pattern_{pattern.pattern_id}.json"

        data = {
            "pattern": pattern.model_dump(),
            "priority": priority,
            "context": context,
            "submitted_at": datetime.utcnow().isoformat(),
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_pattern_metadata(self, pattern_id: str) -> Dict[str, Any]:
        """Load pattern metadata"""
        file_path = self.storage_path / f"pattern_{pattern_id}.json"

        if not file_path.exists():
            return {}

        with open(file_path, "r") as f:
            return json.load(f)

    def _save_review(self, review: PatternReview):
        """Save review record"""
        file_path = self.storage_path / f"reviews_{review.pattern_id}.json"

        # Load existing reviews
        reviews = []
        if file_path.exists():
            with open(file_path, "r") as f:
                reviews = json.load(f)

        # Add new review
        reviews.append(review.to_dict())

        # Save
        with open(file_path, "w") as f:
            json.dump(reviews, f, indent=2)

    def _load_reviews(self):
        """Load all reviews from disk"""
        for file_path in self.storage_path.glob("reviews_*.json"):
            with open(file_path, "r") as f:
                review_data = json.load(f)

            for review_dict in review_data:
                pattern_id = review_dict["pattern_id"]

                review = PatternReview(
                    pattern_id=pattern_id,
                    reviewer=review_dict["reviewer"],
                    action=ReviewAction(review_dict["action"]),
                    notes=review_dict.get("notes", ""),
                    timestamp=datetime.fromisoformat(review_dict["timestamp"]),
                )

                if pattern_id not in self._review_history:
                    self._review_history[pattern_id] = []
                self._review_history[pattern_id].append(review)

        # Load pending patterns
        for file_path in self.storage_path.glob("pattern_*.json"):
            with open(file_path, "r") as f:
                data = json.load(f)

            pattern = DiscoveredPattern(**data["pattern"])

            if pattern.status == PatternStatus.PENDING_REVIEW:
                self._pending_patterns[pattern.pattern_id] = pattern
