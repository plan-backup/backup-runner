#!/usr/bin/env python3
"""
Plan B Database Runner - MongoDB 8.0
Backup, compression, and S3 upload functionality using official MongoDB tools
"""

import os
import sys
import subprocess
import tempfile
import logging
import gzip
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
import tarfile
import io
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class MongoDBRunner:
    def __init__(self):
        """Initialize MongoDB runner with environment variables"""
        logger.info("🔧 Initializing MongoDB runner...")

        # Database connection
        self.db_host = os.getenv('DB_HOST')
        self.db_port = os.getenv('DB_PORT', '27017')
        self.db_name = os.getenv('DB_NAME')
        self.db_username = os.getenv('DB_USERNAME')
        self.db_password = os.getenv('DB_PASSWORD')

        # Storage configuration
        self.storage_type = os.getenv('STORAGE_TYPE', 's3')
        self.storage_endpoint = os.getenv('STORAGE_ENDPOINT')
        self.storage_bucket = os.getenv('STORAGE_BUCKET')
        self.storage_region = os.getenv('STORAGE_REGION', 'us-east-1')
        self.storage_access_key_id = os.getenv('STORAGE_ACCESS_KEY_ID')
        self.storage_secret_access_key = os.getenv('STORAGE_SECRET_ACCESS_KEY')
        self.backup_path = os.getenv('BACKUP_PATH')

        # Job configuration
        self.job_id = os.getenv('JOB_ID')
        self.retention_days = os.getenv('RETENTION_DAYS', '30')
        self.callback_url = os.getenv('CALLBACK_URL')
        self.callback_secret = os.getenv('CALLBACK_SECRET')

        logger.info("🔧 Environment variables loaded")

        # Validate required environment variables
        self._validate_environment()

        # Initialize S3 client
        self._init_s3_client()

    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = [
            'DB_HOST', 'DB_NAME', 'STORAGE_ENDPOINT', 'STORAGE_BUCKET',
            'STORAGE_ACCESS_KEY_ID', 'STORAGE_SECRET_ACCESS_KEY', 'BACKUP_PATH'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _init_s3_client(self):
        """Initialize S3 client with credentials"""
        try:
            logger.info(f"🔧 Initializing S3 client with endpoint: {self.storage_endpoint}")
            logger.info(f"🔧 Storage type: {self.storage_type}")
            logger.info(f"🔧 Storage bucket: {self.storage_bucket}")
            logger.info(f"🔧 Storage region: {self.storage_region}")

            # Validate endpoint format
            if not self.storage_endpoint:
                raise ValueError("Storage endpoint is required")

            if not (self.storage_endpoint.startswith('http://') or self.storage_endpoint.startswith('https://')):
                raise ValueError(f"Invalid endpoint format: {self.storage_endpoint}")

            session = boto3.Session(
                aws_access_key_id=self.storage_access_key_id,
                aws_secret_access_key=self.storage_secret_access_key,
                region_name=self.storage_region
            )

            # For S3-compatible storage (like MinIO), use custom endpoint
            if self.storage_endpoint and not self.storage_endpoint.startswith('https://s3.'):
                # Determine SSL usage based on endpoint
                use_ssl = not ('localhost' in self.storage_endpoint or 'http://' in self.storage_endpoint)
                logger.info(f"🔧 Using custom endpoint with SSL: {use_ssl}")
                self.s3_client = session.client(
                    's3',
                    endpoint_url=self.storage_endpoint,
                    use_ssl=use_ssl
                )
            else:
                # Standard AWS S3
                logger.info("🔧 Using standard AWS S3")
                self.s3_client = session.client('s3')

            logger.info(f"✅ S3 client initialized for endpoint: {self.storage_endpoint}")

            # Test connectivity
            try:
                logger.info("🔧 Testing S3 connectivity...")
                self.s3_client.list_buckets()
                logger.info("✅ S3 connectivity test successful")
            except Exception as conn_error:
                logger.warning(f"⚠️  S3 connectivity test failed: {conn_error}")
                # Don't fail here, just warn - the endpoint might be valid but not accessible yet

        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 client: {e}")
            raise

    def create_backup(self):
        """Create MongoDB backup using mongodump"""
        logger.info(f"🍃 Creating MongoDB backup for database: {self.db_name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            # mongodump creates dump/database_name/ structure
            dump_dir = os.path.join(temp_dir, "dump")
            db_dump_dir = os.path.join(dump_dir, self.db_name)

            try:
                # Construct mongodump command
                mongodump_cmd = [
                    "mongodump",
                    "--host", f"{self.db_host}:{self.db_port}",
                    "--db", self.db_name,
                    "--out", temp_dir  # Output to temp_dir, mongodump will create dump/ subdirectory
                ]

                # Add authentication if provided
                if self.db_username:
                    mongodump_cmd.extend(["--username", self.db_username])
                if self.db_password:
                    mongodump_cmd.extend(["--password", self.db_password])

                logger.info(f"▶️  Running mongodump command: {' '.join(mongodump_cmd[:4])} [auth hidden]")
                
                # First, let's test if we can connect to MongoDB and check the database
                logger.info("🔍 Testing MongoDB connection and checking database...")
                test_cmd = [
                    "mongosh",
                    f"--host", f"{self.db_host}:{self.db_port}",
                    "--eval", f"db.adminCommand('ping'); show dbs; use {self.db_name}; show collections;"
                ]
                if self.db_username:
                    test_cmd.extend(["--username", self.db_username])
                if self.db_password:
                    test_cmd.extend(["--password", self.db_password])
                
                test_result = subprocess.run(test_cmd, capture_output=True, text=True)
                if test_result.returncode == 0:
                    logger.info("✅ MongoDB connection test successful")
                    logger.info(f"🔍 Database info: {test_result.stdout}")
                else:
                    logger.warning(f"⚠️  MongoDB connection test failed: {test_result.stderr}")
                
                # Also test mongodump with verbose output
                logger.info("🔍 Testing mongodump with verbose output...")
                verbose_cmd = mongodump_cmd + ["--verbose"]
                verbose_result = subprocess.run(verbose_cmd, capture_output=True, text=True)
                logger.info(f"🔍 mongodump verbose stderr: {verbose_result.stderr}")
                logger.info(f"🔍 mongodump verbose stdout: {verbose_result.stdout}")
                logger.info(f"🔍 mongodump verbose return code: {verbose_result.returncode}")
                
                # Now run mongodump normally
                result = subprocess.run(mongodump_cmd, capture_output=True, text=True)
                
                # Debug: always show stderr and stdout
                if result.stderr:
                    logger.info(f"🔍 mongodump stderr: {result.stderr}")
                if result.stdout:
                    logger.info(f"🔍 mongodump stdout: {result.stdout}")
                
                if result.returncode != 0:
                    raise Exception(f"mongodump failed: {result.stderr}")
                
                # Debug: check what was created
                logger.info(f"🔍 Checking temp directory contents: {os.listdir(temp_dir)}")
                if os.path.exists(dump_dir):
                    logger.info(f"🔍 Checking dump directory contents: {os.listdir(dump_dir)}")
                
                # Check if dump directory was created
                if not os.path.exists(dump_dir):
                    # If no collections exist, mongodump won't create any output
                    logger.warning(f"⚠️  Dump directory not found: {dump_dir}")
                    logger.warning("⚠️  This means the database has no collections to dump")
                    
                    # Create an empty dump directory structure for consistency
                    os.makedirs(db_dump_dir, exist_ok=True)
                    logger.info("✅ Created empty dump directory structure")
                
                logger.info("✅ MongoDB backup created successfully locally.")

                # Create tar.gz archive of the dump directory
                compressed_file_path = os.path.join(temp_dir, os.path.basename(self.backup_path))
                logger.info(f"🗜️  Compressing backup to {compressed_file_path}...")
                
                with tarfile.open(compressed_file_path, 'w:gz') as tar:
                    tar.add(dump_dir, arcname='dump')
                
                logger.info("✅ Backup compressed successfully.")

                # Upload to S3
                self._upload_to_s3(compressed_file_path)

                logger.info("🎉 MongoDB backup, compression, and upload complete!")
                return True

            except subprocess.CalledProcessError as e:
                logger.error(f"❌ mongodump failed: {e.stderr}")
                raise
            except ClientError as e:
                logger.error(f"❌ S3 client error during upload: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ An unexpected error occurred during backup: {e}")
                raise

    def _upload_to_s3(self, file_path):
        """Uploads a file to S3-compatible storage"""
        logger.info(f"☁️  Uploading {file_path} to s3://{self.storage_bucket}/{self.backup_path}...")
        try:
            self.s3_client.upload_file(file_path, self.storage_bucket, self.backup_path)
            logger.info("✅ File uploaded to S3 successfully.")
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found or configured.")
            raise
        except ClientError as e:
            logger.error(f"❌ S3 upload failed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred during S3 upload: {e}")
            raise

    def restore_backup(self):
        """Restore MongoDB backup using mongorestore"""
        logger.info(f"🔄 Restoring MongoDB backup for database: {self.db_name}")
        # This method would involve downloading from S3, decompressing, and then using mongorestore
        # Implementation details for restore are not yet requested, focusing on backup first.
        logger.warning("⚠️  Restore functionality is not yet implemented.")
        return False # Indicate not implemented

    def send_callback(self, status, message):
        """Send callback to the provided URL"""
        if not self.callback_url:
            logger.info("Skipping callback: No CALLBACK_URL provided.")
            return

        try:
            headers = {
                "Content-Type": "application/json",
                "X-Callback-Secret": self.callback_secret
            }
            payload = {
                "jobId": self.job_id,
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            response = requests.post(self.callback_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"✅ Callback sent successfully to {self.callback_url} with status {status}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to send callback to {self.callback_url}: {e}")
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred during callback: {e}")

if __name__ == '__main__':
    runner = MongoDBRunner()
    try:
        runner.create_backup()
        runner.send_callback("success", "MongoDB backup completed successfully.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        runner.send_callback("failure", f"MongoDB backup failed: {e}")
        sys.exit(1)