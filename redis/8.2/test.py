#!/usr/bin/env python3
"""
Plan B Database Integration Test - Redis 8.2
Tests backup and restore functionality with MinIO S3-compatible storage
Uses the shared test framework for common functionality
"""

import os
import sys
import time
import logging
import subprocess

# Add the shared directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from test_framework import DatabaseTestFramework

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedisIntegrationTest82(DatabaseTestFramework):
    """Redis 8.2 specific implementation of the database test framework"""
    
    def __init__(self):
        super().__init__(
            db_type="redis",
            db_version="8.2", 
            db_image="redis:8.2",
            default_port=6379
        )
        self.test_db = 0  # Redis database number
    
    def get_database_container_config(self) -> dict:
        """Return Redis-specific container configuration"""
        return {}  # Redis doesn't need special config
    
    def wait_for_database_ready(self) -> bool:
        """Wait for Redis to be ready and return True if successful"""
        max_retries = 30
        for i in range(max_retries):
            try:
                # Use docker exec instead of running a new container
                result = subprocess.run([
                    'docker', 'exec', self.container_name,
                    'redis-cli', 'ping'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and "PONG" in result.stdout:
                    logger.info("✅ redis is ready!")
                    return True
            except Exception as e:
                logger.debug(f"Redis not ready yet: {e}")
            time.sleep(2)
        logger.error("❌ Redis failed to start within timeout")
        return False
    
    def create_test_data(self) -> bool:
        """Create test data in Redis"""
        logger.info("📝 Creating test data in Redis...")
        
        try:
            # Create test data using redis-cli via docker exec
            test_commands = [
                "SET test_key_1 'Hello Redis 8.2'",
                "SET test_key_2 'Plan B Backup Test'",
                "SET test_key_3 'Integration Test Data'",
                "HSET test_hash field1 'value1' field2 'value2'",
                "LPUSH test_list 'item1' 'item2' 'item3'",
                "SADD test_set 'member1' 'member2' 'member3'"
            ]
            
            for cmd in test_commands:
                result = subprocess.run([
                    'docker', 'exec', self.container_name,
                    'redis-cli', cmd
                ], capture_output=True, text=True, timeout=5)
                
                logger.debug(f"Command '{cmd}' result: {result.stdout.strip()}")
            
            logger.info("✅ Test data created successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create test data: {e}")
            return False
    
    def get_backup_environment_vars(self) -> dict:
        """Return Redis-specific environment variables for backup"""
        return {
            'DB_HOST': self.container_name,
            'DB_PORT': '6379',
            'DB_NAME': str(self.test_db),
            'DB_USERNAME': 'redis',  # Provide a dummy username
            'DB_PASSWORD': ''         # Empty password for test Redis
        }


def main():
    """Run Redis 8.2 integration test using the shared framework"""
    logger.info("🚀 Starting redis 8.2 Integration Test")
    test = RedisIntegrationTest82()
    try:
        test.run_full_test()
        logger.info("🎉 redis 8.2 integration test completed successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False
    finally:
        test.cleanup()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)