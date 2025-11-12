#!/usr/bin/env python3
"""
Plan B Database Runner - MariaDB 12.2.0 (Latest)
Backup, compression, and S3 upload functionality using official MariaDB tools
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

class MariaDBRunner:
    def __init__(self):
        """Initialize MariaDB runner with environment variables"""
        logger.info("🔧 Initializing MariaDB runner...")

        # Database connection
        self.db_host = os.getenv('DB_HOST')
        self.db_port = os.getenv('DB_PORT', '3306')
        self.db_name = os.getenv('DB_NAME')
        self.db_username = os.getenv('DB_USERNAME', 'root')
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
        """Create MariaDB backup using mariadb-dump"""
        logger.info(f"🐬 Creating MariaDB backup for database: {self.db_name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_file_name = f"{self.db_name}_backup.sql"
            backup_file_path = os.path.join(temp_dir, backup_file_name)

            try:
                # Construct mariadb-dump command
                mariadb_dump_cmd = [
                    "mariadb-dump",
                    f"--host={self.db_host}",
                    f"--port={self.db_port}",
                    f"--user={self.db_username}",
                    f"--password={self.db_password}",
                    "--single-transaction",
                    "--routines",
                    "--triggers",
                    "--events",
                    "--set-gtid-purged=OFF",
                    "--default-character-set=utf8mb4",
                    self.db_name
                ]

                logger.info(f"▶️  Running mariadb-dump command: {' '.join(mariadb_dump_cmd[:-1])} {self.db_name}")
                with open(backup_file_path, 'w') as f:
                    result = subprocess.run(mariadb_dump_cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"mariadb-dump failed: {result.stderr}")
                
                logger.info("✅ MariaDB backup created successfully locally.")

                # Compress the backup file
                compressed_file_path = os.path.join(temp_dir, os.path.basename(self.backup_path))
                logger.info(f"🗜️  Compressing backup to {compressed_file_path}...")
                with open(backup_file_path, 'rb') as f_in:
                    with gzip.open(compressed_file_path, 'wb') as f_out:
                        f_out.writelines(f_in)
                logger.info("✅ Backup compressed successfully.")

                # Upload to S3
                self._upload_to_s3(compressed_file_path)

                logger.info("🎉 MariaDB backup, compression, and upload complete!")
                return True

            except subprocess.CalledProcessError as e:
                logger.error(f"❌ mariadb-dump failed: {e.stderr}")
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
        """Restore MariaDB backup using mariadb client"""
        logger.info(f"🔄 Restoring MariaDB backup for database: {self.db_name}")
        # This method would involve downloading from S3, decompressing, and then using mariadb client
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
    runner = MariaDBRunner()
    try:
        runner.create_backup()
        runner.send_callback("success", "MariaDB backup completed successfully.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        runner.send_callback("failure", f"MariaDB backup failed: {e}")
        sys.exit(1)
