#!/bin/bash
#
# FaultMaven Service Health Check
# Checks the health status of all FaultMaven microservices
#
# Usage: ./health_check.sh [BASE_URL]
# Example: ./health_check.sh http://localhost:8000
#

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
TIMEOUT=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Services to check (via API Gateway)
declare -A SERVICES=(
    ["API Gateway"]="/health"
    ["Auth Service"]="/v1/auth/health"
    ["Session Service"]="/v1/sessions/health"
    ["Case Service"]="/v1/cases/health"
    ["Knowledge Service"]="/v1/knowledge/health"
    ["Evidence Service"]="/v1/evidence/health"
    ["Agent Service"]="/v1/agent/health"
)

# Direct service ports (for local development)
declare -A DIRECT_PORTS=(
    ["Auth Service"]="8001"
    ["Session Service"]="8002"
    ["Case Service"]="8003"
    ["Knowledge Service"]="8004"
    ["Evidence Service"]="8005"
    ["Agent Service"]="8006"
    ["API Gateway"]="8090"
)

echo "=========================================="
echo "  FaultMaven Health Check"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Function to check service health
check_health() {
    local service_name="$1"
    local endpoint="$2"
    local url="${BASE_URL}${endpoint}"

    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $TIMEOUT "$url" 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        echo -e "  ${GREEN}✓${NC} $service_name: ${GREEN}healthy${NC}"
        return 0
    elif [ "$response" = "000" ]; then
        echo -e "  ${RED}✗${NC} $service_name: ${RED}unreachable${NC}"
        return 1
    else
        echo -e "  ${YELLOW}!${NC} $service_name: ${YELLOW}HTTP $response${NC}"
        return 1
    fi
}

# Function to check direct service ports
check_direct() {
    local service_name="$1"
    local port="$2"
    local url="http://localhost:${port}/health"

    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $TIMEOUT "$url" 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        echo -e "  ${GREEN}✓${NC} $service_name (port $port): ${GREEN}healthy${NC}"
        return 0
    elif [ "$response" = "000" ]; then
        echo -e "  ${RED}✗${NC} $service_name (port $port): ${RED}unreachable${NC}"
        return 1
    else
        echo -e "  ${YELLOW}!${NC} $service_name (port $port): ${YELLOW}HTTP $response${NC}"
        return 1
    fi
}

# Check via API Gateway
echo "Checking via API Gateway..."
echo "------------------------------------------"
healthy=0
total=0

for service in "${!SERVICES[@]}"; do
    total=$((total + 1))
    if check_health "$service" "${SERVICES[$service]}"; then
        healthy=$((healthy + 1))
    fi
done

echo ""
echo "=========================================="
echo "Summary: $healthy/$total services healthy"
echo "=========================================="

# Option to check direct ports
if [ "$2" = "--direct" ]; then
    echo ""
    echo "Checking direct service ports..."
    echo "------------------------------------------"

    for service in "${!DIRECT_PORTS[@]}"; do
        check_direct "$service" "${DIRECT_PORTS[$service]}"
    done
fi

# Check capabilities endpoint
echo ""
echo "Checking capabilities..."
echo "------------------------------------------"
capabilities=$(curl -s --connect-timeout $TIMEOUT "${BASE_URL}/v1/meta/capabilities" 2>/dev/null || echo "{}")

if [ -n "$capabilities" ] && [ "$capabilities" != "{}" ]; then
    echo -e "  ${GREEN}✓${NC} Capabilities endpoint responding"

    # Parse deployment mode
    mode=$(echo "$capabilities" | grep -o '"deploymentMode":"[^"]*"' | cut -d'"' -f4)
    version=$(echo "$capabilities" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)

    if [ -n "$mode" ]; then
        echo "  Mode: $mode"
    fi
    if [ -n "$version" ]; then
        echo "  Version: $version"
    fi
else
    echo -e "  ${RED}✗${NC} Capabilities endpoint not responding"
fi

echo ""
echo "Done."
