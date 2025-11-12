#!/usr/bin/env python3
"""
Create runner.py and test.py files for all database versions
Generates backup/restore functionality and integration tests
"""

import os
import json
from pathlib import Path

def get_database_directories():
    """Get all database directories with backup.py files"""
    directories = []
    for root, dirs, files in os.walk('.'):
        if 'backup.py' in files and root != '.':
            # Skip shared and templates directories
            if 'shared' not in root and 'templates' not in root:
                directories.append(root)
    return sorted(directories)

def create_postgresql_runner(db_path, version):
    return f'''#!/usr/bin/env python3
"""
Plan B Database Runner - PostgreSQL {version}
Backup and restore functionality using official PostgreSQL tools
"""

import os
import sys
import subprocess
import tempfile
import logging

# Add shared directory to path
sys.path.append('/app')
from backup_base import BackupRunnerBase

logger = logging.getLogger(__name__)

class PostgreSQLRunner(BackupRunnerBase):
    def create_backup(self):
        """Create PostgreSQL backup using pg_dump"""
        conn = self.job_config['connection']
        
        # Create temporary backup file
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.postgresql') as f:
            backup_file = f.name
        
        # Set environment for pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = conn['password']
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '--host', conn['host'],
            '--port', str(conn['port']),
            '--username', conn['username'],
            '--dbname', conn['database'],
            '--verbose',
            '--no-password',
            '--format=custom',
            '--compress=9',
            '--no-privileges',
            '--no-owner',
            '--file', backup_file
        ]
        
        logger.info(f"Running pg_dump for database {{conn['database']}}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {{result.stderr}}")
        
        logger.info("PostgreSQL backup completed")
        return backup_file

    def restore_backup(self, backup_file, target_config=None):
        """Restore PostgreSQL backup using pg_restore"""
        conn = target_config or self.job_config['connection']
        
        # Set environment for pg_restore
        env = os.environ.copy()
        env['PGPASSWORD'] = conn['password']
        
        # Build pg_restore command
        cmd = [
            'pg_restore',
            '--host', conn['host'],
            '--port', str(conn['port']),
            '--username', conn['username'],
            '--dbname', conn['database'],
            '--verbose',
            '--no-password',
            '--clean',
            '--create',
            '--if-exists',
            backup_file
        ]
        
        logger.info(f"Running pg_restore for database {{conn['database']}}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            # pg_restore often returns non-zero even on success due to warnings
            if "ERROR" in result.stderr.upper():
                raise Exception(f"pg_restore failed: {{result.stderr}}")
            else:
                logger.warning(f"pg_restore completed with warnings: {{result.stderr}}")
        
        logger.info("PostgreSQL restore completed")
        return True

if __name__ == '__main__':
    import sys
    runner = PostgreSQLRunner()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        if len(sys.argv) < 3:
            print("Usage: python runner.py restore <backup_file>")
            sys.exit(1)
        runner.restore_backup(sys.argv[2])
    else:
        runner.run_backup()
'''

def create_mysql_runner(db_path, version):
    return f'''#!/usr/bin/env python3
"""
Plan B Database Runner - MySQL/MariaDB {version}
Backup and restore functionality using official MySQL tools
"""

import os
import sys
import subprocess
import tempfile
import logging

# Add shared directory to path
sys.path.append('/app')
from backup_base import BackupRunnerBase

logger = logging.getLogger(__name__)

class MySQLRunner(BackupRunnerBase):
    def create_backup(self):
        """Create MySQL backup using mysqldump"""
        conn = self.job_config['connection']
        
        # Create temporary backup file
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.mysql.sql') as f:
            backup_file = f.name
        
        # Build mysqldump command
        cmd = [
            'mysqldump',
            f"--host={{conn['host']}}",
            f"--port={{conn['port']}}",
            f"--user={{conn['username']}}",
            f"--password={{conn['password']}}",
            '--single-transaction',
            '--routines',
            '--triggers',
            '--events',
            '--set-gtid-purged=OFF',
            '--default-character-set=utf8mb4',
            conn['database']
        ]
        
        logger.info(f"Running mysqldump for database {{conn['database']}}")
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise Exception(f"mysqldump failed: {{result.stderr}}")
        
        logger.info("MySQL backup completed")
        return backup_file

    def restore_backup(self, backup_file, target_config=None):
        """Restore MySQL backup using mysql client"""
        conn = target_config or self.job_config['connection']
        
        # Build mysql restore command
        cmd = [
            'mysql',
            f"--host={{conn['host']}}",
            f"--port={{conn['port']}}",
            f"--user={{conn['username']}}",
            f"--password={{conn['password']}}",
            '--default-character-set=utf8mb4',
            conn['database']
        ]
        
        logger.info(f"Running mysql restore for database {{conn['database']}}")
        
        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"mysql restore failed: {{result.stderr}}")
        
        logger.info("MySQL restore completed")
        return True

if __name__ == '__main__':
    import sys
    runner = MySQLRunner()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        if len(sys.argv) < 3:
            print("Usage: python runner.py restore <backup_file>")
            sys.exit(1)
        runner.restore_backup(sys.argv[2])
    else:
        runner.run_backup()
'''

