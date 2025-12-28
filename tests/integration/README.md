# Integration Tests

Comprehensive integration tests for the Sentinel AI Security Control Plane.

## Overview

This directory contains end-to-end integration tests that validate the complete system working together:

- **API Integration** (`test_api_integration.py`) - Tests all API endpoints with all security layers
- **Storage Integration** (`test_storage_integration.py`) - Tests Redis and PostgreSQL adapters
- **Observability Integration** (`test_observability_integration.py`) - Tests metrics, tracing, and logging
- **Performance Benchmarks** (`test_performance.py`) - Latency, throughput, and scalability tests

## Quick Start

### Running All Tests

```bash
# From project root
cd /home/karteek/Documents/Cloud_Workspace/ai_agent_security

# Activate virtual environment
source venv/bin/activate

# Run all integration tests
./run_integration_tests.sh
```

### Running Specific Test Suites

```bash
# API tests only
./run_integration_tests.sh api

# Storage tests only
./run_integration_tests.sh storage

# Observability tests only
./run_integration_tests.sh observability

# Performance benchmarks
./run_integration_tests.sh performance

# Fast tests (skip slow/performance)
./run_integration_tests.sh fast
```

### Running with pytest directly

```bash
# All integration tests
pytest tests/integration/ -v

# Specific test file
pytest tests/integration/test_api_integration.py -v

# Specific test class
pytest tests/integration/test_api_integration.py::TestProcessEndpoint -v

# Specific test method
pytest tests/integration/test_api_integration.py::TestProcessEndpoint::test_clean_input_allowed -v

# Run only performance tests
pytest tests/integration/ -v -m performance

# Skip slow tests
pytest tests/integration/ -v -m "not slow"

# With coverage
pytest tests/integration/ -v --cov=sentinel --cov-report=html
```

## Test Categories

### API Integration Tests

**File:** `test_api_integration.py`

Tests the complete API with all security layers:

- ✅ Health and readiness checks
- ✅ Clean input processing (low risk)
- ✅ PII detection and redaction
- ✅ Prompt injection detection and blocking
- ✅ SQL injection detection
- ✅ Session tracking
- ✅ Rate limiting enforcement
- ✅ Metrics collection
- ✅ End-to-end security scenarios
- ✅ Error handling

**Run:**
```bash
pytest tests/integration/test_api_integration.py -v
```

### Storage Integration Tests

**File:** `test_storage_integration.py`

Tests data persistence and caching:

- ✅ Redis session state management
- ✅ Redis pattern caching
- ✅ Redis rate limiting
- ✅ PostgreSQL audit log storage
- ✅ PostgreSQL query operations
- ✅ Connection failure handling
- ✅ Real storage roundtrips (with `@pytest.mark.integration`)

**Run:**
```bash
pytest tests/integration/test_storage_integration.py -v

# With real Redis/PostgreSQL (requires services running)
pytest tests/integration/test_storage_integration.py -v -m integration
```

### Observability Integration Tests

**File:** `test_observability_integration.py`

Tests monitoring and observability:

- ✅ Prometheus metrics collection
- ✅ OpenTelemetry distributed tracing
- ✅ Structured JSON logging
- ✅ Security event logging
- ✅ End-to-end observability pipeline
- ✅ Metrics accumulation
- ✅ Trace correlation

**Run:**
```bash
pytest tests/integration/test_observability_integration.py -v
```

### Performance Benchmarks

**File:** `test_performance.py`

Performance and scalability tests:

- ✅ Latency benchmarks (P50, P95, P99)
- ✅ Throughput measurements
- ✅ Concurrent request handling
- ✅ Scalability with varying input sizes
- ✅ Sustained load testing
- ✅ Memory leak detection
- ✅ Component-level performance

**Run:**
```bash
pytest tests/integration/test_performance.py -v -m performance
```

**Example Output:**
```
📊 Clean Input Latency:
  P50 (Median): 85.23ms
  P95: 142.67ms
  P99: 198.45ms
  Mean: 92.15ms

📊 Sequential Throughput:
  Requests: 1000
  Duration: 45.23s
  Throughput: 22.11 req/s
```

## Prerequisites

### Basic Tests (No External Services)

```bash
pip install -r requirements.txt
```

### Integration Tests (Real Services)

These tests require Redis and PostgreSQL running:

```bash
# Start services with Docker Compose
docker-compose -f docker/docker-compose.yml up -d redis postgres

# Or manually start services
# Redis: docker run -d -p 6379:6379 redis:7-alpine
# PostgreSQL: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=sentinel_password postgres:15
```

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.integration` - Requires real Redis/PostgreSQL
- `@pytest.mark.slow` - Takes longer than 10 seconds
- `@pytest.mark.performance` - Performance benchmarks

### Running by Marker

```bash
# Only integration tests (with real services)
pytest tests/integration/ -v -m integration

