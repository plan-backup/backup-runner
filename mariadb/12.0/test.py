#!/usr/bin/env python3
"""
Plan B MariaDB Latest (12.0.2) Integration Test
Tests backup, compression, and S3 upload functionality
"""

import os
import sys
import time
import logging
import subprocess
import tempfile
import docker
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class MariaDBIntegrationTest120:
    def __init__(self):
        """Initialize MariaDB 12.0 integration test"""
        self.client = docker.from_env()
        self.db_port = 3306 + int(time.time()) % 1000
        self.test_db = "planb_testdb"
        self.mariadb_user = "testuser"
        self.mariadb_password = "testpass123"
        self.container = None
        self.container_name = f"planb_test_mariadb_120_{int(time.time())}"
        self.test_network = None
        
        # MinIO S3-compatible storage for testing
        self.minio_container = None
        self.minio_container_name = f"planb_test_minio_{int(time.time())}"
        self.minio_port = 9000 + int(time.time()) % 1000
        self.minio_access_key = "minioadmin"
        self.minio_secret_key = "minioadmin"
        self.minio_bucket = "test-backups"

    def start_database_container(self):
        """Start MariaDB 12.0 container for testing"""
        logger.info("🐬 Starting MariaDB 12.0 container...")
        
        try:
            # Create a custom network for test containers
            network_name = f"planb_test_network_{int(time.time())}"
            self.test_network = self.client.networks.create(network_name, driver="bridge")
            
            # Start MariaDB container on custom network
            self.container = self.client.containers.run(
                "mariadb:12.0",
                environment={
                    "MARIADB_ROOT_PASSWORD": self.mariadb_password,
                    "MARIADB_DATABASE": self.test_db,
                    "MARIADB_USER": self.mariadb_user,
                    "MARIADB_PASSWORD": self.mariadb_password,
                },
                ports={'3306/tcp': self.db_port},
                detach=True,
                remove=True,
                name=self.container_name,
                network=network_name  # Connect to custom network
            )
            logger.info(f"✅ MariaDB container '{self.container_name}' started on port {self.db_port}")
            
            # Wait for MariaDB to be ready
            logger.info("⏳ Waiting for MariaDB to be ready...")
            max_attempts = 30  # Reduced timeout for faster feedback
            for attempt in range(max_attempts):
                try:
                    # Test MariaDB connection using mariadb client
                    result = subprocess.run([
                        'docker', 'exec', self.container_name,
                        'mariadb', '-u', self.mariadb_user, f'-p{self.mariadb_password}', '-e', 'SELECT 1;'
                    ], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        logger.info("✅ MariaDB is ready!")
                        break
                    else:
                        logger.info(f"Attempt {attempt + 1}: MariaDB not ready yet (return code: {result.returncode})")
                        if result.stderr:
                            logger.info(f"Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    logger.info(f"Attempt {attempt + 1}: Connection timeout")
                except Exception as e:
                    logger.info(f"Attempt {attempt + 1}: Exception: {e}")
                time.sleep(1)  # Reduced sleep time
                if attempt == max_attempts - 1:
                    raise Exception("MariaDB failed to start within timeout")
            
            return True
                            
        except Exception as e:
            logger.error(f"❌ Failed to start MariaDB container: {e}")
            return False

    def setup_test_data(self):
        """Setup test data in MariaDB"""
        logger.info("📊 Setting up test data...")
        
        try:
            # Create test tables and insert sample data
            setup_commands = [
                f"USE {self.test_db}; CREATE TABLE IF NOT EXISTS movies (id INT PRIMARY KEY, title VARCHAR(255), year INT);",
                f"USE {self.test_db}; CREATE TABLE IF NOT EXISTS actors (id INT PRIMARY KEY, name VARCHAR(255), movie_id INT);",
                f"USE {self.test_db}; INSERT INTO movies (id, title, year) VALUES (1, 'The Matrix', 1999), (2, 'Inception', 2010);",
                f"USE {self.test_db}; INSERT INTO actors (id, name, movie_id) VALUES (1, 'Keanu Reeves', 1), (2, 'Leonardo DiCaprio', 2);",
                f"USE {self.test_db}; INSERT INTO actors (id, name, movie_id) VALUES (1, 'Keanu Reeves', 1), (2, 'Leonardo DiCaprio', 2);"
            ]
            
            for cmd in setup_commands:
                result = subprocess.run([
                    'docker', 'exec', self.container_name,
                    'mariadb', '-u', self.mariadb_user, f'-p{self.mariadb_password}', '-e', cmd
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    logger.warning(f"Command failed: {cmd}, Error: {result.stderr}")
            
            logger.info("✅ Test data setup complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup test data: {e}")
            return False

    def start_minio_container(self):
        """Start MinIO container for S3-compatible storage testing"""
        logger.info("☁️  Starting MinIO container...")
        
        try:
            # Start MinIO container
            self.minio_container = self.client.containers.run(
                "minio/minio:latest",
                command=["server", "/data", "--console-address", ":9001"],
                environment={
                    "MINIO_ROOT_USER": self.minio_access_key,
                    "MINIO_ROOT_PASSWORD": self.minio_secret_key,
                },
                ports={'9000/tcp': self.minio_port, '9001/tcp': self.minio_port + 1},
                detach=True,
                remove=True,
                name=self.minio_container_name,
                network=self.test_network.name
            )
            
            logger.info(f"✅ MinIO container '{self.minio_container_name}' started on port {self.minio_port}")
            
            # Wait for MinIO to be ready
            logger.info("⏳ Waiting for MinIO to be ready...")
            time.sleep(10)  # Give MinIO time to start
            
            # Create test bucket
            self._create_minio_bucket()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start MinIO container: {e}")
            return False

    def _create_minio_bucket(self):
        """Create test bucket in MinIO"""
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=f'http://localhost:{self.minio_port}',
                aws_access_key_id=self.minio_access_key,
                aws_secret_access_key=self.minio_secret_key
            )
            s3_client.create_bucket(Bucket=self.minio_bucket)
            logger.info(f"✅ Created MinIO bucket: {self.minio_bucket}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to create MinIO bucket: {e}")

    def build_container(self):
        """Build the MariaDB backup container"""
        logger.info("🔨 Building MariaDB 12.0 backup container...")
        
        try:
            # Build the container
            image, build_logs = self.client.images.build(
                path="/Users/diablo/Projects/react/backup-runner/mariadb/12.0",
                dockerfile="Dockerfile",
                tag="gcr.io/apito-cms/plan-b-backup-mariadb:test-120",
                rm=True
            )
            
            logger.info("✅ MariaDB 12.0 backup container built successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to build MariaDB container: {e}")
            return False

    def run_backup_test(self):
        """Run the backup test using the built container"""
        logger.info("🧪 Running MariaDB 12.0 backup test...")
        
        try:
            # Run the backup container
            backup_container = self.client.containers.run(
                "gcr.io/apito-cms/plan-b-backup-mariadb:test-120",
                command=["python3", "/usr/local/bin/runner.py"],
                environment={
                    'DB_HOST': 'host.docker.internal',
                    'DB_PORT': str(self.db_port),
                    'DB_NAME': self.test_db,
                    'DB_USERNAME': self.mariadb_user,
                    'DB_PASSWORD': self.mariadb_password,
                    'STORAGE_ENDPOINT': f'http://host.docker.internal:{self.minio_port}',
                    'STORAGE_BUCKET': self.minio_bucket,
                    'STORAGE_ACCESS_KEY_ID': self.minio_access_key,
                    'STORAGE_SECRET_ACCESS_KEY': self.minio_secret_key,
                    'BACKUP_PATH': f'{self.test_db}_backup.sql.gz'
                },
                detach=True,
                remove=True,
                network_mode="host"
            )
            
            # Wait for backup to complete
            result = backup_container.wait(timeout=300)
            
            if result['StatusCode'] == 0:
                logger.info("✅ MariaDB 12.0 backup test completed successfully")
                
                # Verify backup was uploaded to MinIO
                self._verify_backup_in_minio()
                return True
            else:
                logger.error(f"❌ MariaDB backup test failed with exit code: {result['StatusCode']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to run MariaDB backup test: {e}")
            return False

    def _verify_backup_in_minio(self):
        """Verify backup was uploaded to MinIO"""
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=f'http://localhost:{self.minio_port}',
                aws_access_key_id=self.minio_access_key,
                aws_secret_access_key=self.minio_secret_key
            )
            
            # List objects in bucket
            response = s3_client.list_objects_v2(Bucket=self.minio_bucket)
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.sql.gz'):
                        logger.info(f"✅ Backup verified in MinIO: {obj['Key']} ({obj['Size']} bytes)")
                        return True
            
            logger.warning("⚠️  No backup files found in MinIO")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to verify backup in MinIO: {e}")
            return False

    def push_to_gcr(self):
        """Push the built container to Google Container Registry"""
        logger.info("🚀 Pushing MariaDB 12.0 container to GCR...")
        
        try:
            # Build for linux/amd64 platform (Cloud Run requirement)
            image, build_logs = self.client.images.build(
                path="/Users/diablo/Projects/react/backup-runner/mariadb/12.0",
                dockerfile="Dockerfile",
                tag="gcr.io/apito-cms/plan-b-backup-mariadb:12.0",
                platform="linux/amd64",
                rm=True
            )
            
            # Push to GCR
            for line in self.client.images.push(
                "gcr.io/apito-cms/plan-b-backup-mariadb:12.0",
                stream=True,
                decode=True
            ):
                if 'status' in line:
                    logger.info(f"Push status: {line['status']}")
            
            logger.info("✅ MariaDB 12.0 container pushed to GCR successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to push MariaDB container to GCR: {e}")
            return False

    def cleanup(self):
        """Clean up test containers and networks"""
        logger.info("🧹 Cleaning up...")
        
        try:
            if self.container:
                self.container.stop()
            if self.minio_container:
                self.minio_container.stop()
            if self.test_network:
                self.test_network.remove()
            logger.info("✅ Test network removed")
        except Exception as e:
            logger.warning(f"⚠️  Cleanup warning: {e}")

    def run_full_test(self):
        """Run the complete MariaDB 12.0 integration test"""
        logger.info("🚀 Starting MariaDB 12.0 Build & Test Pipeline")
        logger.info("=" * 60)
        
        try:
            # Step 1: Start test database
            logger.info("📋 Step 1: Starting test database...")
            if not self.start_database_container():
                return False
            
            # Step 2: Setup test data
            logger.info("📋 Step 2: Setting up test data...")
            if not self.setup_test_data():
                return False
            
            # Step 3: Start MinIO
            logger.info("📋 Step 3: Starting MinIO...")
            if not self.start_minio_container():
                return False
            
            # Step 4: Build container
            logger.info("📋 Step 4: Building backup container...")
            if not self.build_container():
                return False
            
            # Step 5: Run backup test
            logger.info("📋 Step 5: Running backup test...")
            if not self.run_backup_test():
                return False
            
            # Step 6: Push to GCR
            logger.info("📋 Step 6: Pushing to GCR...")
            if not self.push_to_gcr():
                return False
            
            logger.info("🎉 MariaDB 12.0 integration test completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ MariaDB 12.0 integration test failed: {e}")
            return False
        finally:
            self.cleanup()

if __name__ == '__main__':
    test = MariaDBIntegrationTest120()
    success = test.run_full_test()
    sys.exit(0 if success else 1)
