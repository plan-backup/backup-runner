# Plan B Database Backup Runner - Universal Development Guide

## Overview

This guide provides **database-independent** instructions for creating, testing, and deploying backup containers using the **official mirror pattern**. The same methodology applies to **any database type** - SQL, NoSQL, key-value, document, graph, or time-series databases.

## Architecture Philosophy

### Core Principle: Official Mirror Pattern

- **Use official database images** as base (`vendor/database:version`)
- **Override entrypoints** to prevent database server startup
- **Expose only client tools** (dump/backup utilities)
- **Build for production** (linux/amd64) and test locally (native architecture)

### Universal Benefits

- ✅ **Reliable** - Official images maintained by database vendors
- ✅ **Lightweight** - No custom binaries or complex installations
- ✅ **Version-accurate** - Client tools match server versions exactly
- ✅ **Secure** - No database server running, just client tools
- ✅ **Fast builds** - Simple mirror, no compilation needed
- ✅ **Consistent** - Same pattern works for any database type

---

## Part 1: Universal Dockerfile Pattern

### Template Structure (Database-Independent)

```dockerfile
# Plan B Database Backup Runner - [DATABASE_NAME] [VERSION]
# Client tools only - no database server

FROM [OFFICIAL_BASE_IMAGE]:[VERSION]

# Set Plan B metadata (customize for your database)
ENV DB_TYPE=[database_type]
ENV DB_VERSION=[version]
ENV CONTAINER_VERSION=[database_type]-[version]

# CRITICAL: Override the database entrypoint to allow running client tools directly
# The original entrypoint starts the database server, we want client tools only
ENTRYPOINT []
CMD []

# Verify client tools are available (database-specific verification)
RUN [VERIFICATION_COMMANDS]

LABEL maintainer="Plan B Backup"
LABEL database="[database_type]"
LABEL version="[version]"
LABEL source="[OFFICIAL_BASE_IMAGE]:[VERSION]"
```

### Universal Variables Reference

| Variable                  | Purpose                      | Example Values                            |
| ------------------------- | ---------------------------- | ----------------------------------------- |
| `[DATABASE_NAME]`         | Human-readable database name | PostgreSQL, MySQL, MongoDB, Redis         |
| `[OFFICIAL_BASE_IMAGE]`   | Official Docker Hub image    | `postgres`, `mysql`, `mongo`, `redis`     |
| `[VERSION]`               | Database version tag         | `16`, `latest`, `8.0`, `7.2`              |
| `[database_type]`         | Lowercase identifier         | `postgresql`, `mysql`, `mongodb`, `redis` |
| `[VERIFICATION_COMMANDS]` | Tool availability check      | See examples below                        |

### Database-Specific Examples

#### SQL Databases

```dockerfile
# PostgreSQL Example
FROM postgres:16
ENV DB_TYPE=postgresql
RUN which pg_dump && which pg_restore

# MySQL Example
FROM mysql:8.0
ENV DB_TYPE=mysql
RUN mysqldump --version && mysql --version

# MariaDB Example
FROM mariadb:11.4
ENV DB_TYPE=mariadb
RUN mysqldump --version && mysql --version
```

#### NoSQL Databases

```dockerfile
# MongoDB Example
FROM mongo:7.0
ENV DB_TYPE=mongodb
RUN mongodump --version && mongorestore --version

# ArangoDB Example
FROM arangodb/arangodb:3.11.11
ENV DB_TYPE=arangodb
RUN which arangodump && which arangorestore

# Cassandra Example
FROM cassandra:4.1
ENV DB_TYPE=cassandra
RUN which cqlsh && which nodetool
```

#### Key-Value/Cache Databases

```dockerfile
# Redis Example
FROM redis:7.2
ENV DB_TYPE=redis
RUN redis-cli --version

# Memcached Example (if tools available)
FROM memcached:1.6
ENV DB_TYPE=memcached
RUN memcached -h
```

### Key Implementation Points

- **Always override `ENTRYPOINT []` and `CMD []`** - This prevents the database server from starting
- **Use version-specific base images** - Ensures client/server version compatibility
- **Include verification step** - Confirms tools are available during build
- **Set metadata environment variables** - Used by backup runner scripts

