#!/usr/bin/env python3
import sys
import os
import subprocess
import logging
import time
# Add the shared directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from test_framework import DatabaseTestFramework

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostgreSQLIntegrationTest13(DatabaseTestFramework):
    """PostgreSQL 17 specific implementation of the database test framework"""
    
    def __init__(self):
        super().__init__(
            db_type="postgresql",
            db_version="13", 
            db_image="postgres:13",
            default_port=5432
        )
        self.test_db = "planb_testdb"
        self.postgres_user = "postgres"
        self.postgres_password = "planb_test_pass"
    
    def get_database_container_config(self) -> dict:
        """Return PostgreSQL-specific container configuration"""
        return {
            'environment': {
                "POSTGRES_PASSWORD": self.postgres_password,
                "POSTGRES_DB": self.test_db,
            }
        }
    
    def wait_for_database_ready(self) -> bool:
        """Wait for PostgreSQL to be ready and return True if successful"""
        max_retries = 30
        for i in range(max_retries):
            try:
                # Use docker exec to test PostgreSQL connection
                result = subprocess.run([
                    '/usr/local/bin/docker', 'exec', self.container_name,
                    'psql', '-h', 'localhost', '-U', self.postgres_user, '-d', 'postgres', '-c', 'SELECT 1;'
                ], capture_output=True, text=True, timeout=5, env={'PGPASSWORD': self.postgres_password})
                
                if result.returncode == 0:
                    logger.info("✅ PostgreSQL is ready!")
                    return True
                    
            except subprocess.TimeoutExpired:
                logger.info(f"⏳ Waiting for PostgreSQL to be ready... (attempt {i+1}/{max_retries})")
            except Exception as e:
                logger.info(f"⏳ Waiting for PostgreSQL to be ready... (attempt {i+1}/{max_retries}): {e}")
            
            time.sleep(2)
        
        logger.error("❌ PostgreSQL failed to start within timeout")
        return False
    
    def create_test_data(self) -> bool:
        """Create test data in PostgreSQL"""
        logger.info("📝 Creating test data in PostgreSQL...")
        
        try:
            # Create test database
            create_db_result = subprocess.run([
                '/usr/local/bin/docker', 'exec', self.container_name,
                'psql', '-h', 'localhost', '-U', self.postgres_user, '-c', f'CREATE DATABASE {self.test_db};'
            ], capture_output=True, text=True, env={'PGPASSWORD': self.postgres_password})
            
            if create_db_result.returncode != 0 and 'already exists' not in create_db_result.stderr:
                logger.error(f"❌ Failed to create test database: {create_db_result.stderr}")
                return False
            
            # Create test tables and data
            test_data_sql = '''
            -- Create movies table
            CREATE TABLE IF NOT EXISTS movies (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                year INTEGER,
                rating DECIMAL(3,1)
            );
            
            -- Create actors table
            CREATE TABLE IF NOT EXISTS actors (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                birth_year INTEGER
            );
            
            -- Insert test data
            INSERT INTO movies (title, year, rating) VALUES 
                ('The Shawshank Redemption', 1994, 9.3),
                ('The Godfather', 1972, 9.2),
                ('The Dark Knight', 2008, 9.0);
            
            INSERT INTO actors (name, birth_year) VALUES 
                ('Morgan Freeman', 1937),
                ('Marlon Brando', 1924),
                ('Christian Bale', 1974);
            '''
            
            insert_result = subprocess.run([
                '/usr/local/bin/docker', 'exec', self.container_name,
                'psql', '-h', 'localhost', '-U', self.postgres_user, '-d', self.test_db, '-c', test_data_sql
            ], capture_output=True, text=True, env={'PGPASSWORD': self.postgres_password})
            
            if insert_result.returncode == 0:
                logger.info("✅ Test data created successfully")
                return True
            else:
                logger.error(f"❌ Failed to setup test data: {insert_result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Failed to setup test data: {e}")
            return False
    
    def get_backup_environment_vars(self) -> dict:
        """Return PostgreSQL-specific environment variables for backup"""
        import socket
        host_ip = socket.gethostbyname(socket.gethostname())
        
        return {
            'DB_HOST': host_ip,
            'DB_PORT': str(self.db_port),
            'DB_NAME': self.test_db,
            'DB_USERNAME': self.postgres_user,
            'DB_PASSWORD': self.postgres_password
        }

    def verify_restored_data(self) -> bool:
        """Verify that restored data matches original test data"""
        logger.info("🔍 Verifying restored data...")
        
        try:
            # Check if tables exist and have correct data
            verify_script = '''
            SELECT COUNT(*) as movie_count FROM movies;
            SELECT COUNT(*) as actor_count FROM actors;
            
            -- Verify specific data
            SELECT title FROM movies WHERE title = 'The Shawshank Redemption';
            SELECT name FROM actors WHERE name = 'Morgan Freeman';
            '''
            
            verify_result = subprocess.run([
                '/usr/local/bin/docker', 'exec', self.container_name,
                'psql', '-h', 'localhost', '-U', self.postgres_user, '-d', self.test_db, '-c', verify_script
            ], capture_output=True, text=True, env={'PGPASSWORD': self.postgres_password})
            
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
    """Run PostgreSQL 17 integration test using the shared framework"""
    logger.info("🚀 Starting postgresql 13 Integration Test")
    test = PostgreSQLIntegrationTest13()
    try:
        # Run the complete backup and restore test using the shared framework
        success = test.run_backup_and_restore_test()
        
        if success:
            logger.info("🎉 postgresql 13 integration test completed successfully!")
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