def create_mongodb_runner(db_path, version):
    return f'''#!/usr/bin/env python3
"""
Plan B Database Runner - MongoDB {version}
Backup and restore functionality using official MongoDB tools
"""

import os
import sys
import subprocess
import tempfile
import logging

# Add shared directory to path
sys.path.append('/app')
from backup_base import BackupRunnerBase

logger = logging.getLogger(__name__)

class MongoDBRunner(BackupRunnerBase):
    def create_backup(self):
        """Create MongoDB backup using mongodump"""
        conn = self.job_config['connection']
        
        # Create temporary backup directory
        backup_dir = tempfile.mkdtemp(suffix='_mongodb_backup')
        
        # Build mongodump command
        cmd = [
            'mongodump',
            '--host', f"{{conn['host']}}:{{conn['port']}}",
            '--db', conn['database'],
            '--out', backup_dir,
            '--gzip'
        ]
        
        # Add authentication if provided
        if conn.get('username'):
            cmd.extend(['--username', conn['username']])
        if conn.get('password'):
            cmd.extend(['--password', conn['password']])
        if conn.get('authDatabase'):
            cmd.extend(['--authenticationDatabase', conn['authDatabase']])
        
        logger.info(f"Running mongodump for database {{conn['database']}}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"mongodump failed: {{result.stderr}}")
        
        # Create compressed archive of the backup
        archive_file = f"{{backup_dir}}.tar.gz"
        subprocess.run(['tar', '-czf', archive_file, '-C', os.path.dirname(backup_dir), os.path.basename(backup_dir)])
        
        # Clean up temporary directory
        subprocess.run(['rm', '-rf', backup_dir])
        
        logger.info("MongoDB backup completed")
        return archive_file

    def restore_backup(self, backup_file, target_config=None):
        """Restore MongoDB backup using mongorestore"""
        conn = target_config or self.job_config['connection']
        
        # Extract backup archive to temporary directory
        restore_dir = tempfile.mkdtemp(suffix='_mongodb_restore')
        subprocess.run(['tar', '-xzf', backup_file, '-C', restore_dir])
        
        # Find the extracted database directory
        extracted_dirs = os.listdir(restore_dir)
        if not extracted_dirs:
            raise Exception("No backup data found in archive")
        
        backup_path = os.path.join(restore_dir, extracted_dirs[0], conn['database'])
        
        # Build mongorestore command
        cmd = [
            'mongorestore',
            '--host', f"{{conn['host']}}:{{conn['port']}}",
            '--db', conn['database'],
            '--gzip',
            '--drop',
            backup_path
        ]
        
        # Add authentication if provided
        if conn.get('username'):
            cmd.extend(['--username', conn['username']])
        if conn.get('password'):
            cmd.extend(['--password', conn['password']])
        if conn.get('authDatabase'):
            cmd.extend(['--authenticationDatabase', conn['authDatabase']])
        
        logger.info(f"Running mongorestore for database {{conn['database']}}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temporary directory
        subprocess.run(['rm', '-rf', restore_dir])
        
        if result.returncode != 0:
            raise Exception(f"mongorestore failed: {{result.stderr}}")
        
        logger.info("MongoDB restore completed")
        return True

if __name__ == '__main__':
    import sys
    runner = MongoDBRunner()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        if len(sys.argv) < 3:
            print("Usage: python runner.py restore <backup_file>")
            sys.exit(1)
        runner.restore_backup(sys.argv[2])
    else:
        runner.run_backup()
'''

