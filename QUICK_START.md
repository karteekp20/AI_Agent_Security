# Sentinel Agentic Framework - Quick Start Guide

Get started with Sentinel in 5 minutes.

> **📐 For complete architecture details, see [ARCHITECTURE_ENHANCED.md](ARCHITECTURE_ENHANCED.md)**

## What is Sentinel?

Sentinel is a **Zero-Trust AI Security Control Plane** that sits between your users and AI agents, providing:
- 🛡️ **PII/PCI/PHI Protection** - Auto-detect and redact sensitive data
- 🚫 **Prompt Injection Blocking** - Stop jailbreaks and attacks
- ♻️ **Loop Detection** - Prevent infinite loops and token waste
- 🔴 **Red Team Testing** - Find vulnerabilities before attackers do
- ✅ **Compliance** - PCI-DSS, GDPR, HIPAA, SOC2 ready

## Installation

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Minimal Example

```python
from sentinel import SentinelGateway, SentinelConfig

# 1. Configure
config = SentinelConfig()

# 2. Create Gateway
gateway = SentinelGateway(config)

# 3. Define Your Agent
def my_agent(user_input: str) -> str:
    return f"Processing: {user_input}"

# 4. Protect Your Agent
result = gateway.invoke(
    user_input="My credit card is 4532-1234-5678-9010",
    agent_executor=my_agent
)

# 5. Use the Result
print(result["response"])  # PII automatically redacted
print(f"Blocked: {result['blocked']}")
print(f"Threats: {len(result['threats'])}")
```

## Common Configurations

### PCI-DSS Compliance (E-Commerce)

```python
from sentinel import SentinelConfig, ComplianceFramework, EntityType

config = SentinelConfig()
config.pii_detection.entity_types = [
    EntityType.CREDIT_CARD,
    EntityType.CVV,
]
config.compliance.frameworks = [ComplianceFramework.PCI_DSS]
```

### HIPAA Compliance (Healthcare)

```python
config = SentinelConfig()
config.pii_detection.entity_types = [
    EntityType.MEDICAL_RECORD_NUMBER,
    EntityType.SSN,
    EntityType.PERSON_NAME,
]
config.compliance.frameworks = [ComplianceFramework.HIPAA]
```

### Secret Detection (Developer Tools)

```python
config = SentinelConfig()
config.pii_detection.entity_types = [
    EntityType.API_KEY,
    EntityType.PASSWORD,
    EntityType.JWT_TOKEN,
    EntityType.AWS_KEY,
]
```

## LangChain Integration

```python
from langchain_anthropic import ChatAnthropic
from sentinel import SentinelGateway, SentinelConfig

# Your LangChain setup
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# Wrap with Sentinel
config = SentinelConfig()
gateway = SentinelGateway(config)

def protected_langchain_agent(user_input: str):
    def execute(sanitized_input: str):
        return llm.invoke(sanitized_input).content

    return gateway.invoke(user_input, execute)

# Use it
result = protected_langchain_agent("Hello, my SSN is 123-45-6789")
print(result["response"])  # SSN redacted
```

## Decorator Pattern

```python
from sentinel import SentinelMiddleware, SentinelConfig

config = SentinelConfig()
sentinel = SentinelMiddleware(config)

@sentinel
def my_agent(user_input: str) -> str:
    return f"Response: {user_input}"

result = my_agent("Test input")
```

## Check Results

```python
result = gateway.invoke(user_input, agent_executor)

# Response
if not result["blocked"]:
    print(result["response"])
else:
    print(f"Blocked: {result['block_reason']}")

# Security
for threat in result["threats"]:
    print(f"⚠️  {threat['description']}")

# Compliance
if result["violations"]:
    print("❌ Compliance violations found")
    for v in result["violations"]:
        print(f"   [{v['framework']}] {v['description']}")

# Audit
print(f"Session ID: {result['audit_log']['session_id']}")
print(f"PII Redacted: {result['audit_log']['pii_redactions']}")
```

## Generate Reports

```python
# JSON Report
json_report = gateway.generate_report(result, format="json")

# Summary Report
summary = gateway.generate_report(result, format="summary")
print(summary)
```

## Next Steps

1. **Customize Detection**: Configure which PII types to detect
2. **Enable Red Team**: Test your agent for vulnerabilities
3. **Set Up Compliance**: Choose relevant frameworks
4. **Deploy**: See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)

## Configuration Reference

### Entity Types
- `CREDIT_CARD`, `SSN`, `EMAIL`, `PHONE`
- `MEDICAL_RECORD_NUMBER`, `HEALTH_PLAN_NUMBER`
- `API_KEY`, `PASSWORD`, `JWT_TOKEN`, `AWS_KEY`

### Redaction Strategies
- `MASK`: Partial masking (e.g., "****-1234")
- `TOKEN`: Replace with token (e.g., "[REDACTED_001]")
- `HASH`: SHA256 hash
- `ENCRYPT`: Encrypt and store

### Compliance Frameworks
- `PCI_DSS`: Payment Card Industry
- `GDPR`: EU Data Protection
- `HIPAA`: Healthcare Privacy
- `SOC2`: Security Controls
- `CCPA`: California Privacy

## Troubleshooting

**PII not detected?**
```python
# Lower the threshold
config.pii_detection.confidence_threshold = 0.6

# Enable more detection methods
config.pii_detection.use_ner = True
config.pii_detection.use_regex = True
```

**Too many false positives?**
```python
# Raise the threshold
config.pii_detection.confidence_threshold = 0.9

# Limit to specific entity types
config.pii_detection.entity_types = [EntityType.CREDIT_CARD]
```

**Need faster performance?**
```python
# Disable Red Team in production
config.red_team.enabled = False

# Limit entity types
config.pii_detection.entity_types = [EntityType.CREDIT_CARD, EntityType.SSN]
```

## Examples

See [examples/](examples/) directory:
- `basic_usage.py`: 8 comprehensive examples
- `langchain_integration.py`: LangChain integration patterns

## Documentation

- [README.md](README.md) - Full documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Deep dive

## Support

- **GitHub Issues**: Report bugs or request features
- **Email**: security@sentinel.ai
- **Docs**: https://sentinel-docs.example.com
