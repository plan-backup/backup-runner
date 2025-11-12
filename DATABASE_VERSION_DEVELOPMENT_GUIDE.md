# Database Version Development Guide

## Plan B Backup Runner - Adding New Database Versions

This comprehensive guide explains how to add support for new database versions, understand the project structure, implement required components, and test/debug your implementation.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Required Files](#required-files)
4. [Step-by-Step Implementation](#step-by-step-implementation)
5. [Shared Framework Integration](#shared-framework-integration)
6. [Testing and Debugging](#testing-and-debugging)
7. [Deployment Pipeline](#deployment-pipeline)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## 🎯 Project Overview

The Plan B Backup Runner is a containerized backup solution that supports multiple database types and versions. Each database version is implemented as a separate Docker container with standardized interfaces for backup and restore operations.

### Key Features:

- **Multi-database support**: MySQL, PostgreSQL, MongoDB, Redis, etc.
- **Version-specific containers**: Each database version has its own optimized container
- **S3-compatible storage**: MinIO, AWS S3, Google Cloud Storage, etc.
- **Cloud Run integration**: Automatic job creation for production deployment
- **Comprehensive testing**: End-to-end backup and restore validation
- **Shared framework**: Common functionality to reduce code duplication

---

## 📁 Project Structure

```
backup-runner/
├── shared/                          # Shared components
│   ├── test_framework.py           # Base test framework
│   ├── backup_base.py              # Base backup runner class
│   └── entrypoint.sh               # Common container entrypoint
├── {database}/                      # Database-specific directories
│   ├── {version}/                   # Version-specific implementations
│   │   ├── Dockerfile              # Container definition
│   │   ├── runner.py               # Backup/restore logic
│   │   └── test.py                 # Integration tests
│   └── build-verify.sh             # Database-wide build script
├── build-test-verify-push.sh       # Global build and test script
├── create-runner-test-files.py     # Code generation utility
└── README.md                       # Project documentation
```

### Database Directory Examples:

- `mysql/5.7/`, `mysql/8.4/`, `mysql/9.4/`, `mysql/latest/`
- `postgresql/12/`, `postgresql/13/`, `postgresql/14/`, `postgresql/15/`, `postgresql/16/`, `postgresql/17/`
- `mongodb/4.4/`, `mongodb/5.0/`, `mongodb/6.0/`, `mongodb/7.0/`, `mongodb/8.0/`, `mongodb/latest/`
- `redis/8.2/`

---

## 📄 Required Files

### 1. **Dockerfile** - Container Definition

**Location**: `{database}/{version}/Dockerfile`

**Purpose**: Defines the Docker container with database client tools and backup runner.

**Key Requirements**:

- Base image with database client tools (not server)
- Python 3.x installation
- Required Python packages (`boto3`, `requests`)
- Shared components copied from `shared/` directory
- Environment variables for metadata
- Proper entrypoint configuration

**Template Structure**:

```dockerfile
# Plan B Database Backup Runner - {Database} {Version}
# Client tools only - no database server

FROM {database}:{version}

# Set Plan B metadata
ENV DB_TYPE={database}
ENV DB_VERSION={version}
ENV CONTAINER_VERSION={database}-{version}

# Install Python and required packages
RUN {package_manager_commands}

# Install Python dependencies
RUN pip3 install boto3 requests

# Copy shared base class
COPY shared/backup_base.py /usr/local/bin/backup_base.py

# Copy database-specific runner script
COPY {database}/{version}/runner.py /usr/local/bin/runner.py
RUN chmod +x /usr/local/bin/runner.py

# Copy shared entrypoint
COPY shared/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1
ENV OPERATION_TYPE=backup

# Override default entrypoint for client tools only
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Verify client tools are available
RUN {verify_client_tools_commands}

LABEL maintainer="Plan B Backup"
LABEL database="{database}"
LABEL version="{version}"
LABEL source="{database}:{version}"
```

### 2. **runner.py** - Backup/Restore Logic

**Location**: `{database}/{version}/runner.py`

**Purpose**: Implements database-specific backup and restore operations.

**Key Components**:

- Inherits from `backup_base.BackupBase`
- Implements `create_backup()` method
- Implements `restore_backup()` method
- Handles S3/MinIO upload/download
- Supports both backup and restore operations via `OPERATION_TYPE`

**Template Structure**:

```python
#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
import gzip
import logging
from datetime import datetime

# Add the shared directory to Python path
sys.path.append('/usr/local/bin')
from backup_base import BackupBase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class {Database}Runner(BackupBase):
    """{Database} {version} backup and restore runner"""

    def __init__(self):
        super().__init__()
        # Database-specific initialization

    def create_backup(self):
        """Create {database} backup using {client_tool}"""
        logger.info(f"🔄 Creating {Database} backup for database: {self.db_name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. Create backup using database client tool
                # 2. Compress the backup
                # 3. Upload to S3/MinIO
                # Implementation details...

                logger.info("🎉 {Database} backup, compression, and upload complete!")
                return True

            except Exception as e:
                logger.error(f"❌ Backup failed: {e}")
                raise

    def restore_backup(self):
        """Restore {database} backup using {client_tool}"""
        logger.info(f"🔄 Restoring {Database} backup for database: {self.db_name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. Download backup from S3/MinIO
                # 2. Extract the backup file
                # 3. Restore to database
                # Implementation details...

                logger.info("🎉 {Database} backup restore completed successfully!")
                return True

            except Exception as e:
                logger.error(f"❌ Restore failed: {e}")
                raise

if __name__ == '__main__':
    runner = {Database}Runner()
    operation_type = os.getenv('OPERATION_TYPE', 'backup').lower()

    try:
        if operation_type == 'backup':
            logger.info("🔄 Starting backup operation...")
            runner.create_backup()
            runner.send_callback("success", "{Database} backup completed successfully.")
        elif operation_type == 'restore':
            logger.info("🔄 Starting restore operation...")
            runner.restore_backup()
            runner.send_callback("success", "{Database} restore completed successfully.")
        else:
            logger.error(f"❌ Invalid OPERATION_TYPE: {operation_type}. Must be 'backup' or 'restore'")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        operation_name = "backup" if operation_type == "backup" else "restore"
        runner.send_callback("failure", f"{Database} {operation_name} failed: {e}")
        sys.exit(1)
```

### 3. **test.py** - Integration Tests

**Location**: `{database}/{version}/test.py`

**Purpose**: Comprehensive integration testing using the shared framework.

**Key Components**:

- Inherits from `DatabaseTestFramework`
- Implements database-specific methods
- Provides `verify_restored_data()` implementation
- Uses `run_backup_and_restore_test()` for complete testing

**Template Structure**:

```python
#!/usr/bin/env python3
import sys
import os
import subprocess
import logging

# Add the shared directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from test_framework import DatabaseTestFramework

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class {Database}IntegrationTest{VersionClass}(DatabaseTestFramework):
    """{Database} {version} specific implementation of the database test framework"""

    def __init__(self):
        super().__init__(
            db_type="{database}",
            db_version="{version}",
            db_image="{database}:{version}",
            default_port={default_port}
        )
        # Database-specific initialization

    def create_test_data(self) -> bool:
        """Create test data in {database}"""
        logger.info("📝 Creating test data in {Database}...")

        try:
            # Database-specific test data creation
            # Implementation details...

            logger.info("✅ Test data created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to setup test data: {e}")
            return False

    def get_backup_environment_vars(self) -> dict:
        """Return {database}-specific environment variables for backup"""
        import socket
        host_ip = socket.gethostbyname(socket.gethostname())

        return {
            'DB_HOST': host_ip,
            'DB_PORT': str(self.db_port),
            'DB_NAME': self.test_db,
            'DB_USERNAME': self.db_user,
            'DB_PASSWORD': self.db_password
            # Add other database-specific variables
        }

    def verify_restored_data(self) -> bool:
        """Verify that restored data matches original test data"""
        logger.info("🔍 Verifying restored data...")

        try:
            # Database-specific data verification
            # Implementation details...

            if verification_successful:
                logger.info("✅ Restored data matches original test data!")
                return True
            else:
                logger.error("❌ Restored data does not match original test data")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to verify restored data: {e}")
            return False

def main():
    """Run {database} {version} integration test using the shared framework"""
    logger.info("🚀 Starting {database} {version} Integration Test")
    test = {Database}IntegrationTest{VersionClass}()
    try:
        # Run the complete backup and restore test using the shared framework
        success = test.run_backup_and_restore_test()

        if success:
            logger.info("🎉 {database} {version} integration test completed successfully!")
            logger.info("✅ Backup, restore, and verification all passed!")
            return True
        else:
            logger.error("❌ Integration test failed")
            return False

    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False
    finally:
        test.cleanup()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
```

---

## 🚀 Step-by-Step Implementation

### Phase 1: Project Setup

1. **Create Directory Structure**

   ```bash
   mkdir -p {database}/{version}
   cd {database}/{version}
   ```

2. **Research Database Version**
   - Official Docker image name and tag
   - Client tools available in the image
   - Default ports and connection parameters
   - Backup/restore command syntax
   - Python version compatibility

### Phase 2: Container Development

3. **Create Dockerfile**

   - Start with the official database image
   - Install Python and dependencies
   - Copy shared components
   - Set proper environment variables
   - Test container builds locally

4. **Implement runner.py**
   - Inherit from `BackupBase`
   - Implement database-specific backup logic
   - Implement database-specific restore logic
   - Handle Python version compatibility (especially Python 3.6)
   - Test backup/restore operations manually

### Phase 3: Testing Infrastructure

5. **Create test.py**

   - Inherit from `DatabaseTestFramework`
   - Implement `create_test_data()`
   - Implement `get_backup_environment_vars()`
   - Implement `verify_restored_data()`
   - Test locally with shared framework

6. **Run Integration Tests**
   ```bash
   python3 {database}/{version}/test.py
   ```

### Phase 4: Production Deployment

7. **Test GCR Push**

   - Verify container builds for linux/amd64 platform
   - Test Google Container Registry authentication
   - Confirm successful push to GCR

8. **Test Cloud Run Job Creation**
   - Verify job creation in Google Cloud Console
   - Test job configuration and environment variables
   - Confirm production readiness

---

## 🔧 Shared Framework Integration

### DatabaseTestFramework Methods

**Required Implementations**:

- `create_test_data()` - Create sample data for testing
- `get_backup_environment_vars()` - Database connection parameters
- `verify_restored_data()` - Validate restored data integrity

**Inherited Methods**:

- `start_database_container()` - Start database container
- `start_minio_container()` - Start MinIO for S3 testing
- `build_container()` - Build backup runner container
- `run_backup_test()` - Execute backup operation
- `verify_backup_exists()` - Verify backup in MinIO
- `push_to_gcr()` - Push container to Google Container Registry
- `build_jobs()` - Create Cloud Run job
- `run_restore_test()` - Execute restore operation
- `run_backup_and_restore_test()` - Complete end-to-end test
- `cleanup()` - Clean up test resources

### BackupBase Class Features

**Environment Variables**:

- `JOB_ID` - Unique job identifier
- `DB_ENGINE` - Database type
- `DB_HOST`, `DB_PORT`, `DB_NAME` - Connection parameters
- `DB_USERNAME`, `DB_PASSWORD` - Authentication
- `STORAGE_*` - S3/MinIO configuration
- `BACKUP_PATH` - Backup file path
- `OPERATION_TYPE` - 'backup' or 'restore'

**Common Methods**:

- `send_callback()` - Send job status to callback URL
- S3 client initialization and configuration
- Bucket creation and management
- Error handling and logging

---

## 🧪 Testing and Debugging

### Local Testing Workflow

1. **Unit Testing**

   ```bash
   # Test container build
   docker build -f {database}/{version}/Dockerfile -t test-{database}-{version} .

   # Test backup operation
   docker run --rm -e OPERATION_TYPE=backup test-{database}-{version}

   # Test restore operation
   docker run --rm -e OPERATION_TYPE=restore test-{database}-{version}
   ```

2. **Integration Testing**

   ```bash
   # Run complete integration test
   cd /path/to/backup-runner
   python3 {database}/{version}/test.py
   ```

3. **Debug Mode**
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   python3 {database}/{version}/test.py
   ```

### Test Flow Verification

The complete test performs these operations:

1. ✅ **Database Container** - Starts database server
2. ✅ **MinIO Container** - Starts S3-compatible storage
3. ✅ **Test Data Creation** - Creates sample data
4. ✅ **Container Build** - Builds backup runner container
5. ✅ **Backup Test** - Creates and uploads backup
6. ✅ **Backup Verification** - Verifies backup exists in MinIO
7. ✅ **GCR Push** - Pushes container to Google Container Registry
8. ✅ **Cloud Run Job** - Creates production job
9. ✅ **Test Summary** - Prints comprehensive test data
10. ✅ **Restore Test** - Downloads and restores backup
11. ✅ **Data Verification** - Verifies restored data integrity
12. ✅ **Cleanup** - Removes test resources

### Common Debug Commands

```bash
# Check container logs
docker logs {container_name}

# Interactive container debugging
docker run -it --entrypoint /bin/bash test-{database}-{version}

# Test database connectivity
docker exec -it {db_container} {db_client} -h localhost -u {user} -p

# Check MinIO contents
docker exec -it {minio_container} mc ls local/planb-backups

# Verify GCR images
gcloud container images list --repository=gcr.io/apito-cms

# Check Cloud Run jobs
gcloud run jobs list --region=us-central1
```

### Test Data Validation

Ensure your `verify_restored_data()` method checks:

- **Table/Collection existence** - Verify schema restoration
- **Row/Document counts** - Verify data completeness
- **Specific data values** - Verify data integrity
- **Indexes and constraints** - Verify structural elements

---

## 🚀 Deployment Pipeline

### Automated Build Process

The project includes automated build scripts:

1. **Global Build Script**

   ```bash
   ./build-test-verify-push.sh
   ```

   - Discovers all database versions
   - Runs integration tests
   - Builds and pushes to GCR
   - Creates Cloud Run jobs

2. **Database-Specific Build**
   ```bash
   ./mysql/build-verify.sh  # Example for MySQL
   ```

### Production Deployment Steps

1. **Container Registry**

   - Images pushed to `gcr.io/apito-cms/plan-b-backup-{database}:{version}`
   - Platform: `linux/amd64`
   - Multi-architecture support available

2. **Cloud Run Jobs**

   - Job name: `plan-b-backup-{database}-{version-normalized}`
   - Region: `us-central1`
   - Memory: 2Gi, CPU: 1
   - Timeout: 3600 seconds

3. **Environment Variables**
   - All required database connection parameters
   - S3/storage configuration
   - Callback URLs for status reporting

---

## 🔍 Troubleshooting

### Common Issues and Solutions

#### Container Build Issues

**Problem**: Package installation failures

```
Solution: Check base image package manager
- Debian/Ubuntu: apt-get update && apt-get install
- CentOS/RHEL: yum install or dnf install
- Alpine: apk add --no-cache
```

**Problem**: Python compatibility issues

```
Solution: Check Python version in base image
- Python 3.6: Use subprocess.run(stdout=PIPE, stderr=PIPE, universal_newlines=True)
- Python 3.7+: Use subprocess.run(capture_output=True, text=True)
```

#### Database Connection Issues

**Problem**: Connection refused during testing

```
Solution:
1. Check database startup time (add longer wait)
2. Verify port mapping in test framework
3. Check host networking configuration
4. Validate database initialization scripts
```

**Problem**: Authentication failures

```
Solution:
1. Verify default credentials in database image
2. Check environment variable names
3. Validate connection string format
4. Test manual connection first
```

#### Backup/Restore Issues

**Problem**: Backup command failures

```
Solution:
1. Test backup command manually in container
2. Check client tool version compatibility
3. Verify database permissions
4. Validate command-line arguments
```

**Problem**: MinIO upload/download failures

```
Solution:
1. Check MinIO container networking
2. Verify S3 client configuration
3. Test with boto3 fallback
4. Check endpoint URL format
```

#### Test Framework Issues

**Problem**: Test timeouts or hangs

```
Solution:
1. Increase wait times for database startup
2. Check container resource limits
3. Verify cleanup in finally blocks
4. Add more detailed logging
```

**Problem**: Data verification failures

```
Solution:
1. Add debug logging to verification methods
2. Check test data creation logic
3. Verify restore process completeness
4. Compare original vs restored data manually
```

### Debug Logging

Add comprehensive logging to your implementations:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add debug logs at key points
logger.debug(f"Database connection: {host}:{port}")
logger.debug(f"Backup command: {' '.join(backup_cmd)}")
logger.debug(f"Backup file size: {os.path.getsize(backup_file)} bytes")
logger.debug(f"S3 upload response: {response}")
```

---

## 📚 Best Practices

### Code Quality

1. **Error Handling**

   - Use try/except blocks for all external operations
   - Provide meaningful error messages
   - Log errors with context information
   - Clean up resources in finally blocks

2. **Logging**

   - Use structured logging with consistent format
   - Include operation context (database, version, operation)
   - Log both success and failure cases
   - Use appropriate log levels (DEBUG, INFO, ERROR)

3. **Resource Management**
   - Use context managers for temporary files
   - Clean up containers and networks
   - Handle resource limits gracefully
   - Implement proper timeout handling

### Security Considerations

1. **Credentials**

   - Never hardcode passwords or keys
   - Use environment variables for sensitive data
   - Validate input parameters
   - Implement proper authentication

2. **Network Security**
   - Use secure connections when possible
   - Validate SSL certificates
   - Implement proper firewall rules
   - Use least privilege access

### Performance Optimization

1. **Container Size**

   - Use multi-stage builds when beneficial
   - Remove unnecessary packages
   - Optimize layer caching
   - Use appropriate base images

2. **Backup Efficiency**
   - Use streaming compression
   - Implement incremental backups when possible
   - Optimize database dump parameters
   - Use parallel operations where applicable

### Documentation

1. **Code Comments**

   - Document complex logic
   - Explain database-specific quirks
   - Include example commands
   - Reference official documentation

2. **Version Notes**
   - Document version-specific differences
   - Note compatibility requirements
   - Include migration guides
   - Update changelog entries

---

## 📖 Reference Examples

### Working Implementations

Study these existing implementations for reference:

1. **MySQL Versions**

   - `mysql/5.7/` - Python 3.6 compatibility example
   - `mysql/8.4/` - Modern MySQL features
   - `mysql/9.4/` - Latest MySQL version
   - `mysql/latest/` - Rolling latest version

2. **PostgreSQL Versions**

   - `postgresql/12/` through `postgresql/17/`
   - Different client tool versions
   - Various authentication methods

3. **MongoDB Versions**
   - `mongodb/4.4/` through `mongodb/latest/`
   - Document database backup strategies
   - Replica set considerations

### Code Generation

Use the provided utility for scaffolding:

```bash
python3 create-runner-test-files.py
```

This generates template files based on database configuration and can speed up initial development.

---

## 🎯 Validation Checklist

Before submitting your implementation:

### ✅ Container Requirements

- [ ] Container builds successfully
- [ ] Base image contains only client tools (no server)
- [ ] Python dependencies installed correctly
- [ ] Shared components copied properly
- [ ] Environment variables set correctly
- [ ] Entrypoint configured properly

### ✅ Backup Functionality

- [ ] Database backup creates successfully
- [ ] Backup file compresses properly
- [ ] Upload to MinIO/S3 works
- [ ] Error handling implemented
- [ ] Logging provides useful information
- [ ] Callback system works

### ✅ Restore Functionality

- [ ] Backup downloads successfully
- [ ] File extraction works properly
- [ ] Database restoration completes
- [ ] New database created if needed
- [ ] Data integrity maintained
- [ ] Error recovery implemented

### ✅ Testing Framework

- [ ] Inherits from DatabaseTestFramework
- [ ] Test data creation works
- [ ] Environment variables correct
- [ ] Data verification comprehensive
- [ ] Integration test passes
- [ ] Cleanup removes all resources

### ✅ Production Deployment

- [ ] GCR push successful
- [ ] Cloud Run job created
- [ ] Container runs in production environment
- [ ] All environment variables supported
- [ ] Monitoring and logging configured

### ✅ Documentation

- [ ] Code properly commented
- [ ] Version-specific notes included
- [ ] Examples provided
- [ ] Troubleshooting guide updated

---

## 🆘 Getting Help

### Resources

1. **Official Documentation**

   - Database-specific backup/restore guides
   - Docker image documentation
   - Cloud platform documentation

2. **Community Support**

   - Database community forums
   - Stack Overflow for specific issues
   - GitHub issues for project-specific problems

3. **Internal Resources**
   - Existing implementations as examples
   - Shared framework documentation
   - Team knowledge base

### Reporting Issues

When reporting issues, include:

- Database type and version
- Container build logs
- Test execution logs
- Environment details
- Steps to reproduce
- Expected vs actual behavior

---

**Happy coding! 🚀**

This guide should help you successfully add support for new database versions to the Plan B Backup Runner. Remember to test thoroughly and follow the established patterns for consistency across the project.
