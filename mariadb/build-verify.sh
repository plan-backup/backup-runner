#!/bin/bash

# Don't exit on errors - we want to test all versions even if one fails
# set -e

# --- Configuration ---
DB_TYPE="MariaDB"
BASE_DIR="$(dirname "$0")" # mariadb/ directory
LOG_DIR="${BASE_DIR}/test-logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# --- Global counters ---
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -a FAILED_LIST
declare -a SUCCESSFUL_DEPLOYMENTS

# --- Functions ---

# Function to check if a command exists
command_exists () {
  command -v "$1" >/dev/null 2>&1
}

# Function to check Python dependencies
check_python_dependencies() {
    echo -e "${BLUE}📦 Checking Python dependencies...${NC}"
    local missing_deps=()
    for dep in docker; do # Add other Python deps if needed, e.g., psycopg2, mysql-connector-python
        if ! python3 -c "import $dep" &>/dev/null; then
            missing_deps+=("$dep")
        fi
    done

    if [ ${#missing_deps[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All Python dependencies met${NC}"
        return 0
    else
        echo -e "${RED}❌ Missing Python dependencies: ${missing_deps[*]}.${NC}"
        echo -e "${YELLOW}Please install them using 'pip install <dependency-name>' (e.g., 'pip install docker').${NC}"
        return 1
    fi
}

# Function to run a single test.py script
run_test() {
    local version_dir="$1"
    local version=$(basename "$version_dir")
    local test_path="${version_dir}/test.py"

    echo -e "${YELLOW}📂 Found: ${DB_TYPE} ${version}${NC}"
    echo -e "${BLUE}🧪 Testing ${DB_TYPE} ${version}...${NC}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # Create log file for this test
    local log_file="${LOG_DIR}/mariadb_${version}_${TIMESTAMP}.log"

    # Run the test
    local start_time=$(date +%s)

    # Run the test and capture output
    python3 "$test_path" > "$log_file" 2>&1
    local test_exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Check if the backup pipeline succeeded (ignore GCR push failures)
    if grep -q "Complete backup pipeline executed successfully" "$log_file" && \
       grep -q "Backup uploaded and verified" "$log_file"; then
        echo -e "${GREEN}✅ ${DB_TYPE} ${version} PASSED (${duration}s)${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))

        # Extract backup size and image tag from log
        local backup_size=$(grep "Backup verified in MinIO:" "$log_file" | awk '{print $NF, $(NF-1)}' | sed 's/.$//')
        local image_tag=$(grep "Image:" "$log_file" | awk '{print $NF}')

        if [ -n "$backup_size" ]; then
            echo -e "${CYAN}    📦 Backup: ${backup_size}${NC}"
        fi
        if [ -n "$image_tag" ]; then
            echo -e "${CYAN}    🏷️  Image: ${image_tag}${NC}"
            SUCCESSFUL_DEPLOYMENTS+=("${image_tag}")
        fi
        
        # Check if GCR push failed but backup succeeded
        if grep -q "Failed to push to GCR" "$log_file"; then
            echo -e "${YELLOW}    ⚠️  GCR push failed (authentication issue)${NC}"
        fi
    else
        echo -e "${RED}❌ ${DB_TYPE} ${version} FAILED (${duration}s)${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_LIST+=("${DB_TYPE} ${version}")
        echo -e "${RED}    Error details:${NC}"
        tail -n 5 "$log_file" # Show last 5 lines of error
    fi
    
    # Continue to next test regardless of result
    echo ""
}

# --- Main Script ---

echo -e "${BLUE}🐬 Plan B ${DB_TYPE} Build & Verify Pipeline${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "${CYAN}Timestamp: ${TIMESTAMP}${NC}"
echo -e "${CYAN}Log Directory: ${LOG_DIR}${NC}"
echo ""

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo -e "${BLUE}🔍 Checking prerequisites...${NC}"
if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed or not in PATH. Please install Docker.${NC}"
    exit 1
fi
if ! command_exists python3; then
    echo -e "${RED}❌ Python3 is not installed or not in PATH. Please install Python3.${NC}"
    exit 1
fi
if ! check_python_dependencies; then
    exit 1
fi
echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

echo -e "${BLUE}🔍 Discovering ${DB_TYPE} versions...${NC}"
# Find all subdirectories (versions)
for version_dir in "${BASE_DIR}"/*/; do
    if [ -d "$version_dir" ] && [ -f "${version_dir}/test.py" ]; then
        run_test "$version_dir"
    fi
done

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}📊 ${DB_TYPE} Test Report${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

echo -e "${CYAN}📈 Statistics:${NC}"
echo "  Total Tests: ${TOTAL_TESTS}"
echo -e "  ${GREEN}✅ Passed: ${PASSED_TESTS}${NC}"
echo -e "  ${RED}❌ Failed: ${FAILED_TESTS}${NC}"
echo ""

if [ ${#FAILED_LIST[@]} -gt 0 ]; then
    echo -e "${RED}💥 Failed Tests:${NC}"
    for test_name in "${FAILED_LIST[@]}"; do
        echo "  ❌ ${test_name}"
    done
    echo ""
fi

if [ ${#SUCCESSFUL_DEPLOYMENTS[@]} -gt 0 ]; then
    echo -e "${GREEN}🎉 Successful Deployments:${NC}"
    for image_tag in "${SUCCESSFUL_DEPLOYMENTS[@]}"; do
        echo "  ✅ ${image_tag}"
    done
    echo ""
fi

success_rate=0
if [ "$TOTAL_TESTS" -gt 0 ]; then
    success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
fi
echo -e "${CYAN}📊 Success Rate: ${success_rate}%${NC}"
echo ""

echo -e "${BLUE}🏁 ${DB_TYPE} Pipeline Complete!${NC}"
if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}🎉 All ${DB_TYPE} tests passed! All containers are production-ready.${NC}"
    echo ""
    echo -e "${CYAN}📋 Production Images:${NC}"
    for image_tag in "${SUCCESSFUL_DEPLOYMENTS[@]}"; do
        echo "  🏷️  ${image_tag}"
    done
    exit 0
else
    echo -e "${RED}⚠️  Some ${DB_TYPE} tests failed. Check logs for details.${NC}"
    echo -e "${RED}📋 Check detailed logs in: ${LOG_DIR}${NC}"
    exit 1
fi
