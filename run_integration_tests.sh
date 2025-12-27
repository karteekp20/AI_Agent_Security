#!/bin/bash

# Integration Test Runner for Sentinel AI Security Control Plane
# Runs comprehensive integration tests with different configurations

set -e

echo "=========================================="
echo "  Sentinel Integration Test Suite"
echo "=========================================="
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated!"
    echo "   Run: source venv/bin/activate"
    exit 1
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to run tests with specific markers
run_tests() {
    local name=$1
    local marker=$2
    local extra_args="${3:-}"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}Running: $name${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [[ -n "$marker" ]]; then
        pytest tests/integration/ -v -m "$marker" $extra_args
    else
        pytest tests/integration/ -v $extra_args
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $name passed${NC}"
    else
        echo -e "${RED}✗ $name failed${NC}"
        exit 1
    fi
}

# Check service availability
check_services() {
    echo "Checking service availability..."
    echo ""

    # Check Redis
    if nc -z localhost 6379 2>/dev/null; then
        echo -e "${GREEN}✓ Redis available (localhost:6379)${NC}"
        REDIS_AVAILABLE=true
    else
        echo -e "${YELLOW}⚠ Redis not available - integration tests will be skipped${NC}"
        REDIS_AVAILABLE=false
    fi

    # Check PostgreSQL
    if nc -z localhost 5432 2>/dev/null; then
        echo -e "${GREEN}✓ PostgreSQL available (localhost:5432)${NC}"
        POSTGRES_AVAILABLE=true
    else
        echo -e "${YELLOW}⚠ PostgreSQL not available - integration tests will be skipped${NC}"
        POSTGRES_AVAILABLE=false
    fi

    # Check if API server is running
    if nc -z localhost 8000 2>/dev/null; then
        echo -e "${GREEN}✓ API server running (localhost:8000)${NC}"
        API_RUNNING=true
    else
        echo -e "${YELLOW}⚠ API server not running - some tests may fail${NC}"
        echo "   To start: python -m uvicorn sentinel.api.server:app --reload"
        API_RUNNING=false
    fi

    echo ""
}

# Main test execution
case "$TEST_TYPE" in
    "all")
        echo "Running ALL integration tests"
        check_services
        run_tests "All Integration Tests" "" "--tb=short"
        ;;

    "api")
        echo "Running API integration tests"
        run_tests "API Integration Tests" "" "-k test_api_integration --tb=short"
        ;;

    "storage")
        echo "Running storage integration tests"
        check_services
        run_tests "Storage Integration Tests" "" "-k test_storage_integration --tb=short"
        ;;

    "observability")
        echo "Running observability integration tests"
        run_tests "Observability Tests" "" "-k test_observability_integration --tb=short"
        ;;

    "performance")
        echo "Running performance benchmarks"
        echo "⚠️  This may take several minutes..."
        run_tests "Performance Benchmarks" "performance" "--tb=short"
        ;;

    "integration-only")
        echo "Running integration tests with real services"
        check_services
        if [[ "$REDIS_AVAILABLE" != true ]] || [[ "$POSTGRES_AVAILABLE" != true ]]; then
            echo -e "${RED}✗ Redis and PostgreSQL required for integration tests${NC}"
            echo "  Start services with: docker-compose -f docker/docker-compose.yml up -d redis postgres"
            exit 1
        fi
        run_tests "Integration Tests (Real Services)" "integration" "--tb=short"
        ;;

    "fast")
        echo "Running fast tests only (no slow/performance tests)"
        run_tests "Fast Tests" "" "-m 'not slow and not performance' --tb=short"
        ;;

    "coverage")
        echo "Running tests with coverage report"
        pytest tests/integration/ -v --cov=sentinel --cov-report=html --cov-report=term --tb=short
        echo ""
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    "debug")
        echo "Running tests in debug mode"
        run_tests "Debug Mode Tests" "" "-vv -s --tb=long --log-cli-level=DEBUG"
        ;;

    "help"|"-h"|"--help")
        echo "Usage: ./run_integration_tests.sh [TEST_TYPE]"
        echo ""
        echo "TEST_TYPE options:"
        echo "  all              - Run all integration tests (default)"
        echo "  api              - Run API integration tests only"
        echo "  storage          - Run storage integration tests only"
        echo "  observability    - Run observability tests only"
        echo "  performance      - Run performance benchmarks"
        echo "  integration-only - Run tests with real Redis/PostgreSQL"
        echo "  fast             - Run fast tests only (skip slow/performance)"
        echo "  coverage         - Run tests with coverage report"
        echo "  debug            - Run tests in debug mode with verbose output"
        echo "  help             - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_integration_tests.sh                    # Run all tests"
        echo "  ./run_integration_tests.sh api                # API tests only"
        echo "  ./run_integration_tests.sh performance        # Performance benchmarks"
        echo "  ./run_integration_tests.sh coverage           # Generate coverage report"
        echo ""
        exit 0
        ;;

    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Run './run_integration_tests.sh help' for usage"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Test suite completed successfully!${NC}"
echo "=========================================="
echo ""