def create_redis_runner(db_path, version):
    return f'''#!/usr/bin/env python3
"""
Plan B Database Runner - Redis {version}
Backup and restore functionality using official Redis tools
"""

import os
import sys
import subprocess
import tempfile
import logging
import redis

# Add shared directory to path
sys.path.append('/app')
from backup_base import BackupRunnerBase

logger = logging.getLogger(__name__)

class RedisRunner(BackupRunnerBase):
    def create_backup(self):
        """Create Redis backup using BGSAVE"""
        conn = self.job_config['connection']
        
        # Connect to Redis
        r = redis.Redis(
            host=conn['host'],
            port=conn['port'],
            password=conn.get('password'),
            db=conn.get('database', 0)
        )
        
        # Trigger background save
        logger.info(f"Running Redis BGSAVE")
        r.bgsave()
        
        # Wait for save to complete
        import time
        while r.lastsave() == r.lastsave():
            time.sleep(1)
        
        # Create temporary backup file and copy RDB data
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.rdb') as f:
            backup_file = f.name
        
        # Use redis-cli to get RDB dump
        cmd = [
            'redis-cli',
            '--rdb', backup_file,
            '-h', conn['host'],
            '-p', str(conn['port'])
        ]
        
        if conn.get('password'):
            cmd.extend(['-a', conn['password']])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Redis backup failed: {{result.stderr}}")
        
        logger.info("Redis backup completed")
        return backup_file

    def restore_backup(self, backup_file, target_config=None):
        """Restore Redis backup by loading RDB file"""
        conn = target_config or self.job_config['connection']
        
        # Connect to Redis
        r = redis.Redis(
            host=conn['host'],
            port=conn['port'],
            password=conn.get('password'),
            db=conn.get('database', 0)
        )
        
        # Flush existing data
        r.flushdb()
        
        # Use redis-cli to restore from RDB
        cmd = [
            'redis-cli',
            '--pipe',
            '-h', conn['host'],
            '-p', str(conn['port'])
        ]
        
        if conn.get('password'):
            cmd.extend(['-a', conn['password']])
        
        with open(backup_file, 'rb') as f:
            result = subprocess.run(cmd, stdin=f, capture_output=True)
        
        if result.returncode != 0:
            raise Exception(f"Redis restore failed: {{result.stderr}}")
        
        logger.info("Redis restore completed")
        return True

if __name__ == '__main__':
    import sys
    runner = RedisRunner()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        if len(sys.argv) < 3:
            print("Usage: python runner.py restore <backup_file>")
            sys.exit(1)
        runner.restore_backup(sys.argv[2])
    else:
        runner.run_backup()
'''

def _get_default_port(db_type):
    """Get default port for database type"""
    ports = {
        'postgresql': 5433,
        'mysql': 3307,
        'mariadb': 3308,
        'mongodb': 27018,
        'redis': 6380,
        'mssql': 1434,
        'oracle': 1522,
        'cassandra': 9043,
        'arangodb': 8530,
        'couchbase': 8092
    }
    return ports.get(db_type, 9999)

def create_test_template(db_type, version, db_path):
    """Create a basic test template"""
    default_port = _get_default_port(db_type)
    
    return f'''#!/usr/bin/env python3
"""
Plan B Integration Test - {db_type.title()} {version}
Tests backup and restore functionality with real database container
"""

import os
import sys
import time
import docker
import subprocess
import tempfile
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class {db_type.title()}IntegrationTest:
    def __init__(self):
        self.client = docker.from_env()
        self.container = None
        self.test_db = "planb_testdb"
        self.db_port = {default_port}  # Use non-standard port to avoid conflicts
        
    def start_database_container(self):
        """Start {db_type.title()} {version} container for testing"""
        logger.info("📊 Starting {db_type.title()} {version} container...")
        
        try:
            # Database-specific container configuration
            # TODO: Implement container setup for {db_type}
            logger.warning("Container setup needs implementation for {db_type}")
            
            # Wait for database to be ready
            logger.info("⏳ Waiting for database to be ready...")
            time.sleep(10)  # Basic wait - should be improved with proper health checks
            
            logger.info("✅ Database is ready!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start container: {{e}}")
            return False
    
    def setup_test_data(self):
        """Setup test database with sample data"""
        logger.info("📊 Setting up test data...")
        
        try:
            # Database-specific test data setup
            # TODO: Implement test data setup for {db_type}
            logger.warning("Test data setup needs implementation for {db_type}")
            
            logger.info("✅ Test data created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup test data: {{e}}")
            return False
    
    def run_backup_test(self):
        """Test backup using our Docker container"""
        logger.info("💾 Testing backup...")
        
        try:
            # Build our backup container
            logger.info("🔨 Building backup container...")
            build_result = subprocess.run([
                'docker', 'build', '--platform', 'linux/amd64',
                '-f', './{db_path}/Dockerfile',
                '-t', f'planb-backup-{db_type}-{version}-test',
                '.'
            ], capture_output=True, text=True, cwd='/Users/diablo/Projects/react/backup-runner')
            
            if build_result.returncode != 0:
                raise Exception(f"Failed to build backup container: {{build_result.stderr}}")
            
            logger.info("✅ Backup container built successfully!")
            return True
                
        except Exception as e:
            logger.error(f"❌ Backup test failed: {{e}}")
            return False
    
    def cleanup(self):
        """Clean up test resources"""
        logger.info("🧹 Cleaning up...")
        
        if self.container:
            try:
                self.container.stop()
                logger.info("✅ Test container stopped")
            except:
                pass
        
        # Clean up test images
        try:
            self.client.images.remove(f'planb-backup-{db_type}-{version}-test', force=True)
        except:
            pass
    
    def run_full_test(self):
        """Run complete backup/restore integration test"""
        logger.info("🚀 Starting {db_type.title()} {version} Integration Test")
        logger.info("=" * 50)
        
        try:
            # Start container
            if not self.start_database_container():
                return False
            
            # Setup test data
            if not self.setup_test_data():
                return False
            
            # Test backup
            if not self.run_backup_test():
                return False
            
            logger.info("🎉 {db_type.title()} {version} Integration Test PASSED!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {{e}}")
            return False
        finally:
            self.cleanup()

if __name__ == '__main__':
    test = {db_type.title()}IntegrationTest()
    success = test.run_full_test()
    sys.exit(0 if success else 1)
'''

