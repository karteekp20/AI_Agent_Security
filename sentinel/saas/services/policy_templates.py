from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.orm import Session


# Built-in templates
BUILTIN_TEMPLATES = [
    {
        "template_id": "tpl_pii_basic",
        "name": "Basic PII Protection",
        "description": "Blocks requests containing common PII (SSN, credit cards, emails)",
        "category": "pii",
        "policy_type": "pii_pattern",
        "policy_config": {
            "patterns": ["ssn", "credit_card", "email", "phone"],
            "action": "block",
            "threshold": 0.8,
        },
        "variables": {
            "threshold": {
                "type": "float",
                "default": 0.8,
                "description": "Confidence threshold for detection",
            },
            "action": {
                "type": "enum",
                "options": ["block", "warn", "log"],
                "default": "block",
            },
        },
    },
    {
        "template_id": "tpl_injection_strict",
        "name": "Strict Injection Prevention",
        "description": "Aggressive detection of prompt injection attempts",
        "category": "injection",
        "policy_type": "injection_rule",
        "policy_config": {
            "patterns": [
                r"ignore\s+(previous|all)\s+instructions",
                r"(you\s+are|act\s+as)\s+a\s+",
                r"disregard\s+.*\s+rules",
                r"system:\s*",
            ],
            "action": "block",
            "case_sensitive": False,
        },
        "variables": {
            "action": {
                "type": "enum",
                "options": ["block", "warn"],
                "default": "block",
            },
        },
    },
    {
        "template_id": "tpl_rate_limit",
        "name": "Request Rate Limiting",
        "description": "Limit requests per user per time window",
        "category": "rate_limit",
        "policy_type": "custom_filter",
        "policy_config": {
            "type": "rate_limit",
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "burst_limit": 10,
        },
        "variables": {
            "requests_per_minute": {
                "type": "int",
                "default": 60,
                "min": 1,
                "max": 1000,
            },
            "requests_per_hour": {
                "type": "int",
                "default": 1000,
                "min": 1,
                "max": 10000,
            },
        },
    },
    {
        "template_id": "tpl_content_safety",
        "name": "Content Safety Filter",
        "description": "Block harmful, violent, or inappropriate content",
        "category": "content_moderation",
        "policy_type": "content_moderation",
        "policy_config": {
            "categories": ["violence", "hate_speech", "adult_content", "self_harm"],
            "threshold": 0.7,
            "action": "block",
        },
        "variables": {
            "categories": {
                "type": "multi_select",
                "options": ["violence", "hate_speech", "adult_content", "self_harm", "spam"],
                "default": ["violence", "hate_speech"],
            },
            "threshold": {
                "type": "float",
                "default": 0.7,
                "min": 0.5,
                "max": 1.0,
            },
        },
    },
    {
        "template_id": "tpl_hipaa_compliant",
        "name": "HIPAA Compliance",
        "description": "Detect and protect PHI (Protected Health Information)",
        "category": "compliance",
        "policy_type": "pii_pattern",
        "policy_config": {
            "patterns": ["medical_record", "diagnosis", "treatment", "patient_id"],
            "action": "block",
            "logging": {
                "enabled": True,
                "redact_pii": True,
            },
        },
        "compliance_frameworks": ["HIPAA"],
        "variables": {
            "action": {
                "type": "enum",
                "options": ["block", "redact"],
                "default": "block",
                "description": "Action to take on PHI detection",
            },
            "logging_enabled": {
                "type": "enum",
                "options": ["true", "false"],
                "default": "true",
                "description": "Enable audit logging for PHI events",
            },
        },
    },
    {
        "template_id": "tpl_gdpr_compliant",
        "name": "GDPR Compliance",
        "description": "Enforce GDPR requirements for EU user data protection",
        "category": "compliance",
        "policy_type": "pii_pattern",
        "policy_config": {
            "patterns": ["email", "phone", "address", "id_number", "ip_address"],
            "action": "redact",
            "consent_required": True,
            "data_retention_days": 30,
        },
        "compliance_frameworks": ["GDPR"],
        "variables": {
            "action": {
                "type": "enum",
                "options": ["block", "redact"],
                "default": "redact",
                "description": "Action to take on personal data detection",
            },
            "retention_days": {
                "type": "int",
                "default": 30,
                "min": 1,
                "max": 365,
                "description": "Days to retain personal data (GDPR compliance)",
            },
        },
    },
    {
        "template_id": "tpl_pci_dss_compliant",
        "name": "PCI-DSS Compliance",
        "description": "Protect payment card and cardholder data",
        "category": "compliance",
        "policy_type": "pii_pattern",
        "policy_config": {
            "patterns": ["credit_card", "cvv", "pin", "card_number", "expiry_date"],
            "action": "block",
            "encryption_required": True,
            "tokenization": True,
        },
        "compliance_frameworks": ["PCI-DSS"],
        "variables": {
            "action": {
                "type": "enum",
                "options": ["block"],
                "default": "block",
                "description": "Must block card data (PCI requirement)",
            },
            "encryption": {
                "type": "enum",
                "options": ["AES-256", "AES-128"],
                "default": "AES-256",
                "description": "Encryption algorithm for card data at rest",
            },
        },
    },
    {
        "template_id": "tpl_soc2_compliant",
        "name": "SOC2 Compliance",
        "description": "Ensure SOC2 security, availability, and confidentiality controls",
        "category": "compliance",
        "policy_type": "pii_pattern",
        "policy_config": {
            "patterns": ["password", "api_key", "secret", "token", "credential"],
            "action": "block",
            "audit_logging": True,
            "access_control": True,
        },
        "compliance_frameworks": ["SOC2"],
        "variables": {
            "action": {
                "type": "enum",
                "options": ["block", "redact"],
                "default": "block",
                "description": "Action to take on sensitive credential detection",
            },
            "audit_all_access": {
                "type": "enum",
                "options": ["true", "false"],
                "default": "true",
                "description": "Audit all access attempts to sensitive data",
            },
        },
    },
]


