# Plan B Database Backup Runner

Multi-database backup solution with version-specific container support for Cloud Run.

## 🏗️ Architecture

This repository contains lightweight, database-specific backup containers built on Alpine Linux for optimal performance and minimal resource usage.

### Database Support

| Database          | Versions               | Status     |
| ----------------- | ---------------------- | ---------- |
| 🐘 **PostgreSQL** | 12, 13, 14, 15, 16, 17 | ✅ Ready   |
| 🐬 **MySQL**      | latest                 | ✅ Ready   |
| 🦭 **MariaDB**    | latest                 | ✅ Ready   |
| 🍃 **MongoDB**    | latest                 | ✅ Ready   |
| 🏢 **SQL Server** | latest                 | 📋 Planned |
| 🔶 **Oracle**     | latest                 | 📋 Planned |
| 🏛️ **Cassandra**  | latest                 | 📋 Planned |
| 🥑 **ArangoDB**   | latest                 | 📋 Planned |
| 🛋️ **CouchBase**  | latest                 | 📋 Planned |

## 📁 Directory Structure

```
backup-runner/
├── shared/                 # Shared base classes and utilities
│   ├── backup_base.py     # Common backup runner functionality
│   └── entrypoint.sh      # Shared container entrypoint
├── postgresql/            # PostgreSQL containers
│   ├── 12/               # PostgreSQL 12
│   ├── 13/               # PostgreSQL 13
│   ├── 14/               # PostgreSQL 14
│   ├── 15/               # PostgreSQL 15
│   ├── 16/               # PostgreSQL 16
│   └── 17/               # PostgreSQL 17
├── mysql/                 # MySQL container
├── mariadb/              # MariaDB container
├── mongodb/              # MongoDB container
├── build-all.sh          # Build and push all containers
└── README.md
```

## 🚀 Quick Start

### Build All Containers

```bash
# Build and push all containers to Google Container Registry
./build-all.sh
```

### Build Single Container

```bash
# Build PostgreSQL 16 container
cd postgresql/16
docker build -t gcr.io/apito-cms/plan-b-backup-postgresql:16 .
docker push gcr.io/apito-cms/plan-b-backup-postgresql:16
```

## 🛠️ Container Images

All containers follow this naming pattern:

```
gcr.io/apito-cms/plan-b-backup-<database>:<version>
```

Examples:

- `gcr.io/apito-cms/plan-b-backup-postgresql:16`
- `gcr.io/apito-cms/plan-b-backup-mysql:latest`
- `gcr.io/apito-cms/plan-b-backup-mongodb:latest`

## 🔧 Environment Variables

All containers require these environment variables:

### Database Connection

- `JOB_ID` - Unique backup job identifier
- `DB_ENGINE` - Database engine (postgres, mysql, mongodb, etc.)
- `DB_HOST` - Database hostname
- `DB_PORT` - Database port
- `DB_NAME` - Database name
- `DB_USERNAME` - Database username
- `DB_PASSWORD` - Database password

### Storage Configuration

- `STORAGE_TYPE` - Storage type (s3, gcs, etc.)
- `STORAGE_ENDPOINT` - Storage endpoint URL
- `STORAGE_BUCKET` - Storage bucket name
- `STORAGE_REGION` - Storage region
- `STORAGE_ACCESS_KEY_ID` - Storage access key
- `STORAGE_SECRET_ACCESS_KEY` - Storage secret key

### Backup Settings

- `BACKUP_PATH` - Path for backup file in storage
- `RETENTION_DAYS` - Backup retention in days
- `CALLBACK_URL` - Webhook URL for status updates
- `CALLBACK_SECRET` - Webhook authentication secret

## 📊 Features

### ✅ Lightweight Containers

- **Alpine Linux** base for minimal size and attack surface
- **Single-purpose** containers for specific database types
- **Fast startup** times with minimal dependencies

### ✅ Version Compatibility

- **Multiple PostgreSQL versions** (12-17) for exact client/server matching
- **Latest versions** for other databases with automatic updates
- **Backward compatibility** maintained across versions

### ✅ Secure Backup Process

- **Compressed backups** using native database tools
- **Encrypted storage** with S3-compatible providers
- **Webhook callbacks** for real-time status updates
- **Proper cleanup** of temporary files

### ✅ Production Ready

- **Error handling** with detailed logging
- **Retry logic** for transient failures
- **Resource limits** to prevent runaway processes
- **Health checks** and monitoring

## 🔄 Integration

These containers integrate with the Plan B backup platform:

1. **Database Detection** - Plan B website detects database type and version
2. **Container Selection** - Appropriate container is selected automatically
3. **Cloud Run Job** - Container runs as serverless Cloud Run job
4. **Backup Execution** - Database-specific tools create optimized backups
5. **Storage Upload** - Compressed backups uploaded to configured storage
6. **Status Updates** - Real-time progress via webhooks

## 🛡️ Security

- **No hardcoded credentials** - all secrets passed via environment variables
- **Minimal attack surface** - only essential tools installed
- **Non-root execution** where possible
- **Secrets cleanup** after job completion

## 📈 Performance

- **Parallel builds** supported for faster CI/CD
- **Compressed backups** reduce storage and transfer costs
- **Optimized tools** use native database dump utilities
- **Resource limits** prevent resource exhaustion

## 🎯 Usage Examples

### PostgreSQL 16 Backup

```bash
docker run --rm \
  -e JOB_ID="backup-123" \
  -e DB_ENGINE="postgresql" \
  -e DB_HOST="pg.example.com" \
  -e DB_PORT="5432" \
  -e DB_NAME="myapp" \
  -e DB_USERNAME="postgres" \
  -e DB_PASSWORD="secret" \
  -e STORAGE_TYPE="s3" \
  -e STORAGE_ENDPOINT="https://s3.amazonaws.com" \
  -e STORAGE_BUCKET="backups" \
  -e STORAGE_REGION="us-east-1" \
  -e STORAGE_ACCESS_KEY_ID="AKIAI..." \
  -e STORAGE_SECRET_ACCESS_KEY="secret" \
  -e BACKUP_PATH="backups/myapp/backup.sql.gz" \
  -e RETENTION_DAYS="30" \
  -e CALLBACK_URL="https://api.planb.example.com/webhooks/backup" \
  -e CALLBACK_SECRET="webhook-secret" \
  gcr.io/apito-cms/plan-b-backup-postgresql:16
```

### MongoDB Backup

```bash
docker run --rm \
  -e JOB_ID="mongo-backup-456" \
  -e DB_ENGINE="mongodb" \
  -e DB_HOST="mongo.example.com" \
  -e DB_PORT="27017" \
  -e DB_NAME="myapp" \
  -e DB_USERNAME="admin" \
  -e DB_PASSWORD="secret" \
  # ... storage and callback config ...
  gcr.io/apito-cms/plan-b-backup-mongodb:latest
```

---

**Built with ❤️ for reliable database backups**
