#!/bin/bash
# benchmarks/integration_connectivity.sh
# Verifies Jarvis server connectivity and IPv4 loopback binding.

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "--- ${GREEN}Jarvis Connectivity Test Suite${NC} ---"

# 1. Test 127.0.0.1 reachability
echo -n "Test 1: GET http://127.0.0.1:7002/health ... "
status=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7002/health)
if [ "$status" == "200" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL ($status)${NC}"
fi

# 2. Test localhost reachability (should work if IPv4 localhost is bound)
echo -n "Test 2: GET http://localhost:7002/health ... "
status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:7002/health)
if [ "$status" == "200" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL ($status)${NC} (May be IPv6 resolution delay)"
fi

# 3. Test POST /explain for "Empty Reply" regression
echo -n "Test 3: POST http://127.0.0.1:7002/explain (Stability Check) ... "
status=$(curl -s -X POST -H "Content-Type: application/json" -d '{"code": "def foo(): pass", "language": "python"}' -o /dev/null -w "%{http_code}" http://127.0.0.1:7002/explain)
if [ "$status" == "200" ] || [ "$status" == "503" ]; then
    echo -e "${GREEN}PASS (No Crash)${NC}"
else
    echo -e "${RED}FAIL ($status)${NC} (Likely server crash)"
fi

# 4. Check Port Binding
echo -n "Test 4: ss -tulpn Check ... "
if ss -tulpn | grep -q "127.0.0.1:7002"; then
    echo -e "${GREEN}PASS (Bound to 127.0.0.1)${NC}"
else
    echo -e "${RED}FAIL (Bound to $(ss -tulpn | grep 7002 | awk '{print $4}'))${NC}"
fi

echo -e "--- ${GREEN}Tests Completed${NC} ---"
