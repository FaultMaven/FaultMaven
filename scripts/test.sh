#!/bin/bash

# FaultMaven test runner script with comprehensive options
# Provides convenient interface to pytest with coverage, filtering, and reporting

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Print colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default values
COVERAGE=false
VERBOSE=false
SKIP_SERVICES=true
TEST_MARKER=""
TEST_PATH=""
SPECIFIC_TEST=""
HTML_REPORT=false
FAIL_FAST=false
PARALLEL=false

# Show help
show_help() {
    echo "FaultMaven Test Runner"
    echo ""
    echo "Usage: $0 [OPTIONS] [TEST_PATH]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -c, --coverage          Enable coverage reporting"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -s, --with-services     Run tests with live services (default: skip)"
    echo "  -m, --marker MARKER     Run tests with specific marker (unit, integration, api, e2e)"
    echo "  -k, --keyword PATTERN   Run tests matching keyword pattern"
    echo "  -x, --fail-fast         Stop on first failure"
    echo "  -n, --parallel N        Run tests in parallel with N workers"
    echo "  --html                  Generate HTML coverage report"
    echo ""
    echo "Test Markers:"
    echo "  unit                    Fast unit tests (no external dependencies)"
    echo "  integration             Integration tests (may require services)"
    echo "  api                     API endpoint tests"
    echo "  e2e                     End-to-end tests"
    echo ""
    echo "Examples:"
    echo "  $0                                  # Run all tests"
    echo "  $0 -c                               # Run with coverage"
    echo "  $0 -m unit                          # Run only unit tests"
    echo "  $0 -m integration -s                # Run integration tests with services"
    echo "  $0 -k test_auth                     # Run tests matching 'test_auth'"
    echo "  $0 -c --html                        # Generate HTML coverage report"
    echo "  $0 -v -x tests/modules/auth/        # Verbose, fail-fast for auth module"
    echo "  $0 -n 4                             # Run with 4 parallel workers"
    echo ""
    echo "Environment Variables:"
    echo "  SKIP_SERVICE_CHECKS     Set to 'false' to require live services"
    echo "  PYTEST_ARGS             Additional pytest arguments"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -s|--with-services)
            SKIP_SERVICES=false
            shift
            ;;
        -m|--marker)
            TEST_MARKER="$2"
            shift 2
            ;;
        -k|--keyword)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        -x|--fail-fast)
            FAIL_FAST=true
            shift
            ;;
        -n|--parallel)
            PARALLEL=true
            PARALLEL_WORKERS="$2"
            shift 2
            ;;
        --html)
            HTML_REPORT=true
            COVERAGE=true  # HTML report requires coverage
            shift
            ;;
        -*)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            TEST_PATH="$1"
            shift
            ;;
    esac
done

# Check if we're in the correct directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Must run from FaultMaven project root (pyproject.toml not found)"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    print_info "Activating virtual environment..."
    source .venv/bin/activate
elif [ -f "/.dockerenv" ]; then
    print_info "Running in Docker container"
else
    print_warning "No virtual environment found (.venv)"
    if command -v uv >/dev/null 2>&1; then
        print_info "Using uv for package management"
    else
        print_warning "Consider creating a virtual environment: python -m venv .venv"
    fi
fi

# Set environment variables
export SKIP_SERVICE_CHECKS=$SKIP_SERVICES

# Check for required services if not skipping
if [ "$SKIP_SERVICES" = false ]; then
    print_info "Checking for required services..."

    # Check for backend API
    if ! curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        print_error "Backend API not running at http://localhost:8000"
        print_warning "Start server with: ./scripts/start.sh"
        exit 1
    fi

    # Check for Redis
    if command -v redis-cli >/dev/null 2>&1; then
        REDIS_HOST="${REDIS_HOST:-localhost}"
        REDIS_PORT="${REDIS_PORT:-6379}"
        if ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
            print_warning "Redis not responding at $REDIS_HOST:$REDIS_PORT"
        else
            print_success "Redis available at $REDIS_HOST:$REDIS_PORT"
        fi
    fi

    print_success "Required services are available"
else
    print_warning "Skipping service checks (SKIP_SERVICE_CHECKS=$SKIP_SERVICES)"
fi

# Build pytest command
PYTEST_CMD="python -m pytest"

# Add test path or default to tests/
if [ -n "$TEST_PATH" ]; then
    PYTEST_CMD="$PYTEST_CMD $TEST_PATH"
else
    PYTEST_CMD="$PYTEST_CMD tests/"
fi

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage flags
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=faultmaven --cov-report=term-missing"
    if [ "$HTML_REPORT" = true ]; then
        PYTEST_CMD="$PYTEST_CMD --cov-report=html"
    fi
fi

# Add marker filter
if [ -n "$TEST_MARKER" ]; then
    PYTEST_CMD="$PYTEST_CMD -m $TEST_MARKER"
fi

# Add keyword filter
if [ -n "$SPECIFIC_TEST" ]; then
    PYTEST_CMD="$PYTEST_CMD -k '$SPECIFIC_TEST'"
fi

# Add fail-fast
if [ "$FAIL_FAST" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -x"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    if ! python -c "import pytest_xdist" 2>/dev/null; then
        print_warning "pytest-xdist not installed, parallel execution not available"
        print_info "Install with: pip install pytest-xdist"
    else
        PYTEST_CMD="$PYTEST_CMD -n ${PARALLEL_WORKERS:-auto}"
    fi
fi

# Add any additional pytest arguments from environment
if [ -n "$PYTEST_ARGS" ]; then
    PYTEST_CMD="$PYTEST_CMD $PYTEST_ARGS"
fi

# Display configuration
echo ""
print_info "FaultMaven Test Runner"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_info "Project root: $PROJECT_ROOT"
print_info "Test path: ${TEST_PATH:-tests/}"
[ -n "$TEST_MARKER" ] && print_info "Marker: $TEST_MARKER"
[ -n "$SPECIFIC_TEST" ] && print_info "Keyword: $SPECIFIC_TEST"
print_info "Coverage: $([ "$COVERAGE" = true ] && echo 'enabled' || echo 'disabled')"
print_info "Skip services: $SKIP_SERVICES"
[ "$PARALLEL" = true ] && print_info "Parallel workers: ${PARALLEL_WORKERS:-auto}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Print command being executed
print_info "Running: $PYTEST_CMD"
echo ""

# Run tests
START_TIME=$(date +%s)

if eval $PYTEST_CMD; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    print_success "✅ Tests completed successfully in ${DURATION}s!"

    if [ "$HTML_REPORT" = true ]; then
        echo ""
        print_info "📊 HTML coverage report generated at: htmlcov/index.html"
        print_info "Open with: open htmlcov/index.html  (macOS)"
        print_info "       or: xdg-open htmlcov/index.html  (Linux)"
    fi

    exit 0
else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    print_error "❌ Tests failed after ${DURATION}s"

    if [ "$HTML_REPORT" = true ]; then
        echo ""
        print_info "📊 Partial HTML coverage report at: htmlcov/index.html"
    fi

    exit 1
fi