class PolicyTemplateService:
    """
    Service for managing policy templates

    Templates provide pre-configured policies that users can
    quickly apply with optional customization.
    """

    def __init__(self, db: Session):
        self.db = db
        self._templates = {t["template_id"]: t for t in BUILTIN_TEMPLATES}

    def list_templates(
        self,
        category: Optional[str] = None,
        compliance_framework: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List available templates

        Args:
            category: Filter by category (pii, injection, etc.)
            compliance_framework: Filter by compliance (HIPAA, GDPR, etc.)
        """
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.get("category") == category]

        if compliance_framework:
            templates = [
                t for t in templates
                if compliance_framework in t.get("compliance_frameworks", [])
            ]

        return templates

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID"""
        return self._templates.get(template_id)

    def instantiate_template(
        self,
        template_id: str,
        org_id: UUID,
        policy_name: str,
        variable_values: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Create a new policy from a template

        Args:
            template_id: Template to instantiate
            org_id: Organization creating the policy
            policy_name: Name for the new policy
            variable_values: Custom values for template variables
            created_by: User creating the policy
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Start with template config
        policy_config = template["policy_config"].copy()

        # Apply variable overrides
        if variable_values:
            for var_name, var_value in variable_values.items():
                var_spec = template.get("variables", {}).get(var_name)
                if var_spec:
                    # Validate value
                    if not self._validate_variable(var_spec, var_value):
                        raise ValueError(f"Invalid value for variable {var_name}")
                    # Apply to config
                    policy_config[var_name] = var_value

        # Create policy data
        return {
            "policy_id": str(uuid4()),
            "org_id": str(org_id),
            "policy_name": policy_name,
            "policy_type": template["policy_type"],
            "description": template["description"],
            "policy_config": policy_config,
            "template_id": template_id,
            "status": "draft",
            "version": 1,
            "created_by": str(created_by) if created_by else None,
            "created_at": datetime.utcnow().isoformat(),
        }

    def _validate_variable(
        self,
        spec: Dict[str, Any],
        value: Any
    ) -> bool:
        """Validate a variable value against its spec"""
        var_type = spec.get("type")

        if var_type == "int":
            if not isinstance(value, int):
                return False
            if "min" in spec and value < spec["min"]:
                return False
            if "max" in spec and value > spec["max"]:
                return False

        elif var_type == "float":
            if not isinstance(value, (int, float)):
                return False
            if "min" in spec and value < spec["min"]:
                return False
            if "max" in spec and value > spec["max"]:
                return False

        elif var_type == "enum":
            if value not in spec.get("options", []):
                return False

        elif var_type == "multi_select":
            if not isinstance(value, list):
                return False
            if not all(v in spec.get("options", []) for v in value):
                return False

        return True