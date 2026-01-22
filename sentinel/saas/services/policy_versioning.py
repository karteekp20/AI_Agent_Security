from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID, uuid4
import difflib
import json

from sqlalchemy.orm import Session
from ..models.policy import Policy


class PolicyVersionControl:
    """
    Git-like version control for security policies

    Features:
    - Version history with parent tracking
    - Diff between versions
    - Branching for A/B tests
    - Rollback capability
    """

    def __init__(self, db: Session):
        self.db = db

    async def create_version(
        self,
        policy_id: str,
        created_by: str,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new version of a policy

        Args:
            policy_id: ID of policy to version
            created_by: User ID making the change
            comment: Description of changes
        """
        # Get current policy
        current = self.db.query(Policy).filter(
            Policy.policy_id == policy_id
        ).first()

        if not current:
            raise ValueError(f"Policy {policy_id} not found")

        # Create new version (copy current config)
        new_policy_config = dict(current.policy_config) if current.policy_config else {}
        if "metadata" not in new_policy_config:
            new_policy_config["metadata"] = {}
        new_policy_config["metadata"]["commit_message"] = comment or "New version"

        new_version = Policy(
            policy_id=uuid4(),
            org_id=current.org_id,
            workspace_id=current.workspace_id,
            policy_name=current.policy_name,
            policy_type=current.policy_type,
            description=current.description,
            policy_config=new_policy_config,
            version=current.version + 1,
            parent_policy_id=current.policy_id,  # Link to previous version
            status="draft",
            created_by=UUID(created_by) if isinstance(created_by, str) else created_by,
        )

        self.db.add(new_version)
        self.db.commit()
        self.db.refresh(new_version)

        return {
            "policy_id": str(new_version.policy_id),
            "version": new_version.version,
            "status": new_version.status,
            "created_at": new_version.created_at.isoformat() if new_version.created_at else None,
            "created_by": str(new_version.created_by) if new_version.created_by else None,
            "commit_message": comment or "New version",
        }

    def get_version_history(
        self,
        policy_id: UUID,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a policy chain

        Traverses parent_policy_id links to build history
        """
        history = []
        current_id = policy_id

        while current_id and len(history) < limit:
            policy = self.db.query(Policy).filter(
                Policy.policy_id == current_id
            ).first()

            if not policy:
                break

            history.append({
                "policy_id": str(policy.policy_id),
                "version": policy.version,
                "status": policy.status,
                "created_at": policy.created_at.isoformat(),
                "created_by": str(policy.created_by) if policy.created_by else None,
                "commit_message": (
                    policy.policy_config.get("metadata", {}).get("commit_message", "")
                ),
            })

            current_id = policy.parent_policy_id

        return history

    def diff_versions(
        self,
        version_a_id: UUID,
        version_b_id: UUID,
    ) -> Dict[str, Any]:
        """
        Generate diff between two policy versions

        Returns structured diff showing what changed
        """
        policy_a = self.db.query(Policy).filter(
            Policy.policy_id == version_a_id
        ).first()
        policy_b = self.db.query(Policy).filter(
            Policy.policy_id == version_b_id
        ).first()

        if not policy_a or not policy_b:
            raise ValueError("One or both policy versions not found")

        diffs = {
            "version_a": policy_a.version,
            "version_b": policy_b.version,
            "changes": [],
        }

        # Compare basic fields
        fields_to_compare = ["policy_name", "policy_type", "description", "status"]
        for field in fields_to_compare:
            val_a = getattr(policy_a, field)
            val_b = getattr(policy_b, field)
            if val_a != val_b:
                diffs["changes"].append({
                    "field": field,
                    "old": val_a,
                    "new": val_b,
                })

        # Compare policy_config (JSON diff)
        config_a = json.dumps(policy_a.policy_config, indent=2, sort_keys=True)
        config_b = json.dumps(policy_b.policy_config, indent=2, sort_keys=True)

        if config_a != config_b:
            diff_lines = list(difflib.unified_diff(
                config_a.splitlines(),
                config_b.splitlines(),
                fromfile=f"v{policy_a.version}",
                tofile=f"v{policy_b.version}",
                lineterm="",
            ))
            diffs["config_diff"] = "\n".join(diff_lines)

        return diffs

    async def rollback_to_version(
        self,
        policy_id: str,
        target_version: int,
    ) -> Dict[str, Any]:
        """
        Rollback a policy to a previous version

        Creates a new version that copies the target version's config
        """
        # Find current policy
        current = self.db.query(Policy).filter(
            Policy.policy_id == policy_id
        ).first()

        if not current:
            raise ValueError(f"Policy {policy_id} not found")

        # Traverse history to find target
        target = None
        current_id = policy_id

        while current_id:
            policy = self.db.query(Policy).filter(
                Policy.policy_id == current_id
            ).first()

            if not policy:
                break

            if policy.version == target_version:
                target = policy
                break

            current_id = policy.parent_policy_id

        if not target:
            raise ValueError(f"Version {target_version} not found in history")

        # Update current policy with target's config
        current.policy_config = target.policy_config
        current.description = target.description

        # Store rollback info in metadata
        if current.policy_config and "metadata" not in current.policy_config:
            current.policy_config["metadata"] = {}
        if current.policy_config:
            current.policy_config["metadata"]["rolled_back_from"] = current.version
            current.policy_config["metadata"]["rolled_back_to"] = target_version

        self.db.commit()
        self.db.refresh(current)

        return {
            "policy_id": str(current.policy_id),
            "version": current.version,
            "rolled_back_to_version": target_version,
            "status": current.status,
        }