---

## Part 2: Universal Python Test Script Pattern

### Purpose & Goals (Database-Independent)

The `test.py` script serves these **universal functions**:

1. **Integration Testing** - Validates complete backup workflow for ANY database
2. **Production Building** - Builds containers for linux/amd64 (Cloud Run)
3. **Deployment** - Pushes successful containers to registry
4. **Quality Gate** - Only working containers reach production

### Universal Script Structure

```python
#!/usr/bin/env python3
"""
Plan B Integration Test - [DATABASE_NAME] [VERSION]
Tests backup and restore functionality with real database container
"""

import os, sys, time, docker, subprocess, tempfile, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseIntegrationTest:
    def __init__(self):
        # Universal Docker client and container management
        self.client = docker.from_env()
        self.container = None
        self.test_network = None
        self.container_name = None

        # Database-specific configuration (customize per database)
        self.test_db = "planb_testdb"
        self.db_port = [BASE_PORT] + int(time.time()) % 1000  # Dynamic ports
        self.db_user = "[DATABASE_USER]"  # admin, root, postgres, etc.
        self.db_password = "planb_test_pass"

    # Universal 5-Step Pipeline (same for ALL databases):
    def start_database_container(self):    # Step 1: Start test database
    def setup_test_data(self):            # Step 2: Create test data
    def build_container(self):            # Step 3: Build Plan B container
    def run_backup_test(self):            # Step 4: Test backup functionality
    def push_to_gcr(self):               # Step 5: Push to registry

    def cleanup(self):                   # Universal cleanup
    def run_full_test(self):            # Universal orchestrator

if __name__ == '__main__':
    test = DatabaseIntegrationTest()
    success = test.run_full_test()
    sys.exit(0 if success else 1)
```

### Universal Configuration Patterns

#### Database Connection Parameters

| Database Type | Port  | Default User | Environment Variables                                  |
| ------------- | ----- | ------------ | ------------------------------------------------------ |
| PostgreSQL    | 5432  | postgres     | POSTGRES_PASSWORD, POSTGRES_DB                         |
| MySQL         | 3306  | root         | MYSQL_ROOT_PASSWORD, MYSQL_DATABASE                    |
| MongoDB       | 27017 | admin        | MONGO_INITDB_ROOT_USERNAME, MONGO_INITDB_ROOT_PASSWORD |
| ArangoDB      | 8529  | root         | ARANGO_ROOT_PASSWORD                                   |
| Redis         | 6379  | (none)       | REDIS_PASSWORD                                         |
| Cassandra     | 9042  | cassandra    | CASSANDRA_PASSWORD                                     |

#### Universal Test Data Patterns

**SQL Databases** - Standard relational schema:

```sql
CREATE TABLE movies (id [PRIMARY_KEY], title VARCHAR(255), year INT, rating DECIMAL);
CREATE TABLE actors (id [PRIMARY_KEY], name VARCHAR(255), birth_year INT);
-- Insert 3 movies, 3 actors
```

**Document Databases** - JSON collections:

```json
// movies collection
{"title": "Movie Name", "year": 1994, "rating": 9.3, "genre": "Drama"}

// actors collection
{"name": "Actor Name", "birth_year": 1937, "nationality": "American"}
```

**Key-Value Databases** - Structured keys:

```
movies:1 -> {"title": "Movie", "year": 1994}
actors:1 -> {"name": "Actor", "birth_year": 1937}
```

### Universal Pipeline Steps

#### Step 1: Start Database Container (Universal Pattern)

```python
def start_database_container(self):
    # Create isolated Docker network (universal)
    network_name = f"planb_test_network_{int(time.time())}"
    self.test_network = self.client.networks.create(network_name, driver="bridge")

    # Start database with test configuration (customize environment)
    self.container = self.client.containers.run(
        "[OFFICIAL_IMAGE]:[VERSION]",  # Database-specific
        environment={
            # Database-specific environment variables
            "[DB_PASSWORD_VAR]": self.db_password,
            "[DB_NAME_VAR]": self.test_db,
        },
        ports={'[DB_PORT]/tcp': self.db_port},  # Database-specific port
        detach=True, remove=True,
        name=self.container_name,
        network=network_name
    )

    # Wait for database to be ready (database-specific health check)
    for attempt in range(30):
        if self.check_database_ready():  # Implement per database
            break
        time.sleep(2)
```

