#!/usr/bin/env python3
"""
Plan B Database Integration Test - MySQL 8.4
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


class MySQLIntegrationTest84(DatabaseTestFramework):
    """MySQL 8.4 specific implementation of the database test framework"""
    
    def __init__(self):
        super().__init__(
            db_type="mysql",
            db_version="8.4", 
            db_image="mysql:8.4",
            default_port=3306
        )
        self.test_db = "planb_testdb"
        self.mysql_user = "root"
        self.mysql_password = "planb_test_pass"
    
    def get_database_container_config(self) -> dict:
        """Return MySQL-specific container configuration"""
        return {
            'environment': {
                "MYSQL_ROOT_PASSWORD": self.mysql_password,
                "MYSQL_DATABASE": self.test_db,
            }
        }
    
    def wait_for_database_ready(self) -> bool:
        """Wait for MySQL to be ready and return True if successful"""
        max_retries = 30
        for i in range(max_retries):
            try:
                # Use docker exec to test MySQL connection
                result = subprocess.run([
                    'docker', 'exec', self.container_name,
                    'mysql', '-u', self.mysql_user, f'-p{self.mysql_password}', '-e', 'SELECT 1;'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    logger.info("✅ mysql is ready!")
                    return True
            except Exception as e:
                logger.debug(f"MySQL not ready yet: {e}")
            time.sleep(2)
        logger.error("❌ MySQL failed to start within timeout")
        return False
    
    def create_test_data(self) -> bool:
        """Create test data in MySQL"""
        logger.info("📝 Creating test data in MySQL...")
        
        try:
            # Create test tables and insert data using mysql client
            setup_script = f'''
            USE {self.test_db};
            
            -- Create movies table
            CREATE TABLE IF NOT EXISTS movies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                year INT,
                rating DECIMAL(3,1)
            );
            
            -- Create actors table
            CREATE TABLE IF NOT EXISTS actors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                age INT
            );
            
            -- Insert sample movie data
            INSERT INTO movies (title, year, rating) VALUES 
                ('The Shawshank Redemption', 1994, 9.3),
                ('The Godfather', 1972, 9.2),
                ('The Dark Knight', 2008, 9.0);
            
            -- Insert sample actor data
            INSERT INTO actors (name, age) VALUES 
                ('Morgan Freeman', 87),
                ('Marlon Brando', 80),
                ('Heath Ledger', 28);
            '''
            
            setup_result = subprocess.run([
                'docker', 'exec', self.container_name,
                'mysql', '-u', self.mysql_user, f'-p{self.mysql_password}', '-e', setup_script
            ], capture_output=True, text=True)
            
            if setup_result.returncode == 0:
                logger.info("✅ Test data created: 3 movies, 3 actors")
                return True
            else:
                logger.error(f"❌ Failed to setup test data: {setup_result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to setup test data: {e}")
            return False
    
    def get_backup_environment_vars(self) -> dict:
        """Return MySQL-specific environment variables for backup"""
        # Get host IP address for connections when using host network
        import socket
        host_ip = socket.gethostbyname(socket.gethostname())
        
        return {
            'DB_HOST': host_ip,  # Use host IP for host network
            'DB_PORT': str(self.db_port),  # Use the actual port the container is running on
            'DB_NAME': self.test_db,
            'DB_USERNAME': self.mysql_user,
            'DB_PASSWORD': self.mysql_password
        }

    def verify_restored_data(self) -> bool:
        """Verify that restored data matches original test data"""
        logger.info("🔍 Verifying restored data...")
        
        try:
            # Check if tables exist and have correct data
            verify_script = f'''
            USE {self.test_db};
            
            -- Check movies table
            SELECT COUNT(*) as movie_count FROM movies;
            SELECT COUNT(*) as actor_count FROM actors;
            
            -- Verify specific data
            SELECT title FROM movies WHERE title = 'The Shawshank Redemption';
            SELECT name FROM actors WHERE name = 'Morgan Freeman';
            '''
            
            verify_result = subprocess.run([
                'docker', 'exec', self.container_name,
                'mysql', '-u', self.mysql_user, f'-p{self.mysql_password}', '-e', verify_script
            ], capture_output=True, text=True)
            
            if verify_result.returncode == 0:
                output = verify_result.stdout
                logger.info("✅ Restored data verification:")
                logger.info(output)
                
                # Check for expected data
                if 'The Shawshank Redemption' in output and 'Morgan Freeman' in output:
                    logger.info("✅ Restored data matches original test data!")
                    return True
                else:
                    logger.error("❌ Restored data does not match original test data")
                    return False
            else:
                logger.error(f"❌ Failed to verify restored data: {verify_result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to verify restored data: {e}")
            return False


def main():
    """Run MySQL 8.4 integration test using the shared framework"""
    logger.info("🚀 Starting mysql 8.4 Integration Test")
    test = MySQLIntegrationTest84()
    try:
        # Run the complete backup and restore test using the shared framework
        success = test.run_backup_and_restore_test()
        
        if success:
            logger.info("🎉 mysql 8.4 integration test completed successfully!")
            logger.info("✅ Backup, restore, and verification all passed!")
            return True
        else:
            logger.error("❌ Integration test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False
    finally:
        test.cleanup()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)