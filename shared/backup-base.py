#!/usr/bin/env python3
"""
Plan B Database Backup Runner - Shared Base Class
Lightweight, database-agnostic backup runner
"""

import os
import sys
import json
import subprocess
import requests
from datetime import datetime
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BackupRunnerBase:
    def __init__(self):
        self.job_config = self.load_job_config()
        self.setup_storage_credentials()
        
    def load_job_config(self):
        """Load job configuration from environment variables"""
        try:
            return {
                'job_id': os.environ['JOB_ID'],
                'connection': {
                    'engine': os.environ['DB_ENGINE'],
                    'host': os.environ['DB_HOST'],
                    'port': int(os.environ['DB_PORT']),
                    'database': os.environ['DB_NAME'],
                    'username': os.environ['DB_USERNAME'],
                    'password': os.environ['DB_PASSWORD'],
                },
                'storage': {
                    'type': os.environ['STORAGE_TYPE'],
                    'endpoint': os.environ['STORAGE_ENDPOINT'],
                    'bucket': os.environ['STORAGE_BUCKET'],
                    'region': os.environ['STORAGE_REGION'],
                    'access_key_id': os.environ['STORAGE_ACCESS_KEY_ID'],
                    'secret_access_key': os.environ['STORAGE_SECRET_ACCESS_KEY'],
                },
                'backup_path': os.environ['BACKUP_PATH'],
                'retention_days': int(os.environ.get('RETENTION_DAYS', '30')),
                'callback_url': os.environ['CALLBACK_URL'],
                'callback_secret': os.environ['CALLBACK_SECRET'],
            }
        except KeyError as e:
            logger.error(f"Missing required environment variable: {e}")
            sys.exit(1)
    
    def setup_storage_credentials(self):
        """Setup storage credentials for S3-compatible operations"""
        storage = self.job_config['storage']
        
        # Configure AWS CLI
        os.environ['AWS_ACCESS_KEY_ID'] = storage['access_key_id']
        os.environ['AWS_SECRET_ACCESS_KEY'] = storage['secret_access_key']
        os.environ['AWS_DEFAULT_REGION'] = storage['region']
        
        # Set custom endpoint if not AWS S3
        if storage['type'] != 's3':
            os.environ['AWS_ENDPOINT_URL'] = storage['endpoint']
    
    def run_backup(self):
        """Execute the backup process - to be implemented by subclasses"""
        logger.info(f"Starting backup job {self.job_config['job_id']}")
        
        try:
            # Update job status to running
            self.update_job_status('running', 'Backup process started')
            
            # Create backup file
            backup_file = self.create_backup()
            
            # Compress backup if needed
            compressed_file = self.compress_backup(backup_file)
            
            # Upload to storage
            self.upload_backup(compressed_file)
            
            # Clean up local files
            self.cleanup_files(backup_file, compressed_file)
            
            # Update job status to success
            self.update_job_status('success', 'Backup completed successfully')
            
            logger.info(f"Backup job {self.job_config['job_id']} completed successfully")
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            self.update_job_status('failed', str(e))
            sys.exit(1)
    
    def create_backup(self):
        """Create database backup - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement create_backup method")
    
    def compress_backup(self, backup_file):
        """Compress backup file if not already compressed"""
        if backup_file.endswith('.gz'):
            return backup_file
        
        compressed_file = f"{backup_file}.gz"
        
        cmd = ['gzip', '-9', backup_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Compression failed: {result.stderr}")
        
        logger.info(f"Backup compressed: {compressed_file}")
        return compressed_file
    
    def upload_backup(self, backup_file):
        """Upload backup to S3-compatible storage"""
        storage = self.job_config['storage']
        s3_key = self.job_config['backup_path']
        
        # Build AWS CLI command
        cmd = ['aws', 's3', 'cp', backup_file, f"s3://{storage['bucket']}/{s3_key}"]
        
        # Add endpoint URL for non-AWS S3
        if storage['type'] != 's3':
            cmd.extend(['--endpoint-url', storage['endpoint']])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"S3 upload failed: {result.stderr}")
        
        # Get file size
        file_size = os.path.getsize(backup_file)
        
        logger.info(f"Backup uploaded to {storage['bucket']}/{s3_key} ({file_size} bytes)")
        
        # Update job with file size
        self.update_job_metadata({'bytes': file_size, 'object_key': s3_key})
    
    def cleanup_files(self, *files):
        """Clean up temporary files"""
        for file in files:
            if os.path.exists(file):
                os.unlink(file)
                logger.info(f"Cleaned up: {file}")
    
    def update_job_status(self, status, message=None):
        """Update job status via callback to Plan B API"""
        try:
            payload = {
                'job_id': self.job_config['job_id'],
                'status': status,
                'message': message,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {self.job_config['callback_secret']}"
            }
            
            response = requests.post(
                self.job_config['callback_url'],
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            logger.info(f"Job status updated to: {status}")
            
        except Exception as e:
            logger.warning(f"Failed to update job status: {e}")
    
    def update_job_metadata(self, metadata):
        """Update job metadata via callback to Plan B API"""
        try:
            payload = {
                'job_id': self.job_config['job_id'],
                'metadata': metadata,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {self.job_config['callback_secret']}"
            }
            
            response = requests.post(
                f"{self.job_config['callback_url']}/metadata",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            logger.info("Job metadata updated")
            
        except Exception as e:
            logger.warning(f"Failed to update job metadata: {e}")
