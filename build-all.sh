#!/bin/bash
# Plan B Database Backup Runner - Build All Containers
# Manual build script for official database backup tools

set -e

# Configuration
PROJECT_ID="apito-cms"
REGISTRY="gcr.io"
IMAGE_PREFIX="plan-b-backup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Plan B Database Backup Runner - Build All Containers${NC}"
echo "Project: ${PROJECT_ID}"
echo "Registry: ${REGISTRY}"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Error: Not authenticated with gcloud${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi

# Configure docker to use gcloud as credential helper
echo -e "${YELLOW}🔧 Configuring Docker authentication...${NC}"
gcloud auth configure-docker

# Build function
build_and_push() {
    local db_type=$1
    local version=$2
    
    local image_name="${REGISTRY}/${PROJECT_ID}/${IMAGE_PREFIX}-${db_type}"
    local tag="${version}"
    local dockerfile_path="./${db_type}/${version}/Dockerfile"
    
    echo -e "${BLUE}📦 Building ${db_type}:${version}...${NC}"
    
    # Build the image (Linux AMD64 for Cloud Run compatibility)
    docker build \
        --platform linux/amd64 \
        -f "${dockerfile_path}" \
        -t "${image_name}:${tag}" \
        -t "${image_name}:latest" \
        .
    
    echo -e "${YELLOW}⬆️  Pushing ${image_name}:${tag}...${NC}"
    
    # Push the image
    docker push "${image_name}:${tag}"
    
    if [ "${version}" != "latest" ]; then
        docker push "${image_name}:latest"
    fi
    
    echo -e "${GREEN}✅ Successfully built and pushed ${db_type}:${version}${NC}"
}

# Build PostgreSQL containers
echo -e "${BLUE}🐘 Building PostgreSQL containers...${NC}"
build_and_push "postgresql" "12"
build_and_push "postgresql" "13"
build_and_push "postgresql" "14"
build_and_push "postgresql" "15"
build_and_push "postgresql" "16"
build_and_push "postgresql" "17"

# Build MySQL containers
echo -e "${BLUE}🐬 Building MySQL containers...${NC}"
build_and_push "mysql" "latest"
build_and_push "mysql" "8.0"
build_and_push "mysql" "5.7"

# Build MariaDB containers
echo -e "${BLUE}🦭 Building MariaDB containers...${NC}"
build_and_push "mariadb" "latest"
build_and_push "mariadb" "11.4"
build_and_push "mariadb" "10.11"

# Build MongoDB containers
echo -e "${BLUE}🍃 Building MongoDB containers...${NC}"
build_and_push "mongodb" "latest"
build_and_push "mongodb" "7.0"
build_and_push "mongodb" "6.0"

# Build Redis containers
echo -e "${BLUE}🔴 Building Redis containers...${NC}"
build_and_push "redis" "latest"
build_and_push "redis" "7.2"
build_and_push "redis" "7.0"

# Build SQL Server containers
echo -e "${BLUE}🏢 Building SQL Server containers...${NC}"
build_and_push "mssql" "latest"
build_and_push "mssql" "2022"
build_and_push "mssql" "2019"

# Build Oracle containers
echo -e "${BLUE}🔶 Building Oracle containers...${NC}"
build_and_push "oracle" "latest"
build_and_push "oracle" "21c"
build_and_push "oracle" "19c"

# Build Cassandra containers
echo -e "${BLUE}🏛️ Building Cassandra containers...${NC}"
build_and_push "cassandra" "latest"
build_and_push "cassandra" "4.1"
build_and_push "cassandra" "4.0"

# Build ArangoDB containers
echo -e "${BLUE}🥨 Building ArangoDB containers...${NC}"
build_and_push "arangodb" "latest"
build_and_push "arangodb" "3.11"
build_and_push "arangodb" "3.10"

# Build Couchbase containers
echo -e "${BLUE}🛋️ Building Couchbase containers...${NC}"
build_and_push "couchbase" "latest"
build_and_push "couchbase" "7.2"
build_and_push "couchbase" "7.1"

echo ""
echo -e "${GREEN}🎉 All containers built and pushed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Built containers:${NC}"
echo "  PostgreSQL: 12, 13, 14, 15, 16, 17"
echo "  MySQL: latest, 8.0, 5.7"
echo "  MariaDB: latest, 11.4, 10.11"
echo "  MongoDB: latest, 7.0, 6.0"
echo "  Redis: latest, 7.2, 7.0"
echo "  SQL Server: latest, 2022, 2019"
echo "  Oracle: latest, 21c, 19c"
echo "  Cassandra: latest, 4.1, 4.0"
echo "  ArangoDB: latest, 3.11, 3.10"
echo "  Couchbase: latest, 7.2, 7.1"
echo ""
echo -e "${BLUE}🏷️ Container registry:${NC} ${REGISTRY}/${PROJECT_ID}/"
echo -e "${BLUE}🔧 Usage in Cloud Run:${NC} ${REGISTRY}/${PROJECT_ID}/${IMAGE_PREFIX}-<db_type>:<version>"
echo ""
echo -e "${YELLOW}Examples:${NC}"
echo "  ${REGISTRY}/${PROJECT_ID}/${IMAGE_PREFIX}-postgresql:16"
echo "  ${REGISTRY}/${PROJECT_ID}/${IMAGE_PREFIX}-mysql:latest"
echo "  ${REGISTRY}/${PROJECT_ID}/${IMAGE_PREFIX}-mongodb:latest"
echo "  ${REGISTRY}/${PROJECT_ID}/${IMAGE_PREFIX}-mssql:latest"
echo "  ${REGISTRY}/${PROJECT_ID}/${IMAGE_PREFIX}-oracle:latest"
echo ""