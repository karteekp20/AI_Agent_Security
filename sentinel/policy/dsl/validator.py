"""DSL Policy Validator - Syntax and semantic validation"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue found in DSL code"""
    severity: ValidationSeverity
    message: str
    line: Optional[int] = None
    column: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }


class DSLValidator:
    """Validates DSL policy syntax and semantics"""

    VALID_ACTIONS: Set[str] = {"allow", "block", "log", "alert", "quarantine"}
    VALID_OPERATORS: Set[str] = {"==", "!=", ">", "<", ">=", "<=", "and", "or", "not", "in"}
    VALID_FUNCTIONS: Set[str] = {
        "contains", "matches", "length", "count", "risk_score",
        "starts_with", "ends_with", "in_list"
    }
    VALID_FIELDS: Set[str] = {
        "input", "input.text", "input.length", "input.tokens",
        "user", "user.id", "user.role", "user.email",
        "context", "context.ip", "context.timestamp", "context.user_agent",
        "risk_score", "threat_level", "anomaly_score",
        "request", "request.headers", "request.method",
    }

    def validate(self, dsl_source: str) -> List[ValidationIssue]:
        """Validate DSL source code"""
        issues = []

        if not dsl_source or not dsl_source.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Empty policy source"
            ))
            return issues

        # Syntax validation
        syntax_issues = self._validate_syntax(dsl_source)
        issues.extend(syntax_issues)

        if any(i.severity == ValidationSeverity.ERROR for i in syntax_issues):
            return issues  # Stop if syntax errors

        # Parse and semantic validation
        try:
            from .grammar import DSLParser
            parser = DSLParser()
            ast = parser.parse(dsl_source)

            if ast is None:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Failed to parse DSL source"
                ))
                return issues

            semantic_issues = self._validate_semantics(ast)
            issues.extend(semantic_issues)
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Parse error: {str(e)}"
            ))

        return issues

    def validate_ast(self, ast: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate a pre-parsed AST directly"""
        return self._validate_semantics(ast)

    def _validate_syntax(self, source: str) -> List[ValidationIssue]:
        """Basic syntax validation"""
        issues = []
        lines = source.split("\n")

        brace_count = 0
        paren_count = 0
        in_string = False
        string_char = None

        for line_num, line in enumerate(lines, 1):
            # Track string state to avoid counting braces in strings
            i = 0
            while i < len(line):
                char = line[i]

                # Handle string delimiters
                if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None

                # Count braces and parens only outside strings
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                    elif char == '(':
                        paren_count += 1
                    elif char == ')':
                        paren_count -= 1

                i += 1

            # Check for common errors
            stripped = line.strip()
            if stripped.startswith("rule") and "{" not in line and not stripped.endswith("{"):
                # Check if rule continues on next line
                if line_num < len(lines):
                    next_line = lines[line_num].strip() if line_num < len(lines) else ""
                    if not next_line.startswith("{"):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message="Rule declaration should be followed by opening brace",
                            line=line_num
                        ))

        if brace_count > 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Missing {brace_count} closing brace(s)"
            ))
        elif brace_count < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Found {-brace_count} extra closing brace(s)"
            ))

        if paren_count > 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Missing {paren_count} closing parenthesis(es)"
            ))
        elif paren_count < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Found {-paren_count} extra closing parenthesis(es)"
            ))

        return issues

    def _validate_semantics(self, ast: Dict[str, Any]) -> List[ValidationIssue]:
        """Semantic validation of parsed AST"""
        issues = []

        rules = ast.get("rules", [])

        if not rules:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="Policy contains no rules"
            ))
            return issues

        rule_names = set()
        for rule in rules:
            # Validate rule name uniqueness
            name = rule.get("name", "unnamed")
            if name in rule_names:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate rule name: '{name}'"
                ))
            rule_names.add(name)

            # Validate action
            action = rule.get("action")
            if action and action not in self.VALID_ACTIONS:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid action '{action}'. Valid actions: {', '.join(sorted(self.VALID_ACTIONS))}"
                ))

            # Validate conditions
            condition_issues = self._validate_condition(rule.get("condition", {}))
            issues.extend(condition_issues)

        return issues

    def _validate_condition(self, condition: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate a condition recursively"""
        issues = []

        if not condition:
            return issues

        op = condition.get("op")

        if op in ("and", "or"):
            conditions = condition.get("conditions", [])
            if len(conditions) < 2:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"'{op}' operator should have at least 2 conditions"
                ))
            for sub in conditions:
                issues.extend(self._validate_condition(sub))

        elif op == "not":
            sub = condition.get("condition", {})
            if not sub:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="'not' operator requires a condition"
                ))
            else:
                issues.extend(self._validate_condition(sub))

        elif op == "call":
            fn = condition.get("function")
            if fn not in self.VALID_FUNCTIONS:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Unknown function '{fn}'. Valid functions: {', '.join(sorted(self.VALID_FUNCTIONS))}"
                ))

            # Validate function arguments
            args = condition.get("args", [])
            issues.extend(self._validate_function_args(fn, args))

        elif op in self.VALID_OPERATORS:
            # Validate comparison operands
            left = condition.get("left")
            right = condition.get("right")
            if left is not None:
                issues.extend(self._validate_value(left))
            if right is not None:
                issues.extend(self._validate_value(right))

        return issues

    def _validate_value(self, value: Any) -> List[ValidationIssue]:
        """Validate a value reference"""
        issues = []

        if isinstance(value, dict):
            if value.get("type") == "field":
                path = value.get("path", "")
                # Warn about unknown fields but don't error
                # (custom fields may be added at runtime)
                root_field = path.split(".")[0] if path else ""
                known_roots = {"input", "user", "context", "request", "risk_score", "threat_level", "anomaly_score"}
                if root_field and root_field not in known_roots:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Unknown field root '{root_field}' - ensure it exists in context"
                    ))

        return issues

    def _validate_function_args(self, fn: str, args: List[Any]) -> List[ValidationIssue]:
        """Validate function arguments"""
        issues = []

        # Define expected arg counts for functions
        expected_args = {
            "contains": 2,
            "matches": 2,
            "length": 1,
            "count": 1,
            "risk_score": 1,
            "starts_with": 2,
            "ends_with": 2,
            "in_list": 2,
        }

        if fn in expected_args:
            expected = expected_args[fn]
            actual = len(args)
            if actual != expected:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Function '{fn}' expects {expected} argument(s), got {actual}"
                ))

        return issues
