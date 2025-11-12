#!/usr/bin/env python3
"""
Plan B Database Runner - MySQL 9.4
Backup, compression, and S3 upload functionality using official MySQL tools
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

class MySQLRunner:
    def __init__(self):
        """Initialize MySQL runner with environment variables"""
        logger.info("🔧 Initializing MySQL runner...")

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

            # For test environments, use a simple HTTP client approach
            if "planb_test_minio" in self.storage_endpoint:
                logger.info("🔧 Using HTTP client for test environment")
                self.s3_client = "http_client"  # Flag to use HTTP client
            else:
                # Configure boto3 for S3-compatible storage
                import botocore.config
                config = botocore.config.Config(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'path'
                    },
                    retries={'max_attempts': 3}
                )

                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=self.storage_endpoint,
                    aws_access_key_id=self.storage_access_key_id,
                    aws_secret_access_key=self.storage_secret_access_key,
                    region_name=self.storage_region,
                    config=config,
                    use_ssl=False
                )
                
                # Create bucket if it doesn't exist (for test environments)
                try:
                    self.s3_client.head_bucket(Bucket=self.storage_bucket)
                    logger.info(f"✅ Bucket {self.storage_bucket} already exists")
                except Exception as e:
                    logger.info(f"🔧 Creating bucket {self.storage_bucket}...")
                    try:
                        self.s3_client.create_bucket(Bucket=self.storage_bucket)
                        logger.info(f"✅ Bucket {self.storage_bucket} created successfully")
                    except Exception as create_error:
                        logger.warning(f"⚠️  Bucket creation failed: {create_error}")
                
                logger.info("✅ S3-compatible client initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 client: {e}")
            self.s3_client = None

    def create_backup(self):
        """Create MySQL backup using mysqldump"""
        logger.info(f"🐬 Creating MySQL backup for database: {self.db_name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_file_name = f"{self.db_name}_backup.sql"
            backup_file_path = os.path.join(temp_dir, backup_file_name)

            try:
                # Construct mysqldump command
                mysqldump_cmd = [
                    "mysqldump",
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

                logger.info(f"▶️  Running mysqldump command: {' '.join(mysqldump_cmd[:-1])} {self.db_name}")
                with open(backup_file_path, 'w') as f:
                    result = subprocess.run(mysqldump_cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"mysqldump failed: {result.stderr}")
                
                logger.info("✅ MySQL backup created successfully locally.")

                # Compress the backup file
                compressed_file_path = os.path.join(temp_dir, os.path.basename(self.backup_path))
                logger.info(f"🗜️  Compressing backup to {compressed_file_path}...")
                with open(backup_file_path, 'rb') as f_in:
                    with gzip.open(compressed_file_path, 'wb') as f_out:
                        f_out.writelines(f_in)
                logger.info("✅ Backup compressed successfully.")

                # Upload to S3
                self._upload_to_s3(compressed_file_path)

                logger.info("🎉 MySQL backup, compression, and upload complete!")
                return True

            except subprocess.CalledProcessError as e:
                logger.error(f"❌ mysqldump failed: {e.stderr}")
                raise
            except ClientError as e:
                logger.error(f"❌ S3 client error during upload: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ An unexpected error occurred during backup: {e}")
                raise

    def _upload_to_s3(self, file_path):
        """Uploads a file to S3-compatible storage"""
        if not self.s3_client:
            logger.error("❌ S3 client not configured, cannot upload backup")
            raise Exception("S3 client not configured")
            
        logger.info(f"☁️  Uploading {file_path} to s3://{self.storage_bucket}/{self.backup_path}...")
        
        # Try multiple upload methods for reliability
        upload_methods = [
            self._upload_with_boto3,
            self._upload_with_requests
        ]
        
        # For test environments, prioritize HTTP client
        if self.s3_client == "http_client":
            upload_methods = [self._upload_with_requests, self._upload_with_boto3]
        
        last_error = None
        for method in upload_methods:
            try:
                logger.info(f"🔧 Attempting upload with {method.__name__}")
                method(file_path)
                logger.info("✅ File uploaded to S3 successfully.")
                return
            except Exception as e:
                logger.warning(f"⚠️  Upload method {method.__name__} failed: {e}")
                last_error = e
                continue
        
        # If all methods failed
        logger.error(f"❌ All upload methods failed. Last error: {last_error}")
        raise Exception(f"S3 upload failed with all methods: {last_error}")

    def _upload_with_boto3(self, file_path):
        """Upload using boto3 client"""
        if self.s3_client == "http_client":
            logger.info("🔧 Skipping boto3 upload for test environment")
            raise Exception("Using HTTP client for test environment")
        self.s3_client.upload_file(file_path, self.storage_bucket, self.backup_path)

    def _upload_with_requests(self, file_path):
        """Upload using requests library with AWS S3 signature"""
        import requests
        import hashlib
        import hmac
        import datetime
        from urllib.parse import urlparse, quote
        
        # Parse endpoint
        parsed_endpoint = urlparse(self.storage_endpoint)
        upload_url = f"{self.storage_endpoint}/{self.storage_bucket}/{self.backup_path}"
        
        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Create AWS4 signature
        def create_aws4_signature(method, url, headers, payload, access_key, secret_key, region='us-east-1'):
            parsed_url = urlparse(url)
            
            # Create canonical request
            canonical_uri = parsed_url.path
            canonical_query_string = parsed_url.query
            canonical_headers = '\n'.join([f"{k.lower()}:{v}" for k, v in sorted(headers.items())])
            signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
            payload_hash = hashlib.sha256(payload).hexdigest()
            
            canonical_request = f"{method}\n{canonical_uri}\n{canonical_query_string}\n{canonical_headers}\n\n{signed_headers}\n{payload_hash}"
            
            # Create string to sign
            algorithm = 'AWS4-HMAC-SHA256'
            amz_date = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            date_stamp = amz_date[:8]
            credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
            string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
            
            # Calculate signature
            def sign(key, msg):
                return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
            
            k_date = sign(f"AWS4{secret_key}".encode(), date_stamp)
            k_region = sign(k_date, region)
            k_service = sign(k_region, 's3')
            k_signing = sign(k_service, 'aws4_request')
            signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
            
            # Create authorization header
            authorization_header = f"{algorithm} Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
            
            return authorization_header, amz_date
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Length': str(len(file_data)),
            'Host': parsed_endpoint.netloc
        }
        
        # Create AWS4 signature
        auth_header, amz_date = create_aws4_signature(
            'PUT', upload_url, headers, file_data,
            self.storage_access_key_id, self.storage_secret_access_key
        )
        
        headers['Authorization'] = auth_header
        headers['X-Amz-Date'] = amz_date
        
        # Upload using PUT request
        response = requests.put(
            upload_url,
            data=file_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Upload failed with status {response.status_code}: {response.text}")

    def restore_backup(self):
        """Restore MySQL backup using mysql client"""
        logger.info(f"🔄 Restoring MySQL backup for database: {self.db_name}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Download backup from S3
                logger.info(f"📥 Downloading backup from s3://{self.storage_bucket}/{self.backup_path}")
                backup_file_path = os.path.join(temp_dir, os.path.basename(self.backup_path))
                self._download_from_s3(backup_file_path)
                
                # Extract the backup file
                logger.info(f"📦 Extracting backup file: {backup_file_path}")
                extracted_file_path = os.path.join(temp_dir, f"{self.db_name}_restore.sql")
                self._extract_backup(backup_file_path, extracted_file_path)
                
                # Restore to database
                logger.info(f"🔄 Restoring backup to database: {self.db_name}")
                self._restore_to_database(extracted_file_path)
                
                logger.info("🎉 MySQL backup restore completed successfully!")
                return True
                
            except Exception as e:
                logger.error(f"❌ Restore failed: {e}")
                raise

    def _download_from_s3(self, file_path):
        """Download backup file from S3-compatible storage"""
        if not self.s3_client:
            logger.error("❌ S3 client not configured, cannot download backup")
            raise Exception("S3 client not configured")
            
        logger.info(f"📥 Downloading s3://{self.storage_bucket}/{self.backup_path} to {file_path}")
        
        try:
            if self.s3_client == "http_client":
                # Use requests for test environments
                self._download_with_requests(file_path)
            else:
                # Use boto3 for production environments
                self.s3_client.download_file(self.storage_bucket, self.backup_path, file_path)
            
            logger.info("✅ Backup file downloaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to download backup: {e}")
            raise

    def _download_with_requests(self, file_path):
        """Download using requests library with AWS S3 signature"""
        import requests
        import hashlib
        import hmac
        import datetime
        from urllib.parse import urlparse
        
        # Parse endpoint
        parsed_endpoint = urlparse(self.storage_endpoint)
        download_url = f"{self.storage_endpoint}/{self.storage_bucket}/{self.backup_path}"
        
        # Create AWS4 signature for GET request
        def create_aws4_signature(method, url, headers, payload, access_key, secret_key, region='us-east-1'):
            parsed_url = urlparse(url)
            
            # Create canonical request
            canonical_uri = parsed_url.path
            canonical_query_string = parsed_url.query
            canonical_headers = '\n'.join([f"{k.lower()}:{v}" for k, v in sorted(headers.items())])
            signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
            payload_hash = hashlib.sha256(payload).hexdigest()
            
            canonical_request = f"{method}\n{canonical_uri}\n{canonical_query_string}\n{canonical_headers}\n\n{signed_headers}\n{payload_hash}"
            
            # Create string to sign
            algorithm = 'AWS4-HMAC-SHA256'
            amz_date = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            date_stamp = amz_date[:8]
            credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
            string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
            
            # Calculate signature
            def sign(key, msg):
                return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
            
            k_date = sign(f"AWS4{secret_key}".encode(), date_stamp)
            k_region = sign(k_date, region)
            k_service = sign(k_region, 's3')
            k_signing = sign(k_service, 'aws4_request')
            signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
            
            # Create authorization header
            authorization_header = f"{algorithm} Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
            
            return authorization_header, amz_date
        
        # Prepare headers
        headers = {
            'Host': parsed_endpoint.netloc
        }
        
        # Create AWS4 signature
        auth_header, amz_date = create_aws4_signature(
            'GET', download_url, headers, b'',
            self.storage_access_key_id, self.storage_secret_access_key
        )
        
        headers['Authorization'] = auth_header
        headers['X-Amz-Date'] = amz_date
        
        # Download using GET request
        response = requests.get(download_url, headers=headers, timeout=30)
        
        if response.status_code not in [200]:
            raise Exception(f"Download failed with status {response.status_code}: {response.text}")
        
        # Save the downloaded file
        with open(file_path, 'wb') as f:
            f.write(response.content)

    def _extract_backup(self, compressed_file_path, extracted_file_path):
        """Extract compressed backup file"""
        logger.info(f"📦 Extracting {compressed_file_path} to {extracted_file_path}")
        
        try:
            with open(compressed_file_path, 'rb') as f_in:
                with gzip.open(f_in, 'rb') as gz_file:
                    with open(extracted_file_path, 'wb') as f_out:
                        f_out.write(gz_file.read())
            
            logger.info("✅ Backup file extracted successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to extract backup: {e}")
            raise

    def _restore_to_database(self, sql_file_path):
        """Restore SQL file to MySQL database"""
        logger.info(f"🔄 Restoring SQL file to database: {self.db_name}")
        
        try:
            # Create database if it doesn't exist
            create_db_cmd = [
                "mysql",
                f"--host={self.db_host}",
                f"--port={self.db_port}",
                f"--user={self.db_username}",
                f"--password={self.db_password}",
                "-e", f"CREATE DATABASE IF NOT EXISTS {self.db_name};"
            ]
            
            logger.info(f"▶️  Creating database: {' '.join(create_db_cmd[:-1])} {self.db_name}")
            result = subprocess.run(create_db_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Failed to create database: {result.stderr}")
            
            # Restore the SQL file
            restore_cmd = [
                "mysql",
                f"--host={self.db_host}",
                f"--port={self.db_port}",
                f"--user={self.db_username}",
                f"--password={self.db_password}",
                self.db_name
            ]
            
            logger.info(f"▶️  Restoring SQL file: {' '.join(restore_cmd[:-1])} {self.db_name}")
            with open(sql_file_path, 'r') as f:
                result = subprocess.run(restore_cmd, stdin=f, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Failed to restore database: {result.stderr}")
            
            logger.info("✅ Database restored successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to restore database: {e}")
            raise

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
    runner = MySQLRunner()
    operation_type = os.getenv('OPERATION_TYPE', 'backup').lower()
    
    try:
        if operation_type == 'backup':
            logger.info("🔄 Starting backup operation...")
            runner.create_backup()
            runner.send_callback("success", "MySQL backup completed successfully.")
        elif operation_type == 'restore':
            logger.info("🔄 Starting restore operation...")
            runner.restore_backup()
            runner.send_callback("success", "MySQL restore completed successfully.")
        else:
            logger.error(f"❌ Invalid OPERATION_TYPE: {operation_type}. Must be 'backup' or 'restore'")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        operation_name = "backup" if operation_type == "backup" else "restore"
        runner.send_callback("failure", f"MySQL {operation_name} failed: {e}")
        sys.exit(1)