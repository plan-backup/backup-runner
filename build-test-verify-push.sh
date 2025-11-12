#!/bin/bash
# Plan B Database Backup Runner - Unified Build, Test, Verify & Push
# Runs all test.py files recursively to build, test, and push containers

set -e

# Configuration
TARGET_DATABASES=("postgresql" "mysql" "mongodb" "arangodb")
LOG_DIR="./test-logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Create log directory
mkdir -p "$LOG_DIR"

echo -e "${BLUE}🚀 Plan B Database Backup Runner - Unified Test Pipeline${NC}"
echo -e "${BLUE}================================================================${NC}"
echo -e "${CYAN}Timestamp: ${TIMESTAMP}${NC}"
echo -e "${CYAN}Log Directory: ${LOG_DIR}${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    exit 1
fi

# Check gcloud authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated with gcloud. Run: gcloud auth login${NC}"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

# Check required Python packages
echo -e "${BLUE}📦 Checking Python dependencies...${NC}"
python3 -c "import docker, requests, subprocess, tempfile, logging" 2>/dev/null || {
    echo -e "${RED}❌ Missing Python packages. Install with: pip3 install docker requests${NC}"
    exit 1
}

echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# Statistics tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

declare -a PASSED_VERSIONS
declare -a FAILED_VERSIONS
declare -a SKIPPED_VERSIONS

# Function to run a single test
run_single_test() {
    local db_path="$1"
    local db_name=$(basename "$(dirname "$db_path")")
    local version=$(basename "$db_path")
    local test_name="${db_name}:${version}"
    
    echo -e "${BLUE}🧪 Testing ${test_name}...${NC}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # Create log file for this test
    local log_file="${LOG_DIR}/${db_name}_${version}_${TIMESTAMP}.log"
    
    # Run the test with timeout
    local start_time=$(date +%s)
    
    if timeout 600 python3 "$db_path/test.py" > "$log_file" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        echo -e "${GREEN}✅ ${test_name} PASSED (${duration}s)${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        PASSED_VERSIONS+=("$test_name")
        
        # Extract key info from log
        local backup_size=$(grep "Backup file created" "$log_file" | grep -o '[0-9]* bytes' | head -1 || echo "unknown size")
        local image_info=$(grep "Successfully pushed" "$log_file" | tail -1 | cut -d' ' -f5- || echo "")
        
        echo -e "${CYAN}    📦 Backup: ${backup_size}${NC}"
        echo -e "${CYAN}    🏷️  Image: ${image_info}${NC}"
        
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        echo -e "${RED}❌ ${test_name} FAILED (${duration}s)${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_VERSIONS+=("$test_name")
        
        # Show last few lines of error
        echo -e "${RED}    Error details:${NC}"
        tail -3 "$log_file" | sed 's/^/    /' || echo "    No error details available"
    fi
    
    echo ""
}

# Find and run all tests
echo -e "${BLUE}🔍 Discovering test files...${NC}"

for db in "${TARGET_DATABASES[@]}"; do
    if [ -d "$db" ]; then
        echo -e "${YELLOW}📂 Scanning $db/...${NC}"
        
        # Find all test.py files in this database directory
        while IFS= read -r -d '' test_file; do
            if [ -f "$test_file" ]; then
                test_dir=$(dirname "$test_file")
                echo -e "${CYAN}    Found: $test_dir${NC}"
                
                # Run the test
                run_single_test "$test_dir"
            fi
        done < <(find "$db" -name "test.py" -print0 | sort -z)
    else
        echo -e "${YELLOW}⚠️  Directory $db not found, skipping${NC}"
    fi
done

# Final report
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}📊 Final Test Report${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

echo -e "${CYAN}📈 Statistics:${NC}"
echo -e "  Total Tests: ${TOTAL_TESTS}"
echo -e "  ${GREEN}✅ Passed: ${PASSED_TESTS}${NC}"
echo -e "  ${RED}❌ Failed: ${FAILED_TESTS}${NC}"
echo -e "  ${YELLOW}⏸️  Skipped: ${SKIPPED_TESTS}${NC}"
echo ""

if [ ${PASSED_TESTS} -gt 0 ]; then
    echo -e "${GREEN}🎉 Successful Deployments:${NC}"
    for version in "${PASSED_VERSIONS[@]}"; do
        echo -e "  ✅ $version"
    done
    echo ""
fi

if [ ${FAILED_TESTS} -gt 0 ]; then
    echo -e "${RED}💥 Failed Tests:${NC}"
    for version in "${FAILED_VERSIONS[@]}"; do
        echo -e "  ❌ $version"
    done
    echo ""
    echo -e "${RED}📋 Check detailed logs in: ${LOG_DIR}${NC}"
fi

# Calculate success rate
if [ ${TOTAL_TESTS} -gt 0 ]; then
    success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    echo -e "${CYAN}📊 Success Rate: ${success_rate}%${NC}"
fi

echo ""
echo -e "${BLUE}🏁 Pipeline Complete!${NC}"

# Exit code based on results
if [ ${FAILED_TESTS} -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! All containers are production-ready.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Check logs for details.${NC}"
    exit 1
fi
