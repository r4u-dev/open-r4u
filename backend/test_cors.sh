#!/bin/bash

# Test CORS and API Integration Script
# This script tests that the backend API is properly configured for frontend access

set -e

BASE_URL="http://localhost:8000"
FRONTEND_ORIGIN="http://localhost:8080"

echo "======================================"
echo "Testing Open R4U Backend API"
echo "======================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health check
echo "Test 1: Health Check"
echo "-------------------"
response=$(curl -s -w "\n%{http_code}" ${BASE_URL}/health)
status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✓ Backend is running${NC}"
    echo "  Response: $body"
else
    echo -e "${RED}✗ Backend is not responding${NC}"
    echo "  Status code: $status_code"
    exit 1
fi
echo ""

# Test 2: CORS Preflight Request
echo "Test 2: CORS Preflight (OPTIONS)"
echo "--------------------------------"
cors_response=$(curl -s -I -X OPTIONS \
    -H "Origin: ${FRONTEND_ORIGIN}" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: Content-Type" \
    ${BASE_URL}/traces)

if echo "$cors_response" | grep -qi "access-control-allow-origin"; then
    echo -e "${GREEN}✓ CORS headers present${NC}"
    echo "$cors_response" | grep -i "access-control"
else
    echo -e "${RED}✗ CORS headers missing${NC}"
    echo "Response headers:"
    echo "$cors_response"
    exit 1
fi
echo ""

# Test 3: GET /traces endpoint
echo "Test 3: GET /traces"
echo "-------------------"
response=$(curl -s -w "\n%{http_code}" ${BASE_URL}/traces?limit=5)
status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✓ Traces endpoint responding${NC}"

    # Check if response is valid JSON
    if echo "$body" | python3 -m json.tool > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Valid JSON response${NC}"

        # Count traces
        trace_count=$(echo "$body" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
        echo "  Number of traces: $trace_count"
    else
        echo -e "${RED}✗ Invalid JSON response${NC}"
    fi
else
    echo -e "${RED}✗ Traces endpoint failed${NC}"
    echo "  Status code: $status_code"
    echo "  Response: $body"
fi
echo ""

# Test 4: GET /traces with pagination
echo "Test 4: GET /traces with pagination"
echo "-----------------------------------"
response=$(curl -s -w "\n%{http_code}" "${BASE_URL}/traces?limit=3&offset=0")
status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✓ Pagination works${NC}"
    trace_count=$(echo "$body" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    echo "  Requested limit: 3"
    echo "  Traces returned: $trace_count"
else
    echo -e "${RED}✗ Pagination failed${NC}"
    echo "  Status code: $status_code"
fi
echo ""

# Test 5: Test with CORS headers (simulating browser)
echo "Test 5: GET with Origin header"
echo "-------------------------------"
response=$(curl -s -w "\n%{http_code}" \
    -H "Origin: ${FRONTEND_ORIGIN}" \
    ${BASE_URL}/traces?limit=1)
status_code=$(echo "$response" | tail -n1)

if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✓ Request with Origin header works${NC}"
else
    echo -e "${RED}✗ Request with Origin header failed${NC}"
    echo "  Status code: $status_code"
fi
echo ""

# Test 6: Invalid pagination parameters
echo "Test 6: Parameter validation"
echo "----------------------------"
response=$(curl -s -w "\n%{http_code}" "${BASE_URL}/traces?limit=0")
status_code=$(echo "$response" | tail -n1)

if [ "$status_code" = "422" ]; then
    echo -e "${GREEN}✓ Validation works (rejected limit=0)${NC}"
else
    echo -e "${YELLOW}⚠ Validation might not be working properly${NC}"
    echo "  Expected: 422, Got: $status_code"
fi
echo ""

# Summary
echo "======================================"
echo "Summary"
echo "======================================"
echo ""
echo "Backend URL: $BASE_URL"
echo "Frontend Origin: $FRONTEND_ORIGIN"
echo ""
echo "Next steps:"
echo "1. If all tests passed, start the frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "2. Open http://localhost:8080 in your browser"
echo ""
echo "3. Navigate to the Traces page"
echo ""
echo "4. Check the browser console for any errors"
echo ""
echo "If you see CORS errors in the browser:"
echo "- Make sure the backend was restarted after adding CORS middleware"
echo "- Check that the frontend origin matches what's configured"
echo ""