# Skip slow tests
pytest tests/integration/ -v -m "not slow"

# Only performance tests
pytest tests/integration/ -v -m performance

# Fast tests only (no slow, no performance)
pytest tests/integration/ -v -m "not slow and not performance"
```

## Configuration

Tests use environment variables for configuration. See `conftest.py` for defaults.

### Key Environment Variables

```bash
# Disable external services (default for unit tests)
export REDIS_ENABLED=false
export POSTGRES_ENABLED=false
export ENABLE_TRACING=false

# Enable for integration tests
export REDIS_ENABLED=true
export POSTGRES_ENABLED=true
export REDIS_HOST=localhost
export POSTGRES_HOST=localhost
```

## Coverage Report

Generate HTML coverage report:

```bash
./run_integration_tests.sh coverage

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: sentinel_test
          POSTGRES_USER: sentinel_user
          POSTGRES_PASSWORD: sentinel_password
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          python -m spacy download en_core_web_sm

      - name: Run integration tests
        run: |
          export REDIS_ENABLED=true
          export POSTGRES_ENABLED=true
          ./run_integration_tests.sh all

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        if: success()
```

## Troubleshooting

### Tests Skipped

If you see tests being skipped:

```
tests/integration/test_storage_integration.py::TestRealStorageIntegration::test_redis_roundtrip SKIPPED (Redis not available)
```

**Solution:** Start the required services:
```bash
docker-compose -f docker/docker-compose.yml up -d redis postgres
```

### Connection Errors

```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution:** Ensure Redis is running and accessible:
```bash
redis-cli ping  # Should return "PONG"
```

### Import Errors

```
ModuleNotFoundError: No module named 'sentinel'
```

**Solution:** Install the package in editable mode:
```bash
pip install -e .
```

### Slow Tests

If tests are running slowly:

```bash
# Skip slow tests
./run_integration_tests.sh fast

# Or with pytest
pytest tests/integration/ -v -m "not slow and not performance"
```

## Writing New Tests

### Template for New Test File

```python
"""
Description of what this test file validates
"""

import pytest
from fastapi.testclient import TestClient


class TestYourFeature:
    """Test description"""

    @pytest.fixture
    def setup_data(self):
        """Setup test data"""
        return {...}

    def test_basic_functionality(self, client, setup_data):
        """Test basic functionality"""
        response = client.post("/endpoint", json=setup_data)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_with_real_services(self, real_redis_adapter):
        """Test with real external services"""
        # This test only runs when services are available
        pass
```

### Best Practices

1. **Use descriptive test names** - `test_pii_detection_and_redaction` not `test_1`
2. **One assertion per test** - Or closely related assertions
3. **Use fixtures** - For setup/teardown and shared data
4. **Mark appropriately** - Use `@pytest.mark.integration`, `@pytest.mark.slow`
5. **Clean up** - Ensure tests don't affect each other
6. **Test edge cases** - Empty input, very long input, special characters
7. **Test error paths** - Not just happy path

## Expected Results

### Success Criteria

All integration tests should pass with:

- ✅ 100% test pass rate
- ✅ No skipped tests (if services available)
- ✅ Clean input: P50 < 200ms, P95 < 400ms
- ✅ PII detection: Working and redacting correctly
- ✅ Injection detection: Blocking malicious inputs
- ✅ Rate limiting: Enforcing limits correctly
- ✅ Metrics: Being collected on all requests
- ✅ Throughput: > 10 req/s sequential, > 20 req/s concurrent

### Sample Output

```
========================================
  Sentinel Integration Test Suite
========================================

Checking service availability...

✓ Redis available (localhost:6379)
✓ PostgreSQL available (localhost:5432)
✓ API server running (localhost:8000)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: All Integration Tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tests/integration/test_api_integration.py::TestHealthEndpoints::test_health_check PASSED
tests/integration/test_api_integration.py::TestProcessEndpoint::test_clean_input_allowed PASSED
tests/integration/test_api_integration.py::TestProcessEndpoint::test_pii_detection_and_redaction PASSED
tests/integration/test_api_integration.py::TestProcessEndpoint::test_prompt_injection_blocked PASSED
...

========================================
✓ Test suite completed successfully!
========================================
```

## Support

For issues or questions:

1. Check the [Production Deployment Guide](../../PRODUCTION_DEPLOYMENT_GUIDE.md)
2. Review the [Phase 4 Completion Summary](../../PHASE_4_COMPLETION_SUMMARY.md)
3. Open an issue with:
   - Test command used
   - Full error output
   - Environment details (OS, Python version, service versions)
