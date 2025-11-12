#!/usr/bin/env python3
"""
Plan B Database Runner - ArangoDB latest
Backup, compression, and S3 upload functionality using official ArangoDB tools
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

logger = logging.getLogger(__name__)

class ArangoDBRunner:
    def __init__(self):
        """Initialize ArangoDB runner with environment variables"""
        logger.info("🔧 Initializing ArangoDB runner...")
        
        # Database connection
        self.db_host = os.getenv('DB_HOST')
        self.db_port = os.getenv('DB_PORT', '8529')
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
        """Create ArangoDB backup using arangodump"""
        logger.info(f"🥨 Creating ArangoDB backup for database: {self.db_name}")
        
        # Create temporary directory for backup
        backup_dir = tempfile.mkdtemp(suffix='_arangodb_backup')
        
        try:
            # Build arangodump command
            cmd = [
                'arangodump',
                '--server.endpoint', f"tcp://{self.db_host}:{self.db_port}",
                '--server.database', self.db_name,
                '--output-directory', backup_dir,
                '--compress-output', 'true',
                '--dump-data', 'true',
                '--include-system-collections', 'false'
            ]
            
            # Add authentication if provided
            if self.db_username:
                cmd.extend(['--server.username', self.db_username])
            if self.db_password:
                cmd.extend(['--server.password', self.db_password])
            
            logger.info(f"Running arangodump command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"arangodump failed: {result.stderr}")
            
            logger.info("✅ ArangoDB backup created successfully")
            return backup_dir
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            # Clean up on failure
            subprocess.run(['rm', '-rf', backup_dir], check=False)
            raise
    
    def compress_backup(self, backup_dir):
        """Compress backup directory to gzip archive"""
        logger.info(f"🗜️  Compressing backup directory: {backup_dir}")
        
        try:
            # Create temporary compressed file
            compressed_file = tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False)
            compressed_file.close()
            
            # Create gzip archive
            with open(compressed_file.name, 'wb') as f_out:
                with gzip.GzipFile(fileobj=f_out, mode='wb') as gz_out:
                    # Create tar archive in memory and compress
                    tar_buffer = io.BytesIO()
                    with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                        tar.add(backup_dir, arcname=os.path.basename(backup_dir))
                    
                    tar_buffer.seek(0)
                    gz_out.write(tar_buffer.read())
            
            # Get file size
            file_size = os.path.getsize(compressed_file.name)
            logger.info(f"✅ Backup compressed successfully: {compressed_file.name} ({file_size} bytes)")
            
            return compressed_file.name
            
        except Exception as e:
            logger.error(f"❌ Failed to compress backup: {e}")
            raise
    
    def upload_to_s3(self, local_file_path):
        """Upload file to S3-compatible storage"""
        logger.info(f"⬆️  Uploading to S3: {self.backup_path}")
        
        try:
            # Upload file
            self.s3_client.upload_file(
                local_file_path,
                self.storage_bucket,
                self.backup_path,
                ExtraArgs={
                    'ContentType': 'application/gzip',
                    'ContentEncoding': 'gzip'
                }
            )
            
            # Verify upload by checking if object exists
            try:
                response = self.s3_client.head_object(Bucket=self.storage_bucket, Key=self.backup_path)
                file_size = response['ContentLength']
                logger.info(f"✅ Upload successful: s3://{self.storage_bucket}/{self.backup_path} ({file_size} bytes)")
                return True
                
            except ClientError as e:
                logger.error(f"❌ Upload verification failed: {e}")
                return False
                
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found")
            return False
        except ClientError as e:
            logger.error(f"❌ S3 upload failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            return False
    
    def verify_upload(self):
        """Verify that the uploaded file exists and is accessible"""
        logger.info(f"🔍 Verifying upload: {self.backup_path}")
        
        try:
            response = self.s3_client.head_object(Bucket=self.storage_bucket, Key=self.backup_path)
            file_size = response['ContentLength']
            last_modified = response['LastModified']
            
            logger.info(f"✅ Upload verified: {file_size} bytes, modified: {last_modified}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Upload verification failed: {e}")
            return False
    
    def send_callback(self, success=True, message=""):
        """Send callback notification to webhook"""
        if not self.callback_url:
            logger.info("No callback URL provided, skipping notification")
            return
        
        try:
            import requests
            
            payload = {
                'job_id': self.job_id,
                'status': 'completed' if success else 'failed',
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            headers = {}
            if self.callback_secret:
                headers['Authorization'] = f'Bearer {self.callback_secret}'
            
            response = requests.post(
                self.callback_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("✅ Callback notification sent successfully")
            else:
                logger.warning(f"⚠️  Callback notification failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️  Failed to send callback notification: {e}")
    
    def run_backup(self):
        """Complete backup pipeline: backup → compress → upload → verify"""
        logger.info("🚀 Starting ArangoDB backup pipeline...")
        
        backup_dir = None
        compressed_file = None
        
        try:
            # Step 1: Create backup
            logger.info("📋 Step 1: Creating database backup...")
            backup_dir = self.create_backup()
            
            # Step 2: Compress backup
            logger.info("📋 Step 2: Compressing backup...")
            compressed_file = self.compress_backup(backup_dir)
            
            # Step 3: Upload to S3
            logger.info("📋 Step 3: Uploading to S3...")
            if not self.upload_to_s3(compressed_file):
                raise Exception("S3 upload failed")
            
            # Step 4: Verify upload
            logger.info("📋 Step 4: Verifying upload...")
            if not self.verify_upload():
                raise Exception("Upload verification failed")
            
            # Step 5: Send success callback
            logger.info("📋 Step 5: Sending success notification...")
            self.send_callback(success=True, message="Backup completed successfully")
            
            logger.info("🎉 ArangoDB backup pipeline completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup pipeline failed: {e}")
            self.send_callback(success=False, message=str(e))
            return False
            
        finally:
            # Cleanup temporary files
            if backup_dir and os.path.exists(backup_dir):
                subprocess.run(['rm', '-rf', backup_dir], check=False)
            if compressed_file and os.path.exists(compressed_file):
                os.unlink(compressed_file)
    
    def restore_backup(self, backup_path=None):
        """Restore ArangoDB backup using arangorestore"""
        if not backup_path:
            backup_path = self.backup_path
        
        logger.info(f"🔄 Restoring ArangoDB backup from: {backup_path}")
        
        # Download backup from S3
        temp_file = tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False)
        temp_file.close()
        
        try:
            # Download from S3
            self.s3_client.download_file(self.storage_bucket, backup_path, temp_file.name)
            logger.info("✅ Backup downloaded from S3")
            
            # Extract backup archive to temporary directory
            restore_dir = tempfile.mkdtemp(suffix='_arangodb_restore')
            subprocess.run(['tar', '-xzf', temp_file.name, '-C', restore_dir], check=True)
            
            # Find the extracted backup directory
            extracted_dirs = os.listdir(restore_dir)
            if not extracted_dirs:
                raise Exception("No backup data found in archive")
            
            backup_data_path = os.path.join(restore_dir, extracted_dirs[0])
            
            # Build arangorestore command
            cmd = [
                'arangorestore',
                '--server.endpoint', f"tcp://{self.db_host}:{self.db_port}",
                '--server.database', self.db_name,
                '--input-directory', backup_data_path,
                '--create-database', 'true',
                '--include-system-collections', 'false'
            ]
            
            # Add authentication if provided
            if self.db_username:
                cmd.extend(['--server.username', self.db_username])
            if self.db_password:
                cmd.extend(['--server.password', self.db_password])
            
            logger.info(f"Running arangorestore command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"arangorestore failed: {result.stderr}")
            
            logger.info("✅ ArangoDB restore completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Restore failed: {e}")
            raise
            
        finally:
            # Clean up temporary files
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            if 'restore_dir' in locals() and os.path.exists(restore_dir):
                subprocess.run(['rm', '-rf', restore_dir], check=False)

if __name__ == '__main__':
    import sys
    
    try:
        runner = ArangoDBRunner()
        
        if len(sys.argv) > 1 and sys.argv[1] == 'restore':
            if len(sys.argv) < 3:
                print("Usage: python runner.py restore [backup_path]")
                sys.exit(1)
            backup_path = sys.argv[2] if len(sys.argv) > 2 else None
            success = runner.restore_backup(backup_path)
        else:
            success = runner.run_backup()
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)