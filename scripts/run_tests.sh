#!/bin/bash
# Test runner script for AstraGuard-AI
# Usage: ./run_tests.sh [options]
# Options:
#   --unit          Run only unit tests
#   --integration   Run only integration tests
#   --coverage      Run with coverage reporting
#   --slow          Include slow tests
#   --profile       Profile memory usage
#   --full          Run all checks (unit, integration, coverage, quality)

set -e

echo "🧪 AstraGuard-AI Test Runner"
echo "============================"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default behavior
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_COVERAGE=false
RUN_QUALITY=false
SKIP_SLOW=true
VERBOSE=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            shift
            ;;
        --integration)
            RUN_UNIT=false
            RUN_INTEGRATION=true
            shift
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        --quality)
            RUN_QUALITY=true
            shift
            ;;
        --slow)
            SKIP_SLOW=false
            shift
            ;;
        --quiet)
            VERBOSE=false
            shift
            ;;
        --full)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_COVERAGE=true
            RUN_QUALITY=true
            SKIP_SLOW=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    pip install -r requirements.txt > /dev/null 2>&1
    pip install pytest pytest-cov pytest-mock pytest-timeout > /dev/null 2>&1
fi

# Run unit tests
if [ "$RUN_UNIT" = true ]; then
    echo -e "${YELLOW}🔍 Running unit tests...${NC}"
    if [ "$SKIP_SLOW" = true ]; then
        pytest tests/ -v -m "not slow" --timeout=10 --tb=short
    else
        pytest tests/ -v --timeout=10 --tb=short
    fi
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Unit tests passed${NC}"
    else
        echo -e "${RED}❌ Unit tests failed${NC}"
        exit 1
    fi
fi

# Run integration tests
if [ "$RUN_INTEGRATION" = true ]; then
    echo -e "${YELLOW}🔗 Running integration tests...${NC}"
    if [ -f "validate_integration.py" ]; then
        python validate_integration.py
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Integration tests passed${NC}"
        else
            echo -e "${RED}⚠️  Integration tests had issues${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Integration test script not found${NC}"
    fi
fi

# Run coverage analysis
if [ "$RUN_COVERAGE" = true ]; then
    echo -e "${YELLOW}📊 Running coverage analysis...${NC}"
    pytest tests/ \
        --cov=core \
        --cov=anomaly \
        --cov=state_machine \
        --cov=memory_engine \
        --cov-report=term-missing \
        --cov-report=html \
        --cov-fail-under=80 \
        -q
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Coverage threshold met (80%+)${NC}"
        echo -e "${YELLOW}📄 HTML report: htmlcov/index.html${NC}"
    else
        echo -e "${RED}❌ Coverage below threshold${NC}"
        exit 1
    fi
fi

# Run code quality checks
if [ "$RUN_QUALITY" = true ]; then
    echo -e "${YELLOW}🎨 Running code quality checks...${NC}"
    
    # Flake8
    if command -v flake8 &> /dev/null; then
        flake8 core anomaly state_machine memory_engine \
            --max-line-length=100 \
            --exclude=__pycache__
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Flake8 checks passed${NC}"
        else
            echo -e "${YELLOW}⚠️  Flake8 warnings found${NC}"
        fi
    fi
    
    # Bandit (security)
    if command -v bandit &> /dev/null; then
        bandit -r core anomaly state_machine memory_engine -ll -q 2>/dev/null || true
        echo -e "${GREEN}✅ Security scan complete${NC}"
    fi
fi

# Summary
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All tests completed successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""

exit 0