#### Step 2: Setup Test Data (Database-Specific Implementation)

```python
def setup_test_data(self):
    """Create consistent test data using database-appropriate methods"""

    # SQL Databases: Execute CREATE TABLE and INSERT statements
    # NoSQL Databases: Create collections/documents
    # Key-Value: Set structured keys

    # Universal validation: Ensure data was created
    if self.verify_test_data():
        logger.info("✅ Test data created: 3 movies, 3 actors")
        return True
    else:
        logger.error("❌ Failed to create test data")
        return False
```

#### Step 3: Build Container (Universal)

```python
def build_container(self):
    """Build Plan B container for testing (native platform)"""

    # Universal build command (only paths change per database)
    build_result = subprocess.run([
        'docker', 'build',
        '-f', './[database]/[version]/Dockerfile',  # Database-specific path
        '-t', 'gcr.io/apito-cms/plan-b-backup-[database]:test-local',
        '.'
    ], capture_output=True, text=True, cwd='/Users/diablo/Projects/react/backup-runner')

    return build_result.returncode == 0
```

#### Step 4: Test Backup (Database-Specific Commands)

```python
def run_backup_test(self):
    """Test backup using database-specific tools"""

    backup_file = f"/tmp/planb_[database]_test_{int(time.time())}.[ext]"

    # Universal container execution, database-specific commands
    backup_result = subprocess.run([
        'docker', 'run', '--rm',
        '--network', self.test_network.name,
        '-v', '/tmp:/tmp',
        'gcr.io/apito-cms/plan-b-backup-[database]:test-local',

        # Database-specific backup command and arguments
        '[BACKUP_TOOL]',  # pg_dump, mysqldump, mongodump, etc.
        '[BACKUP_ARGS]',  # Database-specific connection and output args

    ], capture_output=True, text=True)

    # Universal validation (content varies per database)
    return self.validate_backup_content(backup_file)
```

#### Step 5: Push to Registry (Universal)

```python
def push_to_gcr(self):
    """Build production image and push to registry"""

    # Universal production build (linux/amd64 for Cloud Run)
    build_result = subprocess.run([
        'docker', 'build', '--platform', 'linux/amd64',
        '-f', './[database]/[version]/Dockerfile',
        '-t', 'gcr.io/apito-cms/plan-b-backup-[database]:[version]',
        '.'
    ])

    # Universal registry push
    push_result = subprocess.run([
        'docker', 'push', 'gcr.io/apito-cms/plan-b-backup-[database]:[version]'
    ])

    return push_result.returncode == 0
```

---

## Part 3: Universal Success Criteria

### Expected Output Flow (Database-Independent)

```
🚀 Starting [DATABASE] [VERSION] Build & Test Pipeline
============================================================
📋 Step 1: Starting test database...
[🐘|🐬|🍃|🥨|🔴] Starting [DATABASE] container...
⏳ Waiting for [DATABASE] to be ready...
✅ [DATABASE] is ready!

📋 Step 2: Setting up test data...
📊 Setting up test data...
✅ Test data created: 3 movies, 3 actors

📋 Step 3: Building Plan B container...
🔨 Building Plan B [DATABASE] container for testing...
✅ Container built successfully for local testing!

📋 Step 4: Testing backup functionality...
💾 Testing backup with our container...
▶️  Running backup using our Plan B container...
✅ [DATABASE] backup completed successfully!
✅ Backup file created: /tmp/planb_[database]_test_[timestamp].[ext] ([size] bytes)
✅ Backup contains expected [tables|collections|keys] and data

📋 Step 5: Pushing to production registry...
☁️  Building production image and pushing to GCR...
🔨 Building production image for linux/amd64...
✅ Production image built successfully!
⬆️  Pushing to Google Container Registry...
✅ Successfully pushed to Google Container Registry!
🏷️  Image: gcr.io/apito-cms/plan-b-backup-[database]:[version]

🎉 [DATABASE] [VERSION] Pipeline COMPLETED SUCCESSFULLY!
✅ Container tested and deployed to production
```

