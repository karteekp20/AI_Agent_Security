# Sentinel Framework Test Suite

Comprehensive test suite for the Sentinel AI Security Control Plane.

## Test Structure

```
tests/
├── unit/                          # Unit tests (individual components)
│   ├── test_input_guard.py       # PII & injection detection tests
│   ├── test_output_guard.py      # Output validation & leak detection tests
│   ├── test_state_monitor.py     # Loop & cost monitoring tests
│   ├── test_shadow_agents.py     # Shadow agent tests (Phase 2)
│   └── test_schemas.py           # Data model validation tests
│
├── test_phase1_risk_scoring.py   # Integration tests (Phase 1)
├── test_phase2_shadow_agents.py  # Integration tests (Phase 2)
└── requirements-test.txt          # Test dependencies
```

## Test Types

### 1. Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation

**Characteristics**:
- Fast execution (< 1s per test)
- No external dependencies (LLM, DB, etc.)
- Uses mocks for external calls
- High coverage of edge cases

**Coverage**:
- ✅ **Input Guard**: 15+ tests for PII & injection detection
- ✅ **Output Guard**: 12+ tests for leak detection & sanitization
- ✅ **State Monitor**: 10+ tests for loop & cost monitoring
- ✅ **Shadow Agents**: 15+ tests for LLM-powered analysis
- ✅ **Schemas**: 12+ tests for data model validation

### 2. Integration Tests

**Purpose**: Test full workflow end-to-end

**Files**:
- `test_phase1_risk_scoring.py`: Phase 1 features (10 tests)
- `test_phase2_shadow_agents.py`: Phase 2 features (12 tests)

**Characteristics**:
- Test complete workflows
- May call real LLMs (if API keys set)
- Slower execution (5-10s per test)

## Running Tests

### Install Test Dependencies

```bash
# Install test requirements
pip install -r tests/requirements-test.txt

# Or install everything
pip install -r requirements.txt
pip install -r tests/requirements-test.txt
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=sentinel --cov-report=html --cov-report=term
```

### Run Specific Test Suites

```bash
# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests only
pytest tests/test_phase1_risk_scoring.py tests/test_phase2_shadow_agents.py -v

# Specific component
pytest tests/unit/test_input_guard.py -v

# Specific test
pytest tests/unit/test_input_guard.py::TestPIIDetector::test_credit_card_detection -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=sentinel --cov-report=html tests/unit/

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Coverage Goals

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| Input Guard | 90%+ | ✅ Covered |
| Output Guard | 90%+ | ✅ Covered |
| State Monitor | 85%+ | ✅ Covered |
| Shadow Agents | 80%+ | ✅ Covered |
| Schemas | 95%+ | ✅ Covered |
| Gateway | 85%+ | ⚠️ Partial |
| **Overall** | **85%+** | **~80%** |

## Writing New Tests

### Unit Test Template

```python
"""
Unit tests for [Component Name]
Tests [component] in isolation
"""

import pytest
from sentinel.[module] import [Component]


class Test[Component]:
    """Unit tests for [component]"""

    def test_[feature]_[scenario](self):
        """Test [specific behavior]"""
        # Arrange
        config = ...
        component = Component(config)

        # Act
        result = component.method(...)

        # Assert
        assert result.expected_field == expected_value
