#!/bin/bash

# Plan B Redis Build and Verify Script
# Tests all Redis versions and pushes to GCR

set -e

echo "🔴 Plan B Redis Build and Verify"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run test for a version
run_test() {
    local version=$1
    local version_dir=$2
    
    echo -e "${YELLOW}🧪 Testing Redis $version...${NC}"
    
    if [ -f "$version_dir/test.py" ]; then
        cd "$version_dir"
        if python3 test.py; then
            echo -e "${GREEN}✅ Redis $version test passed${NC}"
        else
            echo -e "${RED}❌ Redis $version test failed${NC}"
            return 1
        fi
        cd - > /dev/null
    else
        echo -e "${RED}❌ No test.py found for Redis $version${NC}"
        return 1
    fi
}

# Test all Redis versions
echo "🚀 Starting Redis version tests..."

# Test Redis latest
if ! run_test "latest" "./latest"; then
    echo -e "${RED}❌ Redis latest test failed${NC}"
    exit 1
fi

# Test Redis 7.8
if ! run_test "7.8" "./7.8"; then
    echo -e "${RED}❌ Redis 7.8 test failed${NC}"
    exit 1
fi

# Test Redis 7.2
if ! run_test "7.2" "./7.2"; then
    echo -e "${RED}❌ Redis 7.2 test failed${NC}"
    exit 1
fi

# Test Redis 6.2.18
if ! run_test "6.2.18" "./6.2.18"; then
    echo -e "${RED}❌ Redis 6.2.18 test failed${NC}"
    exit 1
fi

# Test Redis 6.0
if ! run_test "6.0" "./6.0"; then
    echo -e "${RED}❌ Redis 6.0 test failed${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 All Redis version tests passed!${NC}"
echo -e "${GREEN}✅ Redis containers are ready for production${NC}"