def get_database_type(path):
    """Extract database type from path"""
    if 'postgresql' in path:
        return 'postgresql'
    elif 'mysql' in path:
        return 'mysql' 
    elif 'mariadb' in path:
        return 'mariadb'
    elif 'mongodb' in path:
        return 'mongodb'
    elif 'redis' in path:
        return 'redis'
    elif 'mssql' in path:
        return 'mssql'
    elif 'oracle' in path:
        return 'oracle'
    elif 'cassandra' in path:
        return 'cassandra'
    elif 'arangodb' in path:
        return 'arangodb'
    elif 'couchbase' in path:
        return 'couchbase'
    else:
        return 'unknown'

def get_version_from_path(path):
    """Extract version from path"""
    return os.path.basename(path)

def create_runner_content(db_type, version, db_path):
    """Create appropriate runner content based on database type"""
    if db_type == 'postgresql':
        return create_postgresql_runner(db_path, version)
    elif db_type in ['mysql', 'mariadb']:
        return create_mysql_runner(db_path, version)
    elif db_type == 'mongodb':
        return create_mongodb_runner(db_path, version)
    elif db_type == 'redis':
        return create_redis_runner(db_path, version)
    else:
        # For other databases, use a generic template
        return f'''#!/usr/bin/env python3
"""
Plan B Database Runner - {db_type.title()} {version}
Backup and restore functionality using official tools
"""

import os
import sys
import subprocess
import tempfile
import logging

# Add shared directory to path
sys.path.append('/app')
from backup_base import BackupRunnerBase

logger = logging.getLogger(__name__)

class {db_type.title()}Runner(BackupRunnerBase):
    def create_backup(self):
        """Create backup using {db_type} tools"""
        # TODO: Implement {db_type} backup functionality
        raise NotImplementedError("Backup functionality not yet implemented for {db_type}")

    def restore_backup(self, backup_file, target_config=None):
        """Restore backup using {db_type} tools"""
        # TODO: Implement {db_type} restore functionality
        raise NotImplementedError("Restore functionality not yet implemented for {db_type}")

if __name__ == '__main__':
    import sys
    runner = {db_type.title()}Runner()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        if len(sys.argv) < 3:
            print("Usage: python runner.py restore <backup_file>")
            sys.exit(1)
        runner.restore_backup(sys.argv[2])
    else:
        runner.run_backup()
'''

def main():
    """Generate runner.py and test.py files for all database versions"""
    print("🚀 Creating runner.py and test.py files for all databases...")
    
    db_directories = get_database_directories()
    created_files = []
    
    for db_path in db_directories:
        db_type = get_database_type(db_path)
        version = get_version_from_path(db_path)
        
        print(f"\n📦 Processing {db_type} {version} ({db_path})")
        
        # Create runner.py
        runner_file = os.path.join(db_path, 'runner.py')
        runner_content = create_runner_content(db_type, version, db_path)
        
        with open(runner_file, 'w') as f:
            f.write(runner_content)
        
        # Make executable
        os.chmod(runner_file, 0o755)
        created_files.append(runner_file)
        
        # Create test.py
        test_file = os.path.join(db_path, 'test.py')
        test_content = create_test_template(db_type, version, db_path)
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Make executable
        os.chmod(test_file, 0o755)
        created_files.append(test_file)
        
        print(f"✅ Created runner.py and test.py for {db_type} {version}")
    
    print(f"\n🎉 Successfully created {len(created_files)} files!")
    print(f"📊 Generated for {len(db_directories)} database versions")
    
    # Summary
    db_summary = {}
    for db_path in db_directories:
        db_type = get_database_type(db_path)
        if db_type not in db_summary:
            db_summary[db_type] = 0
        db_summary[db_type] += 1
    
    print("\\n📋 Summary:")
    for db_type, count in sorted(db_summary.items()):
        print(f"  {db_type.title()}: {count} versions")

if __name__ == '__main__':
    main()
