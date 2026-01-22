"""DSL Policy Evaluator - Execute parsed policy AST"""

from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
import re


class PolicyAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    LOG = "log"
    ALERT = "alert"
    QUARANTINE = "quarantine"


@dataclass
class EvaluationResult:
    """Result of policy evaluation"""
    action: PolicyAction
    matched_rules: List[str]
    context: Dict[str, Any]


class DSLEvaluator:
    """Evaluates parsed DSL policies against request context"""

    def __init__(self):
        self.functions: Dict[str, Callable] = {
            "contains": self._fn_contains,
            "matches": self._fn_matches,
            "length": self._fn_length,
            "count": self._fn_count,
            "risk_score": self._fn_risk_score,
            "starts_with": self._fn_starts_with,
            "ends_with": self._fn_ends_with,
            "in_list": self._fn_in_list,
        }

    def evaluate(self, ast: Dict[str, Any], context: Dict[str, Any]) -> EvaluationResult:
        """Evaluate a policy AST against request context"""
        matched_rules = []
        final_action = PolicyAction.ALLOW

        for rule in ast.get("rules", []):
            if self._evaluate_condition(rule.get("condition", {}), context):
                matched_rules.append(rule.get("name", "unnamed"))
                action = PolicyAction(rule.get("action", "log"))

                # Block takes precedence over all
                if action == PolicyAction.BLOCK:
                    final_action = PolicyAction.BLOCK
                # Quarantine next
                elif action == PolicyAction.QUARANTINE and final_action not in (PolicyAction.BLOCK,):
                    final_action = PolicyAction.QUARANTINE
                # Alert takes precedence over Log
                elif action == PolicyAction.ALERT and final_action not in (PolicyAction.BLOCK, PolicyAction.QUARANTINE):
                    final_action = PolicyAction.ALERT
                # Log is lowest priority
                elif action == PolicyAction.LOG and final_action == PolicyAction.ALLOW:
                    final_action = PolicyAction.LOG

        return EvaluationResult(
            action=final_action,
            matched_rules=matched_rules,
            context=context
        )

    def _evaluate_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Recursively evaluate a condition"""
        op = condition.get("op")

        if op == "and":
            return all(self._evaluate_condition(c, context) for c in condition.get("conditions", []))
        elif op == "or":
            return any(self._evaluate_condition(c, context) for c in condition.get("conditions", []))
        elif op == "not":
            return not self._evaluate_condition(condition.get("condition", {}), context)
        elif op in ("==", "!=", ">", "<", ">=", "<="):
            left = self._resolve_value(condition.get("left"), context)
            right = self._resolve_value(condition.get("right"), context)
            return self._compare(left, op, right)
        elif op == "call":
            fn_name = condition.get("function")
            args = [self._resolve_value(a, context) for a in condition.get("args", [])]
            return self._call_function(fn_name, args)
        elif op == "in":
            item = self._resolve_value(condition.get("item"), context)
            collection = self._resolve_value(condition.get("collection"), context)
            if collection is None:
                return False
            return item in collection

        return False

    def _resolve_value(self, value: Any, context: Dict[str, Any]) -> Any:
        """Resolve a value from context or return literal"""
        if isinstance(value, dict):
            if value.get("type") == "field":
                return self._get_nested(context, value.get("path", ""))
            elif value.get("type") == "literal":
                return value.get("value")
        return value

    def _get_nested(self, obj: Dict, path: str) -> Any:
        """Get nested value from dict using dot notation"""
        if not path:
            return None
        for key in path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return None
        return obj

    def _compare(self, left: Any, op: str, right: Any) -> bool:
        """Perform comparison"""
        if left is None or right is None:
            # Special case: checking for None
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            return False
        try:
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == ">":
                return left > right
            if op == "<":
                return left < right
            if op == ">=":
                return left >= right
            if op == "<=":
                return left <= right
        except TypeError:
            return False
        return False

    def _call_function(self, name: str, args: List[Any]) -> Any:
        """Call a built-in function"""
        fn = self.functions.get(name)
        if fn:
            try:
                return fn(*args)
            except (TypeError, ValueError):
                return False
        return False

    # Built-in functions
    def _fn_contains(self, haystack: str, needle: str) -> bool:
        """Check if haystack contains needle (case-insensitive)"""
        if haystack is None:
            return False
        return needle.lower() in str(haystack).lower()

    def _fn_matches(self, text: str, pattern: str) -> bool:
        """Check if text matches regex pattern"""
        if text is None:
            return False
        try:
            return bool(re.search(pattern, str(text)))
        except re.error:
            return False

    def _fn_length(self, value: Any) -> int:
        """Get length of value"""
        if value is None:
            return 0
        try:
            return len(value)
        except TypeError:
            return 0

    def _fn_count(self, items: List) -> int:
        """Count items in a list"""
        if items is None:
            return 0
        try:
            return len(items)
        except TypeError:
            return 0

    def _fn_risk_score(self, context: Dict) -> float:
        """Get risk score from context"""
        if isinstance(context, dict):
            return float(context.get("risk_score", 0.0))
        return 0.0

    def _fn_starts_with(self, text: str, prefix: str) -> bool:
        """Check if text starts with prefix"""
        if text is None:
            return False
        return str(text).lower().startswith(prefix.lower())

    def _fn_ends_with(self, text: str, suffix: str) -> bool:
        """Check if text ends with suffix"""
        if text is None:
            return False
        return str(text).lower().endswith(suffix.lower())

    def _fn_in_list(self, item: Any, items: List) -> bool:
        """Check if item is in list"""
        if items is None:
            return False
        return item in items
