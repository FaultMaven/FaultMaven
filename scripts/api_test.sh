#!/bin/bash
#
# FaultMaven API Flow Tester
# Tests core API flows: authentication, cases, and agent chat
#
# Usage: ./api_test.sh [BASE_URL] [EMAIL] [PASSWORD]
# Example: ./api_test.sh http://localhost:8000 test@example.com password123
#

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
TEST_EMAIL="${2:-test@faultmaven.local}"
TEST_PASSWORD="${3:-testpassword123}"
TEST_NAME="Test User"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "  FaultMaven API Flow Tester"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo "Test Email: $TEST_EMAIL"
echo ""

# Helper function for API calls
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local token="$4"

    local auth_header=""
    if [ -n "$token" ]; then
        auth_header="-H \"Authorization: Bearer $token\""
    fi

    if [ "$method" = "GET" ]; then
        eval "curl -s -X GET \"${BASE_URL}${endpoint}\" \
            -H \"Content-Type: application/json\" \
            $auth_header"
    else
        eval "curl -s -X $method \"${BASE_URL}${endpoint}\" \
            -H \"Content-Type: application/json\" \
            $auth_header \
            -d '$data'"
    fi
}

# Test result tracking
TESTS_PASSED=0
TESTS_FAILED=0

test_result() {
    local name="$1"
    local success="$2"
    local details="$3"

    if [ "$success" = "true" ]; then
        echo -e "  ${GREEN}✓${NC} $name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗${NC} $name"
        if [ -n "$details" ]; then
            echo -e "    ${YELLOW}→ $details${NC}"
        fi
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# ==========================================
# Test 1: User Registration
# ==========================================
echo ""
echo "${BLUE}Test 1: User Registration${NC}"
echo "------------------------------------------"

REGISTER_RESPONSE=$(api_call "POST" "/v1/auth/register" "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"full_name\": \"$TEST_NAME\"
}")

if echo "$REGISTER_RESPONSE" | grep -q "user_id"; then
    USER_ID=$(echo "$REGISTER_RESPONSE" | grep -o '"user_id":"[^"]*"' | cut -d'"' -f4)
    test_result "Registration successful" "true"
    echo "    User ID: $USER_ID"
elif echo "$REGISTER_RESPONSE" | grep -q "already exists"; then
    test_result "User already exists (OK for re-runs)" "true"
else
    test_result "Registration" "false" "$REGISTER_RESPONSE"
fi

# ==========================================
# Test 2: User Login
# ==========================================
echo ""
echo "${BLUE}Test 2: User Login${NC}"
echo "------------------------------------------"

LOGIN_RESPONSE=$(api_call "POST" "/v1/auth/login" "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\"
}")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    test_result "Login successful" "true"
    echo "    Token: ${ACCESS_TOKEN:0:20}..."
else
    test_result "Login" "false" "$LOGIN_RESPONSE"
    echo -e "${RED}Cannot continue without authentication. Exiting.${NC}"
    exit 1
fi

# ==========================================
# Test 3: Create Case
# ==========================================
echo ""
echo "${BLUE}Test 3: Create Troubleshooting Case${NC}"
echo "------------------------------------------"

CASE_RESPONSE=$(api_call "POST" "/v1/cases" "{
    \"title\": \"API Test Case - $(date +%Y%m%d%H%M%S)\",
    \"description\": \"Automated test case created by api_test.sh\"
}" "$ACCESS_TOKEN")

if echo "$CASE_RESPONSE" | grep -q "case_id"; then
    CASE_ID=$(echo "$CASE_RESPONSE" | grep -o '"case_id":"[^"]*"' | cut -d'"' -f4)
    test_result "Case created" "true"
    echo "    Case ID: $CASE_ID"
else
    test_result "Create case" "false" "$CASE_RESPONSE"
fi

# ==========================================
# Test 4: Get Case
# ==========================================
echo ""
echo "${BLUE}Test 4: Retrieve Case${NC}"
echo "------------------------------------------"

if [ -n "$CASE_ID" ]; then
    GET_CASE_RESPONSE=$(api_call "GET" "/v1/cases/$CASE_ID" "" "$ACCESS_TOKEN")

    if echo "$GET_CASE_RESPONSE" | grep -q "$CASE_ID"; then
        test_result "Case retrieved" "true"
    else
        test_result "Get case" "false" "$GET_CASE_RESPONSE"
    fi
else
    test_result "Get case" "false" "No case ID from previous step"
fi

# ==========================================
# Test 5: List Cases
# ==========================================
echo ""
echo "${BLUE}Test 5: List Cases${NC}"
echo "------------------------------------------"

LIST_CASES_RESPONSE=$(api_call "GET" "/v1/cases" "" "$ACCESS_TOKEN")

if echo "$LIST_CASES_RESPONSE" | grep -q "cases"; then
    CASE_COUNT=$(echo "$LIST_CASES_RESPONSE" | grep -o '"total":[0-9]*' | cut -d':' -f2)
    test_result "Cases listed" "true"
    echo "    Total cases: ${CASE_COUNT:-unknown}"
else
    test_result "List cases" "false" "$LIST_CASES_RESPONSE"
fi

# ==========================================
# Test 6: Chat with Agent
# ==========================================
echo ""
echo "${BLUE}Test 6: Chat with AI Agent${NC}"
echo "------------------------------------------"

if [ -n "$CASE_ID" ]; then
    CHAT_RESPONSE=$(api_call "POST" "/v1/agent/chat" "{
        \"case_id\": \"$CASE_ID\",
        \"message\": \"Hello, this is a test message. Can you acknowledge?\"
    }" "$ACCESS_TOKEN")

    if echo "$CHAT_RESPONSE" | grep -q "content"; then
        test_result "Agent responded" "true"
        AGENT_REPLY=$(echo "$CHAT_RESPONSE" | grep -o '"content":"[^"]*"' | head -1 | cut -d'"' -f4)
        echo "    Agent: ${AGENT_REPLY:0:60}..."
    else
        test_result "Agent chat" "false" "$CHAT_RESPONSE"
    fi
else
    test_result "Agent chat" "false" "No case ID available"
fi

# ==========================================
# Test 7: Knowledge Base Search
# ==========================================
echo ""
echo "${BLUE}Test 7: Knowledge Base Search${NC}"
echo "------------------------------------------"

KB_SEARCH_RESPONSE=$(api_call "POST" "/v1/knowledge/search" "{
    \"query\": \"database connection timeout troubleshooting\",
    \"limit\": 5
}" "$ACCESS_TOKEN")

if echo "$KB_SEARCH_RESPONSE" | grep -q "results"; then
    RESULT_COUNT=$(echo "$KB_SEARCH_RESPONSE" | grep -o '"total_results":[0-9]*' | cut -d':' -f2)
    test_result "KB search completed" "true"
    echo "    Results found: ${RESULT_COUNT:-0}"
else
    test_result "KB search" "false" "$KB_SEARCH_RESPONSE"
fi

# ==========================================
# Test 8: Capabilities Endpoint
# ==========================================
echo ""
echo "${BLUE}Test 8: Capabilities Discovery${NC}"
echo "------------------------------------------"

CAPABILITIES_RESPONSE=$(api_call "GET" "/v1/meta/capabilities" "")

if echo "$CAPABILITIES_RESPONSE" | grep -q "deploymentMode"; then
    DEPLOY_MODE=$(echo "$CAPABILITIES_RESPONSE" | grep -o '"deploymentMode":"[^"]*"' | cut -d'"' -f4)
    VERSION=$(echo "$CAPABILITIES_RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    test_result "Capabilities retrieved" "true"
    echo "    Mode: $DEPLOY_MODE"
    echo "    Version: $VERSION"
else
    test_result "Capabilities" "false" "$CAPABILITIES_RESPONSE"
fi

# ==========================================
# Summary
# ==========================================
echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo -e "  ${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "  ${RED}Failed:${NC} $TESTS_FAILED"
echo "  Total: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${YELLOW}Some tests failed. Check the output above.${NC}"
    exit 1
fi