### Universal Success Criteria

For **any database type**, these must pass:

1. **Database starts** ✅ - Test database container becomes ready
2. **Test data created** ✅ - Database-appropriate data structures created
3. **Container builds** ✅ - Plan B container builds without errors
4. **Backup works** ✅ - Database backup command executes successfully
5. **Content validation** ✅ - Backup contains expected database structures
6. **Production build** ✅ - linux/amd64 container builds for Cloud Run
7. **Registry push** ✅ - Container successfully pushed to registry
8. **Cleanup** ✅ - All test resources are cleaned up

### Universal Failure Scenarios

| Failure Point      | Common Causes            | Universal Debugging                      |
| ------------------ | ------------------------ | ---------------------------------------- |
| Database startup   | Port conflicts, memory   | Check `docker ps`, try different port    |
| Test data setup    | Syntax, permissions      | Check container logs, verify credentials |
| Container build    | Dockerfile syntax, paths | Check build context, file paths          |
| Backup execution   | Network, authentication  | Test container networking, credentials   |
| Content validation | Format, empty file       | Inspect backup file contents             |
| Production build   | Platform, registry auth  | Check gcloud auth, Docker platform       |
| Registry push      | Auth, quota limits       | Verify registry permissions, disk space  |

---

## Part 4: Universal Pipeline Runner

### Unified Test Script Purpose

The `build-test-verify-push.sh` script provides **database-independent** pipeline execution:

- **Discovers** all `test.py` files recursively across database types
- **Executes** each test with timeout protection
- **Logs** detailed output per database:version
- **Reports** comprehensive success/failure statistics
- **Validates** all containers are production-ready

### Universal Usage

```bash
# Run all database tests
./build-test-verify-push.sh

# Supports any database structure:
# postgresql/16/test.py
# mysql/latest/test.py
# mongodb/7.0/test.py
# redis/latest/test.py
# [database]/[version]/test.py
```

---

## Part 5: Adding Any New Database

### Universal Process (Works for Any Database)

#### Step 1: Research Official Image

```bash
# Find official image and verify client tools exist
docker run --rm [OFFICIAL_IMAGE]:[VERSION] [CLIENT_TOOL] --version

# Examples across different database types:
docker run --rm postgres:16 pg_dump --version        # PostgreSQL
docker run --rm mysql:8.0 mysqldump --version        # MySQL
docker run --rm mongo:7.0 mongodump --version        # MongoDB
docker run --rm redis:latest redis-cli --version     # Redis
docker run --rm cassandra:4.1 cqlsh --version       # Cassandra
```

#### Step 2: Create Directory Structure

```bash
mkdir -p [database]/[version]
```

#### Step 3: Create Universal Dockerfile

```dockerfile
FROM [OFFICIAL_IMAGE]:[VERSION]
ENV DB_TYPE=[database]
ENV DB_VERSION=[version]
ENV CONTAINER_VERSION=[database]-[version]
ENTRYPOINT []
CMD []
RUN [verify-client-tools]  # Database-specific verification
# Universal labels...
```

#### Step 4: Adapt Universal test.py

1. Copy from **similar database type** (SQL vs NoSQL vs Key-Value)
2. Update **connection parameters** (port, credentials, environment)
3. Adapt **backup commands** for database's client tools
4. Modify **test data** for database's data model
5. Update **validation logic** for backup format

#### Step 5: Test & Validate

```bash
# Test single database
python3 [database]/[version]/test.py

# Test all databases (including new one)
./build-test-verify-push.sh
```

### Database Type Categories

#### SQL Databases (Relational)

- **Pattern**: Tables, rows, SQL commands
- **Examples**: PostgreSQL, MySQL, MariaDB, MSSQL, Oracle
- **Test Data**: CREATE TABLE, INSERT statements
- **Backup Tools**: `pg_dump`, `mysqldump`, `sqlcmd`

#### Document Databases (NoSQL)

- **Pattern**: Collections, documents, JSON-like
- **Examples**: MongoDB, CouchDB, ArangoDB
- **Test Data**: Collections with JSON documents
- **Backup Tools**: `mongodump`, `arangodump`

#### Key-Value Databases

