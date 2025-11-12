#!/usr/bin/env python3
"""
Plan B Database Integration Test Framework
Shared library for common test functionality across all database types and versions
"""

import os
import sys
import time
import logging
import docker
import subprocess
import requests
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseTestFramework(ABC):
    """Base class for database integration tests with common functionality"""
    
    def __init__(self, db_type: str, db_version: str, db_image: str, default_port: int):
        """
        Initialize the test framework
        
        Args:
            db_type: Database type (e.g., 'redis', 'mongodb', 'postgresql')
            db_version: Database version (e.g., '8.2', '4.4', '16')
            db_image: Docker image for the database (e.g., 'redis:8.2')
            default_port: Default port for the database
        """
        self.db_type = db_type
        self.db_version = db_version
        self.db_image = db_image
        self.default_port = default_port
        
        # Docker client
        self.client = docker.from_env()
        
        # Container management
        self.container = None
        self.minio_container = None
        self.test_network = None
        self.container_name = None
        self.minio_container_name = None
        
        # Dynamic ports to avoid conflicts
        self.db_port = default_port + int(time.time()) % 1000
        self.minio_port = 9000 + int(time.time()) % 1000
        
        # MinIO configuration
        self.minio_access_key = "minioadmin"
        self.minio_secret_key = "minioadmin"
        self.minio_bucket = "planb-backups"
        
        # Cloud Run configuration
        self.project_id = "apito-cms"
        self.region = "us-central1"
        self.service_account = "plan-b-service-account@apito-cms.iam.gserviceaccount.com"
    
    def start_database_container(self):
        """Start the database container for testing"""
        logger.info(f"🚀 Starting {self.db_type} {self.db_version} container...")
        
        try:
            # Create a custom network for test containers
            network_name = f"planb_test_network_{int(time.time())}"
            self.test_network = self.client.networks.create(network_name, driver="bridge")
            self.container_name = f"planb_test_{self.db_type}_{self.db_version.replace('.', '_')}_{int(time.time())}"
            
            # Start database container on custom network
            self.container = self.client.containers.run(
                self.db_image,
                ports={f'{self.default_port}/tcp': self.db_port},
                detach=True,
                remove=True,
                name=self.container_name,
                network=network_name,
                **self.get_database_container_config()
            )
            
            logger.info(f"✅ {self.db_type} container '{self.container_name}' started on port {self.db_port}")
            
            # Wait for database to be ready
            logger.info(f"⏳ Waiting for {self.db_type} to be ready...")
            if self.wait_for_database_ready():
                logger.info(f"✅ {self.db_type} is ready!")
                return True
            else:
                raise Exception(f"{self.db_type} failed to start within timeout")
                
        except Exception as e:
            logger.error(f"❌ Failed to start {self.db_type} container: {e}")
            raise
    
    def start_minio_container(self):
        """Start MinIO container for S3-compatible storage testing"""
        logger.info("☁️  Starting MinIO container...")
        
        try:
            self.minio_container_name = f"planb_test_minio_{int(time.time())}"
            
            # Start MinIO container on default bridge network for proper port mapping
            self.minio_container = self.client.containers.run(
                "minio/minio:latest",
                command=["server", "/data", "--console-address", ":9001"],
                environment={
                    'MINIO_ROOT_USER': self.minio_access_key,
                    'MINIO_ROOT_PASSWORD': self.minio_secret_key,
                    'MINIO_DOMAIN': 'localhost',  # Allow localhost domain
                    'MINIO_SERVER_URL': f'http://localhost:{self.minio_port}'  # Use localhost for host access
                },
                detach=True,
                remove=False,  # Don't remove immediately to debug port mapping
                name=self.minio_container_name,
                ports={'9000/tcp': self.minio_port}  # Port mapping on default bridge network
            )
            
            logger.info(f"✅ MinIO container '{self.minio_container_name}' started on port {self.minio_port}")
            
            # Wait for MinIO to be ready
            logger.info("⏳ Waiting for MinIO to be ready...")
            time.sleep(10)  # Give MinIO time to start
            
            # Create bucket using MinIO client
            logger.info("🪣 Creating MinIO bucket...")
            try:
                create_bucket_cmd = [
                    'docker', 'run', '--rm',
                    '--network', 'bridge',  # Use bridge network to access MinIO
                    'minio/mc:latest',
                    'mc', 'alias', 'set', 'myminio', f'http://{self.minio_container_name}:9000', self.minio_access_key, self.minio_secret_key
                ]
                subprocess.run(create_bucket_cmd, capture_output=True, text=True, timeout=30)
                
                create_bucket_cmd = [
                    'docker', 'run', '--rm',
                    '--network', 'bridge',  # Use bridge network to access MinIO
                    'minio/mc:latest',
                    'mc', 'mb', f'myminio/{self.minio_bucket}'
                ]
                result = subprocess.run(create_bucket_cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("✅ MinIO bucket created successfully!")
                else:
                    logger.warning(f"⚠️  Bucket creation warning: {result.stderr}")
            except Exception as e:
                logger.warning(f"⚠️  Bucket creation failed: {e}")
            
            logger.info("✅ MinIO is ready!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start MinIO container: {e}")
            raise
    
    def build_container(self):
        """Build the Plan B backup container for testing"""
        logger.info(f"🔨 Building Plan B {self.db_type} container for testing...")
        
        try:
            test_tag = f'gcr.io/apito-cms/plan-b-backup-{self.db_type}:test-{self.db_version}'
            dockerfile_path = f'./{self.db_type}/{self.db_version}/Dockerfile'
            
            # Build for linux/amd64 for consistency
            build_result = subprocess.run([
                'docker', 'build', '--platform', 'linux/amd64',
                '-f', dockerfile_path,
                '-t', test_tag,
                '.'
            ], capture_output=True, text=True, cwd='/Users/diablo/Projects/react/backup-runner')
            
            if build_result.returncode != 0:
                raise Exception(f"Failed to build container: {build_result.stderr}")
            
            logger.info("✅ Container built successfully for local testing!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Container build failed: {e}")
            return False
    
    def run_backup_test(self, custom_backup_filename=None):
        """Test backup functionality"""
        logger.info(f"🧪 Testing {self.db_type} backup functionality...")
        
        try:
            test_tag = f'gcr.io/apito-cms/plan-b-backup-{self.db_type}:test-{self.db_version}'
            
            if custom_backup_filename:
                backup_path = custom_backup_filename
                logger.info(f"🔍 Using custom backup filename: {backup_path}")
            else:
                backup_path = f'{self.db_type}-{self.db_version}-test-backup-{int(time.time())}.tar.gz'
                logger.info(f"🔍 Using generated backup filename: {backup_path}")
            
            # Use host networking and MinIO's exposed port
            minio_endpoint = f'http://127.0.0.1:{self.minio_port}'
            logger.info(f"🔍 Using MinIO endpoint: {minio_endpoint}")
            logger.info(f"🔍 Using DB host: {self.container_name}")
            logger.info(f"🔍 Test network name: {self.test_network.name}")
            
            # Get database-specific environment variables
            env_vars = {
                'JOB_ID': f'test-{self.db_type}-{self.db_version}-{int(time.time())}',
                'DB_ENGINE': self.db_type,
                'STORAGE_TYPE': 's3',
                'STORAGE_ENDPOINT': minio_endpoint,
                'STORAGE_BUCKET': self.minio_bucket,
                'STORAGE_ACCESS_KEY_ID': self.minio_access_key,
                'STORAGE_SECRET_ACCESS_KEY': self.minio_secret_key,
                'STORAGE_REGION': 'us-east-1',
                'BACKUP_PATH': backup_path,
                'CALLBACK_URL': 'http://localhost:3000/test-callback',
                'CALLBACK_SECRET': 'test-secret',
            }
            
            # Add database-specific environment variables
            env_vars.update(self.get_backup_environment_vars())
            
            # Run backup using our container with host networking
            backup_container = self.client.containers.run(
                test_tag,
                environment=env_vars,
                network='host',  # Use host network to access MinIO
                detach=True,  # Run in detached mode
                tty=False,
                stream=False
            )
            
            # Wait for the backup container to complete
            result = backup_container.wait()
            logs = backup_container.logs().decode('utf-8')
            
            # Remove the backup container
            backup_container.remove()
            
            logger.info(f"✅ Backup test completed: {logs}")
            return result['StatusCode'] == 0
            
        except Exception as e:
            logger.error(f"❌ Backup test failed: {e}")
            return False
    
    def verify_backup_exists(self):
        """Verify backup was created in MinIO"""
        logger.info("🔍 Verifying backup exists in MinIO...")
        
        try:
            # First, set up MinIO client alias using the bridge network
            alias_cmd = [
                'docker', 'run', '--rm',
                '--network', 'bridge',  # Use bridge network to access MinIO
                'minio/mc:latest',
                'mc', 'alias', 'set', 'myminio', f'http://{self.minio_container_name}:9000', 
                self.minio_access_key, self.minio_secret_key
            ]
            
            alias_result = subprocess.run(alias_cmd, capture_output=True, text=True, timeout=30)
            if alias_result.returncode != 0:
                logger.error(f"❌ Failed to set MinIO alias: {alias_result.stderr}")
                return False
            
            # List objects in MinIO bucket
            list_cmd = [
                'docker', 'run', '--rm',
                '--network', 'bridge',  # Use bridge network to access MinIO
                'minio/mc:latest',
                'mc', 'ls', f'myminio/{self.minio_bucket}'
            ]
            
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"✅ MinIO bucket contents:")
                logger.info(f"Raw output: '{result.stdout}'")
                logger.info(f"Output length: {len(result.stdout)}")
                
                # Also try to list all buckets to see what exists
                list_buckets_cmd = [
                    'docker', 'run', '--rm',
                    '--network', 'bridge',
                    'minio/mc:latest',
                    'mc', 'ls', 'myminio'
                ]
                bucket_result = subprocess.run(list_buckets_cmd, capture_output=True, text=True, timeout=30)
                logger.info(f"✅ Available buckets: {bucket_result.stdout}")
                
                # Check if our backup file exists
                backup_pattern = f'{self.db_type}-{self.db_version}-test-backup'
                if backup_pattern in result.stdout:
                    logger.info(f"✅ Backup file found in MinIO: {backup_pattern}")
                    return True
                else:
                    logger.error(f"❌ Backup file not found in MinIO. Expected pattern: {backup_pattern}")
                    logger.error(f"❌ Actual bucket contents: '{result.stdout}'")
                    logger.error(f"❌ Bucket contents length: {len(result.stdout)}")
                    
                    # Let's also try to connect using the same method as the backup container
                    logger.info("🔍 Trying alternative verification using boto3...")
                    return self._verify_with_boto3()
            else:
                logger.error(f"❌ Failed to list MinIO bucket: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to verify backup: {e}")
            return False
    
    def _verify_with_boto3(self):
        """Verify backup using boto3 - same method as backup container"""
        try:
            import boto3
            import botocore.config
            
            # Use the same configuration as the backup container
            config = botocore.config.Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'},
                retries={'max_attempts': 3}
            )
            
            s3_client = boto3.client(
                's3',
                endpoint_url=f'http://127.0.0.1:{self.minio_port}',
                aws_access_key_id=self.minio_access_key,
                aws_secret_access_key=self.minio_secret_key,
                region_name='us-east-1',
                config=config,
                use_ssl=False
            )
            
            # List objects in the bucket
            response = s3_client.list_objects_v2(Bucket=self.minio_bucket)
            
            if 'Contents' in response:
                logger.info("✅ Files found in bucket using boto3:")
                backup_pattern = f'{self.db_type}-{self.db_version}-test-backup'
                for obj in response['Contents']:
                    logger.info(f"  - {obj['Key']} (Size: {obj['Size']} bytes)")
                    if backup_pattern in obj['Key']:
                        logger.info(f"✅ Backup file found using boto3: {obj['Key']}")
                        return True
                
                logger.error(f"❌ Backup file not found using boto3. Expected pattern: {backup_pattern}")
                return False
            else:
                logger.error("❌ No files found in bucket using boto3")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to verify using boto3: {e}")
            return False
    
    def push_to_gcr(self):
        """Build and push container to Google Container Registry"""
        logger.info(f"🚀 Building and pushing {self.db_type} {self.db_version} container to GCR...")
        
        try:
            production_tag = f'gcr.io/apito-cms/plan-b-backup-{self.db_type}:{self.db_version}'
            dockerfile_path = f'./{self.db_type}/{self.db_version}/Dockerfile'
            
            # Build for linux/amd64 and push to GCR
            build_result = subprocess.run([
                'docker', 'build', '--platform', 'linux/amd64',
                '-f', dockerfile_path,
                '-t', production_tag,
                '.'
            ], capture_output=True, text=True, cwd='/Users/diablo/Projects/react/backup-runner')
            
            if build_result.returncode != 0:
                raise Exception(f"Failed to build container: {build_result.stderr}")
            
            # Push to GCR
            push_result = subprocess.run([
                'docker', 'push', production_tag
            ], capture_output=True, text=True)
            
            if push_result.returncode != 0:
                raise Exception(f"Failed to push container: {push_result.stderr}")
            
            logger.info(f"✅ {self.db_type} {self.db_version} container pushed to GCR successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to push to GCR: {e}")
            return False
    
    def build_jobs(self):
        """Create Cloud Run job after successful image push"""
        logger.info(f"🔧 Creating Cloud Run job for {self.db_type} {self.db_version}...")
        
        try:
            container_image = f'gcr.io/apito-cms/plan-b-backup-{self.db_type}:{self.db_version}'
            
            # Sanitize version name for Cloud Run job naming
            sanitized_version = self.db_version.replace('.', '-').lower()
            job_name = f"plan-b-backup-{self.db_type}-{sanitized_version}"
            
            logger.info(f"📦 Creating job: {job_name}")
            logger.info(f"Image: {container_image}")
            
            # Check if job already exists
            check_result = subprocess.run([
                'gcloud', 'run', 'jobs', 'describe', job_name,
                '--region', self.region,
                '--quiet'
            ], capture_output=True, text=True)
            
            if check_result.returncode == 0:
                logger.info(f"⚠️ Job {job_name} already exists - skipping")
                return True
            
            # Create Cloud Run job
            create_result = subprocess.run([
                'gcloud', 'run', 'jobs', 'create', job_name,
                '--image', container_image,
                '--region', self.region,
                '--memory', '4Gi',
                '--cpu', '2',
                '--tasks', '1',
                '--parallelism', '10',
                '--task-timeout', '3600',
                '--max-retries', '1',
                '--service-account', self.service_account,
                '--quiet'
            ], capture_output=True, text=True)
            
            if create_result.returncode != 0:
                raise Exception(f"Failed to create job: {create_result.stderr}")
            
            logger.info(f"✅ Cloud Run job {job_name} created successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create Cloud Run job: {e}")
            return False

    def print_data(self):
        """Print all important test data and verify backup exists in MinIO"""
        logger.info("📊 Printing test data summary...")
        
        # Container information
        test_tag = f'gcr.io/apito-cms/plan-b-backup-{self.db_type}:test-{self.db_version}'
        production_tag = f'gcr.io/apito-cms/plan-b-backup-{self.db_type}:{self.db_version}'
        
        # Job information
        sanitized_version = self.db_version.replace('.', '-').lower()
        job_name = f"plan-b-backup-{self.db_type}-{sanitized_version}"
        
        # Backup information
        backup_filename = f"{self.db_type}-{self.db_version}-test-backup-{int(time.time())}.tar.gz"
        
        logger.info("=" * 80)
        logger.info("📋 TEST DATA SUMMARY")
        logger.info("=" * 80)
        logger.info(f"🗄️  Database Type: {self.db_type}")
        logger.info(f"📦 Database Version: {self.db_version}")
        logger.info(f"🐳 Test Container: {test_tag}")
        logger.info(f"🚀 Production Container: {production_tag}")
        logger.info(f"⚙️  Cloud Run Job: {job_name}")
        logger.info(f"📁 Backup Filename: {backup_filename}")
        logger.info(f"☁️  MinIO Container: {self.minio_container_name}")
        logger.info(f"🪣 MinIO Bucket: {self.minio_bucket}")
        logger.info(f"🌐 MinIO Endpoint: http://{self.minio_container_name}:9000")
        logger.info("=" * 80)
        
        # Verify backup exists in MinIO
        logger.info("🔍 Verifying backup exists in MinIO...")
        try:
            # List objects in MinIO bucket
            list_cmd = [
                'docker', 'run', '--rm',
                '--network', self.test_network.name,
                'minio/mc:latest',
                'mc', 'ls', f'myminio/{self.minio_bucket}'
            ]
            
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("✅ MinIO bucket contents:")
                logger.info(result.stdout)
                
                # Check if our backup file exists
                backup_pattern = f'{self.db_type}-{self.db_version}-test-backup'
                if backup_pattern in result.stdout:
                    logger.info(f"✅ Backup file found in MinIO: {backup_pattern}")
                else:
                    logger.warning(f"⚠️  Backup file not found in MinIO: {backup_pattern}")
            else:
                logger.error(f"❌ Failed to list MinIO bucket: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Failed to verify backup in MinIO: {e}")
        
        logger.info("=" * 80)
        logger.info("📊 Test data summary completed!")
        logger.info("=" * 80)

    def cleanup(self):
        """Clean up test containers and network"""
        logger.info("🧹 Cleaning up test resources...")
        
        try:
            if self.container:
                self.container.stop()
            if self.minio_container:
                self.minio_container.stop()
            if self.test_network:
                self.test_network.remove()
            logger.info("✅ Cleanup completed!")
        except Exception as e:
            logger.warning(f"⚠️  Cleanup warning: {e}")
    
    def run_full_test(self):
        """Run the complete integration test suite"""
        logger.info(f"🚀 Starting {self.db_type} {self.db_version} Integration Test")
        
        try:
            # Start test infrastructure
            if not self.start_database_container():
                return False
            
            if not self.start_minio_container():
                return False
            
            # Create test data
            if not self.create_test_data():
                return False
            
            # Build and test our container
            if not self.build_container():
                return False
            
            # Run backup test (continue even if it fails to check MinIO)
            backup_success = self.run_backup_test()
            
            # Always verify backup exists in MinIO
            if not self.verify_backup_exists():
                logger.error("❌ Backup verification failed - file not found in MinIO")
                return False
            
            # Push to GCR
            if not self.push_to_gcr():
                return False
            
            # Create Cloud Run job
            if not self.build_jobs():
                return False
            
            # Print test data summary
            self.print_data()
            
            logger.info(f"🎉 {self.db_type} {self.db_version} integration test completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            logger.info("🔍 Keeping containers running for debugging...")
            return False
        finally:
            # Comment out cleanup for debugging
            # self.cleanup()
            pass
    
    # Abstract methods that must be implemented by each database type
    @abstractmethod
    def get_database_container_config(self) -> dict:
        """Return database-specific container configuration"""
        pass
    
    @abstractmethod
    def wait_for_database_ready(self) -> bool:
        """Wait for database to be ready and return True if successful"""
        pass
    
    @abstractmethod
    def create_test_data(self) -> bool:
        """Create test data in the database"""
        pass
    
    @abstractmethod
    def get_backup_environment_vars(self) -> dict:
        """Return database-specific environment variables for backup"""
        pass

    def run_restore_test(self, backup_filename: str) -> bool:
        """Test restore functionality - database independent"""
        logger.info(f"🧪 Testing {self.db_type} restore functionality...")
        
        try:
            test_tag = f'gcr.io/apito-cms/plan-b-backup-{self.db_type}:test-{self.db_version}'
            
            # Get host IP address for connections when using host network
            import socket
            host_ip = socket.gethostbyname(socket.gethostname())
            
            # Use host networking and MinIO's exposed port
            minio_endpoint = f'http://127.0.0.1:{self.minio_port}'
            logger.info(f"🔍 Using MinIO endpoint: {minio_endpoint}")
            logger.info(f"🔍 Using DB host: {host_ip}")
            logger.info(f"🔍 Using backup file: {backup_filename}")
            
            # Get database-specific environment variables
            env_vars = {
                'JOB_ID': f'test-restore-{self.db_type}-{self.db_version}-{int(time.time())}',
                'DB_ENGINE': self.db_type,
                'STORAGE_TYPE': 's3',
                'STORAGE_ENDPOINT': minio_endpoint,
                'STORAGE_BUCKET': self.minio_bucket,
                'STORAGE_ACCESS_KEY_ID': self.minio_access_key,
                'STORAGE_SECRET_ACCESS_KEY': self.minio_secret_key,
                'STORAGE_REGION': 'us-east-1',
                'BACKUP_PATH': backup_filename,
                'CALLBACK_URL': 'http://localhost:3000/test-callback',
                'CALLBACK_SECRET': 'test-secret',
                'OPERATION_TYPE': 'restore'  # Set operation type to restore
            }
            
            # Add database-specific environment variables
            env_vars.update(self.get_backup_environment_vars())
            
            # Run restore using our container with host networking
            restore_container = self.client.containers.run(
                test_tag,
                environment=env_vars,
                network='host',  # Use host network to access MinIO
                detach=True,  # Run in detached mode
                tty=False,
                stream=False
            )
            
            # Wait for the restore container to complete
            result = restore_container.wait()
            logs = restore_container.logs().decode('utf-8')
            
            # Remove the restore container
            restore_container.remove()
            
            logger.info(f"✅ Restore test completed: {logs}")
            return result['StatusCode'] == 0
            
        except Exception as e:
            logger.error(f"❌ Restore test failed: {e}")
            return False

    @abstractmethod
    def verify_restored_data(self) -> bool:
        """Verify that restored data matches original test data"""
        pass

    def run_backup_and_restore_test(self) -> bool:
        """Run complete backup and restore test flow"""
        logger.info("🔄 Running complete backup and restore test flow...")
        
        try:
            # Start test infrastructure
            if not self.start_database_container():
                logger.error("❌ Failed to start database container")
                return False
                
            if not self.wait_for_database_ready():
                logger.error("❌ Database failed to start")
                return False
                
            if not self.start_minio_container():
                logger.error("❌ Failed to start MinIO container")
                return False
                
            if not self.create_test_data():
                logger.error("❌ Failed to create test data")
                return False
                
            if not self.build_container():
                logger.error("❌ Failed to build container")
                return False
                
            logger.info("✅ Test environment setup completed!")
            
            # Use a consistent backup filename for restore test
            backup_filename = f'{self.db_type}-{self.db_version}-test-backup.tar.gz'
            logger.info(f"🔍 Backup filename for restore: {backup_filename}")
            
            # Run backup test with consistent filename
            logger.info("🔄 Running backup test with consistent filename...")
            backup_success = self.run_backup_test(custom_backup_filename=backup_filename)
            
            if not backup_success:
                logger.error("❌ Backup test failed, cannot proceed with restore test")
                return False
                
            logger.info("✅ Backup test completed successfully!")
            
            # Verify backup exists
            logger.info("🔍 Verifying backup exists...")
            if not self.verify_backup_exists():
                logger.error("❌ Backup verification failed")
                return False
                
            logger.info("✅ Backup verification completed!")
            
            # Push to GCR
            logger.info("☁️  Pushing container to Google Container Registry...")
            if not self.push_to_gcr():
                logger.error("❌ Failed to push to GCR")
                return False
                
            logger.info("✅ Container pushed to GCR successfully!")
            
            # Create Cloud Run job
            logger.info("🔨 Creating Cloud Run job...")
            if not self.build_jobs():
                logger.error("❌ Failed to create Cloud Run job")
                return False
                
            logger.info("✅ Cloud Run job created successfully!")
            
            # Print test data summary
            logger.info("📊 Printing test data summary...")
            self.print_data()
            
            # Now run restore test
            logger.info("🔄 Running restore test...")
            restore_success = self.run_restore_test(backup_filename)
            
            if restore_success:
                logger.info("✅ Restore test completed successfully!")
                
                # Verify restored data
                logger.info("🔍 Verifying restored data...")
                verification_success = self.verify_restored_data()
                
                if verification_success:
                    logger.info("🎉 Complete backup and restore test completed successfully!")
                    logger.info("✅ Backup, restore, and verification all passed!")
                    return True
                else:
                    logger.error("❌ Data verification failed")
                    return False
            else:
                logger.error("❌ Restore test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backup and restore test failed: {e}")
            return False