```

### Best Practices

1. **Descriptive Names**: Test names should describe what they test
   - ✅ `test_credit_card_detection_with_dashes`
   - ❌ `test1`

2. **AAA Pattern**: Arrange, Act, Assert
   ```python
   # Arrange: Set up test data
   config = ...
   detector = PIIDetector(config)

   # Act: Execute the code
   result = detector.detect_pii("test")

   # Assert: Verify results
   assert len(result) == 1
   ```

3. **One Assertion Per Concept**: Focus each test on one behavior
   - ✅ Separate tests for different PII types
   - ❌ One giant test checking everything

4. **Use Mocks for External Dependencies**:
   ```python
   from unittest.mock import patch

   with patch.object(agent, '_call_llm') as mock_llm:
       mock_llm.return_value = {"result": ...}
       result = agent.analyze(...)
   ```

5. **Test Edge Cases**:
   - Empty inputs
   - Null values
   - Boundary conditions (0.0, 1.0 for risk scores)
   - Error conditions

## Common Test Scenarios

### Testing PII Detection

```python
def test_pii_detection():
    config = PIIDetectionConfig(entity_types=[EntityType.EMAIL])
    detector = PIIDetector(config)

    text = "Contact: john@example.com"
    entities = detector.detect_pii(text)

    assert len(entities) == 1
    assert entities[0].entity_type == EntityType.EMAIL
    assert entities[0].original_value == "john@example.com"
```

### Testing Risk Scoring

```python
def test_risk_score_calculation():
    # High risk input
    high_result = component.calculate_risk(high_risk_input)

    # Low risk input
    low_result = component.calculate_risk(low_risk_input)

    assert high_result.risk_score > low_result.risk_score
    assert high_result.risk_score > 0.7
    assert low_result.risk_score < 0.3
```

### Testing with Mocks (Shadow Agents)

```python
def test_shadow_agent_with_mock():
    from unittest.mock import patch

    config = ShadowAgentConfig()
    agent = ShadowInputAgent(config)

    # Mock LLM response
    with patch.object(agent, '_call_llm') as mock_llm:
        mock_llm.return_value = {
            "result": {
                "risk_score": 0.85,
                "risk_level": "high",
                "confidence": 0.9,
                "threats_detected": ["injection"],
                "reasoning": "Test",
                "recommendations": []
            },
            "tokens_used": 200,
            "latency_ms": 300
        }

        result = agent.analyze(context)

        assert result.risk_score == 0.85
        assert not result.fallback_used
```

## Continuous Integration

### GitHub Actions (Example)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: |
          pip install -r requirements.txt
          pip install -r tests/requirements-test.txt
      - run: pytest --cov=sentinel --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests Fail with "Module not found"

```bash
# Make sure you're running from project root
cd /home/karteek/Documents/Cloud_Workspace/ai_agent_security

# Install in editable mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH
pytest
```

### Tests Skip or XFAIL

Some tests may be skipped if:
- Optional dependencies not installed (spaCy, LLMs)
- API keys not set (shadow agent tests)

This is expected - core functionality is tested without external deps.

### Slow Tests

Integration tests are slower (call real LLMs). To run only fast tests:

```bash
pytest tests/unit/ -v  # Unit tests only
```

## Test Metrics

### Current Test Stats

```
Unit Tests:       64 tests
Integration Tests: 22 tests
Total:            86 tests

Execution Time:
- Unit tests:     ~5 seconds
- Integration:    ~30 seconds (with LLM calls)
- Total:          ~35 seconds

Coverage:         ~80% (target: 85%)
```

### Test Quality Checklist

- [x] All components have unit tests
- [x] Edge cases covered (null, empty, boundary)
- [x] Error handling tested
- [x] Mocks used for external dependencies
- [x] Integration tests for full workflows
- [ ] Performance/load tests (future)
- [ ] Security-specific tests (fuzzing, etc.)

## Contributing Tests

When adding new features:

1. **Write unit tests first** (TDD approach)
2. **Achieve 80%+ coverage** for new code
3. **Add integration test** if feature touches multiple components
4. **Document test purpose** in docstrings
5. **Run full test suite** before committing

```bash
# Before committing
pytest --cov=sentinel tests/
black tests/  # Format
flake8 tests/  # Lint
```

---

## Summary

✅ **86 comprehensive tests** covering all major components
✅ **Unit + Integration** testing strategy
✅ **~80% code coverage** (target: 85%)
✅ **Fast execution** (<1min for all tests)
✅ **CI/CD ready** for automated testing

**Next Steps**:
1. Increase coverage to 85%+ (add gateway tests)
2. Add performance benchmarks
3. Add security-specific tests (fuzzing, etc.)