- **Pattern**: Keys and values, simple operations
- **Examples**: Redis, Memcached
- **Test Data**: SET operations with structured keys
- **Backup Tools**: `redis-cli`, custom export scripts

#### Column Databases

- **Pattern**: Column families, distributed
- **Examples**: Cassandra, HBase
- **Test Data**: CREATE KEYSPACE, INSERT statements
- **Backup Tools**: `nodetool`, custom scripts

#### Graph Databases

- **Pattern**: Nodes, edges, relationships
- **Examples**: Neo4j, ArangoDB (graph mode)
- **Test Data**: CREATE nodes and relationships
- **Backup Tools**: Database-specific dump utilities

---

## Part 6: Universal Production Integration

### Cloud Run Job Template

```yaml
# Works for any database container
apiVersion: run.googleapis.com/v1
kind: Job
spec:
  template:
    spec:
      template:
        spec:
          containers:
            - image: gcr.io/[PROJECT]/plan-b-backup-[database]:[version]
              env:
                # Universal environment variables (adapt values per database)
                - name: DB_HOST
                  value: "[your-database-host]"
                - name: DB_PORT
                  value: "[database-port]"
                - name: DB_NAME
                  value: "[database-name]"
                - name: DB_USERNAME
                  value: "[username]"
                - name: DB_PASSWORD
                  value: "[password]"
                # Universal storage configuration
                - name: STORAGE_TYPE
                  value: "s3" # or gcs, azure
                - name: STORAGE_ENDPOINT
                  value: "[storage-endpoint]"
                - name: STORAGE_BUCKET
                  value: "[backup-bucket]"
                # Universal callback configuration
                - name: CALLBACK_URL
                  value: "[plan-b-api-callback-url]"
                - name: CALLBACK_SECRET
                  value: "[callback-authentication-secret]"
```

### Universal Environment Variables

**Every database container expects these standard variables:**

| Variable           | Purpose                  | Example                          |
| ------------------ | ------------------------ | -------------------------------- |
| `DB_HOST`          | Database server hostname | `localhost`, `db.example.com`    |
| `DB_PORT`          | Database server port     | `5432`, `3306`, `27017`          |
| `DB_NAME`          | Database/schema name     | `production_db`                  |
| `DB_USERNAME`      | Database username        | `postgres`, `root`, `admin`      |
| `DB_PASSWORD`      | Database password        | `secure_password`                |
| `STORAGE_TYPE`     | Backup storage type      | `s3`, `gcs`, `azure`             |
| `STORAGE_ENDPOINT` | Storage endpoint URL     | `s3.amazonaws.com`               |
| `STORAGE_BUCKET`   | Backup bucket name       | `backups-bucket`                 |
| `BACKUP_PATH`      | Path within bucket       | `daily/2025-01-15/`              |
| `CALLBACK_URL`     | Success/failure callback | `https://api.planb.com/callback` |
| `CALLBACK_SECRET`  | Callback authentication  | `webhook_secret_key`             |

---

## Part 7: Universal Maintenance

### Regular Tasks (Database-Independent)

1. **Monitor base images** - Watch for new database versions
2. **Test compatibility** - Ensure client tools work with target versions
3. **Security updates** - Rebuild when base images receive updates
4. **Performance monitoring** - Track backup sizes and execution times

### Universal Troubleshooting Steps

1. **Check container logs** in Cloud Run Console
2. **Verify network connectivity** between Cloud Run and database
3. **Test credentials** with database client tools
4. **Monitor resource usage** (CPU, memory, disk)
5. **Validate backup files** by testing restoration
6. **Check registry permissions** for image pulls

---

## Summary

This **universal guide** provides the foundation for implementing Plan B backup containers for **any database type**. The core patterns - official mirror Dockerfiles, comprehensive test pipelines, and production deployment - remain consistent regardless of the specific database technology.

**Key Principles:**

- ✅ **Use official images** as base for reliability
- ✅ **Override entrypoints** to expose client tools only
- ✅ **Test comprehensively** before production deployment
- ✅ **Follow consistent patterns** across all database types
- ✅ **Maintain version compatibility** between client and server

This approach ensures **reliable, maintainable, and scalable** backup solutions for any database in your infrastructure.
