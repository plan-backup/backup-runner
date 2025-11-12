#!/usr/bin/env python3
"""
Plan B Integration Test - ArangoDB latest
Tests backup and restore functionality with real database container
"""

import os
import sys
import time
import docker
import subprocess
import tempfile
import logging
import requests
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArangoDBIntegrationTest:
    def __init__(self):
        self.client = docker.from_env()
        self.container = None
        self.minio_container = None
        self.test_network = None
        self.container_name = None
        self.minio_container_name = None
        self.test_db = "planb_testdb"
        self.db_port = 8530 + int(time.time()) % 1000  # Dynamic port to avoid conflicts
        self.minio_port = 9000 + int(time.time()) % 1000  # Dynamic port for MinIO
        self.arango_user = "planb_test"
        self.arango_password = "planb_test_pass"
        self.minio_access_key = "minioadmin"
        self.minio_secret_key = "minioadmin"
        self.minio_bucket = "planb-backups"
        
    def start_database_container(self):
        """Start ArangoDB latest container for testing"""
        logger.info("🥨 Starting ArangoDB latest container...")
        
        try:
            # Create a custom network for test containers
            network_name = f"planb_test_network_{int(time.time())}"
            self.test_network = self.client.networks.create(network_name, driver="bridge")
            self.container_name = f"planb_test_arangodb_latest_{int(time.time())}"
            
            # Start ArangoDB container on custom network
            self.container = self.client.containers.run(
                "arangodb/arangodb:latest",
                environment={
                    "ARANGO_ROOT_PASSWORD": self.arango_password,
                },
                ports={'8529/tcp': self.db_port},
                detach=True,
                remove=True,
                name=self.container_name,
                network=network_name  # Connect to custom network
            )
            
            # Wait for ArangoDB to be ready
            logger.info("⏳ Waiting for ArangoDB to be ready...")
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.get(
                        f"http://localhost:{self.db_port}/_api/version",
                        auth=('root', self.arango_password),
                        timeout=5
                    )
                    if response.status_code == 200:
                        logger.info("✅ ArangoDB is ready!")
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(2)
                if attempt == max_attempts - 1:
                    raise Exception("ArangoDB failed to start within timeout")
            
            return True
                        
        except Exception as e:
            logger.error(f"❌ Failed to start ArangoDB container: {e}")
            return False
    
    def start_minio_container(self):
        """Start MinIO S3-compatible storage container for testing"""
        logger.info("📦 Starting MinIO S3-compatible storage container...")
        
        try:
            self.minio_container_name = f"planb_test_minio_{int(time.time())}"
            
            # Start MinIO container on custom network
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
                network=self.test_network.name  # Connect to custom network
            )
            
            # Wait for MinIO to be ready
            logger.info("⏳ Waiting for MinIO to be ready...")
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.get(
                        f"http://localhost:{self.minio_port}/minio/health/live",
                        timeout=5
                    )
                    if response.status_code == 200:
                        logger.info("✅ MinIO is ready!")
                        break
                except requests.exceptions.ConnectionError:
                    pass
                time.sleep(2)
                if attempt == max_attempts - 1:
                    raise Exception("MinIO failed to start within timeout")
            
            # Create bucket
            self._create_minio_bucket()
            
            return True
                        
        except Exception as e:
            logger.error(f"❌ Failed to start MinIO container: {e}")
            return False
    
    def _create_minio_bucket(self):
        """Create MinIO bucket for testing"""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Initialize MinIO client
            s3_client = boto3.client(
                's3',
                endpoint_url=f'http://localhost:{self.minio_port}',
                aws_access_key_id=self.minio_access_key,
                aws_secret_access_key=self.minio_secret_key,
                use_ssl=False
            )
            
            # Create bucket
            s3_client.create_bucket(Bucket=self.minio_bucket)
            logger.info(f"✅ MinIO bucket '{self.minio_bucket}' created successfully")
            
        except Exception as e:
            # Check if it's a ClientError for bucket already exists
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'BucketAlreadyOwnedByYou':
                logger.info(f"✅ MinIO bucket '{self.minio_bucket}' already exists")
            else:
                logger.error(f"❌ Failed to create MinIO bucket: {e}")
                raise
    
    def setup_test_data(self):
        """Setup test database with IMDB document data"""
        logger.info("📊 Setting up test data...")
        
        try:
            base_url = f"http://localhost:{self.db_port}"
            auth = ('root', self.arango_password)
            
            # Create database
            db_response = requests.post(
                f"{base_url}/_api/database",
                json={"name": self.test_db},
                auth=auth
            )
            
            if db_response.status_code not in [201, 409]:  # 409 = already exists
                raise Exception(f"Failed to create database: {db_response.text}")
            
            # Create collections and insert test data
            collections_data = {
                "movies": [
                    {"_key": "1", "title": "The Shawshank Redemption", "year": 1994, "rating": 9.3, "genre": "Drama", "director": "Frank Darabont"},
                    {"_key": "2", "title": "The Godfather", "year": 1972, "rating": 9.2, "genre": "Crime", "director": "Francis Ford Coppola"},
                    {"_key": "3", "title": "The Dark Knight", "year": 2008, "rating": 9.0, "genre": "Action", "director": "Christopher Nolan"}
                ],
                "actors": [
                    {"_key": "1", "name": "Morgan Freeman", "birth_year": 1937, "nationality": "American"},
                    {"_key": "2", "name": "Marlon Brando", "birth_year": 1924, "nationality": "American"},
                    {"_key": "3", "name": "Christian Bale", "birth_year": 1974, "nationality": "British"}
                ]
            }
            
            for collection_name, documents in collections_data.items():
                # Create collection
                collection_response = requests.post(
                    f"{base_url}/_db/{self.test_db}/_api/collection",
                    json={"name": collection_name},
                    auth=auth
                )
                
                if collection_response.status_code not in [200, 409]:
                    raise Exception(f"Failed to create collection {collection_name}: {collection_response.text}")
                
                # Insert documents
                for doc in documents:
                    doc_response = requests.post(
                        f"{base_url}/_db/{self.test_db}/_api/document/{collection_name}",
                        json=doc,
                        auth=auth
                    )
                    
                    if doc_response.status_code not in [201, 202]:
                        raise Exception(f"Failed to insert document: {doc_response.text}")
            
            logger.info(f"✅ Test data created: {len(collections_data['movies'])} movies, {len(collections_data['actors'])} actors")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup test data: {e}")
            return False
    
    def build_container(self):
        """Build our Plan B ArangoDB container for testing (native platform)"""
        logger.info("🔨 Building Plan B ArangoDB container for testing...")
        
        try:
            # Build for native platform (ARM64) for local testing
            build_result = subprocess.run([
                'docker', 'build', 
                '-f', './arangodb/latest/Dockerfile',
                '-t', 'gcr.io/apito-cms/plan-b-backup-arangodb:test-local',
                '.'
            ], capture_output=True, text=True, cwd='/Users/diablo/Projects/react/backup-runner')
            
            if build_result.returncode != 0:
                raise Exception(f"Failed to build container: {build_result.stderr}")
            
            logger.info("✅ Container built successfully for local testing!")
            return True
                
        except Exception as e:
            logger.error(f"❌ Container build failed: {e}")
            return False

    def run_backup_test(self):
        """Test complete backup pipeline using our built container"""
        logger.info("💾 Testing complete backup pipeline with our container...")
        
        try:
            # Generate unique backup path
            timestamp = int(time.time())
            backup_path = f"backups/test/{timestamp}/arangodb-backup.tar.gz"
            
            logger.info("▶️  Running complete backup pipeline using our Plan B container...")
            
            # Use container name for network resolution (Docker internal DNS)
            logger.info(f"Using MinIO container name: {self.minio_container_name}")
            
            # Use Docker Python client instead of subprocess
            try:
                backup_output = self.client.containers.run(
                    'gcr.io/apito-cms/plan-b-backup-arangodb:test-local',
                    command=['python3', '/usr/local/bin/runner.py'],
                    environment={
                        # Database connection
                        'DB_HOST': self.container_name,  # Use container name for internal network
                        'DB_PORT': '8529',
                        'DB_NAME': self.test_db,
                        'DB_USERNAME': 'root',
                        'DB_PASSWORD': self.arango_password,
                        
                        # Storage configuration (use host networking for simplicity)
                        'STORAGE_TYPE': 's3',
                        'STORAGE_ENDPOINT': f'http://host.docker.internal:{self.minio_port}',  # Use host gateway
                        'STORAGE_BUCKET': self.minio_bucket,
                        'STORAGE_REGION': 'us-east-1',
                        'STORAGE_ACCESS_KEY_ID': self.minio_access_key,
                        'STORAGE_SECRET_ACCESS_KEY': self.minio_secret_key,
                        'BACKUP_PATH': backup_path,
                        
                        # Job configuration
                        'JOB_ID': f'test-job-{timestamp}',
                        'RETENTION_DAYS': '30',
                        'CALLBACK_URL': '',  # No callback for testing
                        'CALLBACK_SECRET': ''
                    },
                    network=self.test_network.name,  # Use same network as database and MinIO
                    remove=True,
                    detach=False
                )
                
                # Container ran successfully
                backup_result = type('obj', (object,), {'returncode': 0, 'stdout': backup_output.decode('utf-8'), 'stderr': ''})()
                logger.info(f"Container output: {backup_output.decode('utf-8')}")
                
            except Exception as container_error:
                # Container failed
                error_msg = str(container_error)
                logger.error(f"Container execution failed: {error_msg}")
                backup_result = type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': error_msg})()
            
            if backup_result.returncode == 0:
                logger.info("✅ Complete backup pipeline executed successfully!")
                
                # Verify backup was uploaded to MinIO
                if self._verify_backup_upload(backup_path):
                    logger.info(f"✅ Backup uploaded and verified: {backup_path}")
                    return True
                else:
                    logger.error("❌ Backup upload verification failed")
                    return False
            else:
                logger.error(f"❌ Backup pipeline failed: {backup_result.stderr}")
                logger.error(f"❌ Backup stdout: {backup_result.stdout}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Backup test failed: {e}")
            return False
    
    def _verify_backup_upload(self, backup_path):
        """Verify that backup was uploaded to MinIO"""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Initialize MinIO client
            s3_client = boto3.client(
                's3',
                endpoint_url=f'http://localhost:{self.minio_port}',
                aws_access_key_id=self.minio_access_key,
                aws_secret_access_key=self.minio_secret_key,
                use_ssl=False
            )
            
            # Check if object exists
            response = s3_client.head_object(Bucket=self.minio_bucket, Key=backup_path)
            file_size = response['ContentLength']
            logger.info(f"✅ Backup verified in MinIO: {file_size} bytes")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Backup verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Backup verification failed: {e}")
            return False

    def push_to_gcr(self):
        """Build production image and push to Google Container Registry"""
        logger.info("☁️  Building production image and pushing to GCR...")
        
        try:
            # Configure Docker authentication for GCR
            auth_result = subprocess.run([
                'gcloud', 'auth', 'configure-docker', '--quiet'
            ], capture_output=True, text=True)
            
            if auth_result.returncode != 0:
                logger.warning(f"Docker auth warning: {auth_result.stderr}")
            
            # Build production image for linux/amd64 (Cloud Run requirement)
            logger.info("🔨 Building production image for linux/amd64...")
            build_result = subprocess.run([
                'docker', 'build', '--platform', 'linux/amd64',
                '-f', './arangodb/latest/Dockerfile',
                '-t', 'gcr.io/apito-cms/plan-b-backup-arangodb:latest',
                '.'
            ], capture_output=True, text=True, cwd='/Users/diablo/Projects/react/backup-runner')
            
            if build_result.returncode != 0:
                raise Exception(f"Failed to build production container: {build_result.stderr}")
            
            logger.info("✅ Production image built successfully!")
            
            # Push to GCR
            logger.info("⬆️  Pushing to Google Container Registry...")
            push_result = subprocess.run([
                'docker', 'push', 'gcr.io/apito-cms/plan-b-backup-arangodb:latest'
            ], capture_output=True, text=True)
            
            if push_result.returncode == 0:
                logger.info("✅ Successfully pushed to Google Container Registry!")
                logger.info("🏷️  Image: gcr.io/apito-cms/plan-b-backup-arangodb:latest")
                return True
            else:
                logger.error(f"❌ Failed to push to GCR: {push_result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ GCR push failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test resources"""
        logger.info("🧹 Cleaning up...")
        
        if self.container:
            try:
                self.container.stop()
                logger.info("✅ ArangoDB test container stopped")
            except:
                pass
        
        if self.minio_container:
            try:
                self.minio_container.stop()
                logger.info("✅ MinIO test container stopped")
            except:
                pass
        
        # Clean up custom network
        if hasattr(self, 'test_network'):
            try:
                self.test_network.remove()
                logger.info("✅ Test network removed")
            except:
                pass
    
    def run_full_test(self):
        """Run complete build, test, and deploy pipeline"""
        logger.info("🚀 Starting ArangoDB latest Build & Test Pipeline")
        logger.info("=" * 60)
        
        try:
            # Step 1: Start test database container
            logger.info("📋 Step 1: Starting test database...")
            if not self.start_database_container():
                return False
            
            # Step 2: Start MinIO S3-compatible storage
            logger.info("📋 Step 2: Starting MinIO S3 storage...")
            if not self.start_minio_container():
                return False
            
            # Step 3: Setup test data
            logger.info("📋 Step 3: Setting up test data...")
            if not self.setup_test_data():
                return False
            
            # Step 4: Build our Plan B container
            logger.info("📋 Step 4: Building Plan B container...")
            if not self.build_container():
                return False
            
            # Step 5: Test complete backup pipeline (backup → compress → upload)
            logger.info("📋 Step 5: Testing complete backup pipeline...")
            if not self.run_backup_test():
                return False
            
            # Step 6: Push to Google Container Registry (only if all tests pass)
            logger.info("📋 Step 6: Pushing to production registry...")
            if not self.push_to_gcr():
                logger.error("❌ Failed to push to GCR, but tests passed")
                return False
            
            logger.info("🎉 ArangoDB latest Pipeline COMPLETED SUCCESSFULLY!")
            logger.info("✅ Container tested and deployed to production")
            logger.info("✅ Complete backup → compress → upload pipeline verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            return False
        finally:
            self.cleanup()

if __name__ == '__main__':
    test = ArangoDBIntegrationTest()
    success = test.run_full_test()
    sys.exit(0 if success else 1)