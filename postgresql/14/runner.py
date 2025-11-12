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
from backup_base import BackupRunnerBase as BackupBase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostgreSQLRunner(BackupBase):
    """PostgreSQL 14 backup and restore runner"""
    
    def __init__(self):
        super().__init__()
        # PostgreSQL-specific initialization
        self.db_name = os.getenv('DB_NAME')
        self.db_host = os.getenv('DB_HOST')
        self.db_port = os.getenv('DB_PORT', '5432')
        self.db_username = os.getenv('DB_USERNAME', 'postgres')
        self.db_password = os.getenv('DB_PASSWORD')
        self.storage_endpoint = os.getenv('STORAGE_ENDPOINT')
        self.storage_bucket = os.getenv('STORAGE_BUCKET')
        self.storage_access_key_id = os.getenv('STORAGE_ACCESS_KEY_ID')
        self.storage_secret_access_key = os.getenv('STORAGE_SECRET_ACCESS_KEY')
        self.storage_region = os.getenv('STORAGE_REGION', 'us-east-1')
        self.backup_path = os.getenv('BACKUP_PATH')
        
        # Debug logging
        logger.info(f"🔍 Storage bucket: {self.storage_bucket}")
        logger.info(f"🔍 Storage endpoint: {self.storage_endpoint}")
        logger.info(f"🔍 Storage access key: {self.storage_access_key_id[:10]}..." if self.storage_access_key_id else "None")
        
    def create_backup(self):
        """Create PostgreSQL backup using pg_dump"""
        logger.info(f"🔄 Creating PostgreSQL backup for database: {self.db_name}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. Create backup using pg_dump
                backup_file = os.path.join(temp_dir, f'{self.db_name}_backup.sql')
                logger.info(f"📦 Creating backup file: {backup_file}")
                
                # Set PGPASSWORD environment variable for pg_dump
                env = os.environ.copy()
                if self.db_password:
                    env['PGPASSWORD'] = self.db_password
                
                dump_cmd = [
                    'pg_dump',
                    '-h', self.db_host,
                    '-p', str(self.db_port),
                    '-U', self.db_username,
                    '-d', self.db_name,
                    '--verbose',
                    '--no-password',
                    '-f', backup_file
                ]
                
                logger.info(f"🔧 Running pg_dump command: {' '.join(dump_cmd)}")
                dump_result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
                
                if dump_result.returncode != 0:
                    logger.error(f"❌ pg_dump failed: {dump_result.stderr}")
                    raise Exception(f"pg_dump failed: {dump_result.stderr}")
                
                logger.info("✅ PostgreSQL backup created successfully")
                
                # 2. Compress the backup
                compressed_file = f"{backup_file}.tar.gz"
                logger.info(f"🗜️  Compressing backup to: {compressed_file}")
                
                import tarfile
                with tarfile.open(compressed_file, 'w:gz') as tar:
                    tar.add(backup_file, arcname=os.path.basename(backup_file))
                
                logger.info("✅ Backup compressed successfully")
                
                # 3. Upload to S3/MinIO
                backup_filename = self.backup_path if self.backup_path else f'{self.db_name}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql.gz'
                logger.info(f"☁️  Uploading backup to S3/MinIO: {backup_filename}")
                
                # Upload using boto3 directly
                self._upload_to_s3(compressed_file, backup_filename)
                
                logger.info("🎉 PostgreSQL backup, compression, and upload complete!")
                return True
                
            except Exception as e:
                logger.error(f"❌ Backup failed: {e}")
                raise

    def restore_backup(self):
        """Restore PostgreSQL backup using psql"""
        logger.info(f"🔄 Restoring PostgreSQL backup for database: {self.db_name}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. Download backup from S3/MinIO
                backup_filename = self.backup_path
                if not backup_filename:
                    raise Exception("BACKUP_PATH environment variable is required for restore")
                
                logger.info(f"📥 Downloading backup from S3/MinIO: {backup_filename}")
                downloaded_file = self._download_from_s3(backup_filename, temp_dir)
                
                # 2. Extract the backup file
                logger.info(f"📦 Extracting backup file: {downloaded_file}")
                extracted_file = self._extract_backup(downloaded_file, temp_dir)
                
                # 3. Restore to database
                logger.info(f"🔄 Restoring to PostgreSQL database: {self.db_name}")
                self._restore_to_database(extracted_file)
                
                logger.info("🎉 PostgreSQL backup restore completed successfully!")
                return True
                
            except Exception as e:
                logger.error(f"❌ Restore failed: {e}")
                raise

    def _upload_to_s3(self, file_path, backup_filename):
        """Upload backup to S3/MinIO using boto3"""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Create S3 client
            s3_client = boto3.client(
                's3',
                endpoint_url=self.storage_endpoint,
                aws_access_key_id=self.storage_access_key_id,
                aws_secret_access_key=self.storage_secret_access_key,
                region_name=self.storage_region,
                use_ssl=False
            )
            
            # Create bucket if it doesn't exist (for test environments)
            try:
                s3_client.head_bucket(Bucket=self.storage_bucket)
                logger.info(f"✅ Bucket {self.storage_bucket} already exists")
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    logger.info(f"🔧 Creating bucket {self.storage_bucket}...")
                    try:
                        s3_client.create_bucket(Bucket=self.storage_bucket)
                        logger.info(f"✅ Bucket {self.storage_bucket} created successfully")
                    except Exception as create_error:
                        logger.warning(f"⚠️  Bucket creation failed: {create_error}")
                else:
                    logger.warning(f"⚠️  Bucket check failed: {e}")
            
            # Upload file
            s3_client.upload_file(file_path, self.storage_bucket, backup_filename)
            logger.info(f"✅ Backup uploaded to S3/MinIO: {backup_filename}")
            
        except Exception as e:
            logger.error(f"❌ S3 upload failed: {e}")
            raise

    def _download_from_s3(self, backup_filename: str, temp_dir: str) -> str:
        """Download backup from S3/MinIO"""
        try:
            # Try using boto3 first
            import boto3
            s3_client = boto3.client(
                's3',
                endpoint_url=self.storage_endpoint,
                aws_access_key_id=self.storage_access_key_id,
                aws_secret_access_key=self.storage_secret_access_key,
                region_name=self.storage_region,
                use_ssl=False
            )
            
            local_file = os.path.join(temp_dir, backup_filename)
            s3_client.download_file(self.storage_bucket, backup_filename, local_file)
            logger.info(f"✅ Downloaded backup using boto3: {local_file}")
            return local_file
            
        except Exception as e:
            logger.warning(f"⚠️  boto3 download failed, trying requests: {e}")
            return self._download_with_requests(backup_filename, temp_dir)

    def _download_with_requests(self, backup_filename: str, temp_dir: str) -> str:
        """Download backup using requests with AWS4 signature"""
        try:
            import requests
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            # Create AWS4 signed request
            url = f"{self.storage_endpoint}/{self.storage_bucket}/{backup_filename}"
            request = AWSRequest(method='GET', url=url)
            
            # Sign the request
            credentials = {
                'access_key': self.storage_access_key_id,
                'secret_key': self.storage_secret_access_key,
                'region': self.storage_region
            }
            SigV4Auth(credentials, 's3', self.storage_region).add_auth(request)
            
            # Make the request
            response = requests.get(url, headers=dict(request.headers))
            response.raise_for_status()
            
            # Save the file
            local_file = os.path.join(temp_dir, backup_filename)
            with open(local_file, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"✅ Downloaded backup using requests: {local_file}")
            return local_file
            
        except Exception as e:
            logger.error(f"❌ Failed to download backup: {e}")
            raise

    def _extract_backup(self, compressed_file: str, temp_dir: str) -> str:
        """Extract compressed backup file"""
        try:
            if compressed_file.endswith('.tar.gz'):
                # Handle tar.gz files
                import tarfile
                with tarfile.open(compressed_file, 'r:gz') as tar:
                    tar.extractall(temp_dir)
                
                # Find the extracted SQL file
                for file in os.listdir(temp_dir):
                    if file.endswith('.sql') and file != os.path.basename(compressed_file):
                        extracted_file = os.path.join(temp_dir, file)
                        logger.info(f"✅ Extracted tar.gz backup: {extracted_file}")
                        return extracted_file
                
                raise Exception("No SQL file found in tar.gz archive")
                
            elif compressed_file.endswith('.gz'):
                # Handle gzipped files
                extracted_file = compressed_file.replace('.gz', '')
                with gzip.open(compressed_file, 'rb') as f_in:
                    with open(extracted_file, 'wb') as f_out:
                        f_out.write(f_in.read())
                
                logger.info(f"✅ Extracted gzipped backup: {extracted_file}")
                return extracted_file
                
            else:
                # Assume it's already uncompressed
                logger.info(f"✅ Using uncompressed backup: {compressed_file}")
                return compressed_file
                
        except Exception as e:
            logger.error(f"❌ Failed to extract backup: {e}")
            raise

    def _restore_to_database(self, sql_file: str):
        """Restore SQL file to PostgreSQL database"""
        try:
            # Create database if it doesn't exist
            create_db_cmd = [
                'createdb',
                '-h', self.db_host,
                '-p', str(self.db_port),
                '-U', self.db_username,
                self.db_name
            ]
            
            env = os.environ.copy()
            if self.db_password:
                env['PGPASSWORD'] = self.db_password
            
            logger.info(f"🔧 Creating database if it doesn't exist: {self.db_name}")
            create_result = subprocess.run(create_db_cmd, env=env, capture_output=True, text=True)
            
            if create_result.returncode != 0 and 'already exists' not in create_result.stderr:
                logger.warning(f"⚠️  Database creation warning: {create_result.stderr}")
            
            # Restore the SQL file
            restore_cmd = [
                'psql',
                '-h', self.db_host,
                '-p', str(self.db_port),
                '-U', self.db_username,
                '-d', self.db_name,
                '-f', sql_file
            ]
            
            logger.info(f"🔧 Restoring SQL file: {sql_file}")
            restore_result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
            
            if restore_result.returncode == 0:
                logger.info("✅ PostgreSQL restore completed successfully")
            else:
                logger.error(f"❌ PostgreSQL restore failed: {restore_result.stderr}")
                raise Exception(f"PostgreSQL restore failed: {restore_result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Failed to restore to database: {e}")
            raise


if __name__ == '__main__':
    runner = PostgreSQLRunner()
    operation_type = os.getenv('OPERATION_TYPE', 'backup').lower()
    
    try:
        if operation_type == 'backup':
            logger.info("🔄 Starting backup operation...")
            runner.create_backup()
            runner.update_job_status("success", "PostgreSQL backup completed successfully.")
        elif operation_type == 'restore':
            logger.info("🔄 Starting restore operation...")
            runner.restore_backup()
            runner.update_job_status("success", "PostgreSQL restore completed successfully.")
        else:
            logger.error(f"❌ Invalid OPERATION_TYPE: {operation_type}. Must be 'backup' or 'restore'")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        operation_name = "backup" if operation_type == "backup" else "restore"
        runner.update_job_status("failure", f"PostgreSQL {operation_name} failed: {e}")
        sys.exit(1)