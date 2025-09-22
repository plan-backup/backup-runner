# Plan B Backup Runner 🚀

Docker container for automated database backups with S3-compatible storage upload. Part of the [Plan B Database Backup](https://planb.apito.io) platform.

## 🎯 **Supported Databases**

- **PostgreSQL** - Using `pg_dump` with custom format and compression
- **MySQL** - Using `mysqldump` with single transaction 
- **MongoDB** - Using `mongodump` with gzip compression

## 🔧 **Supported Storage**

- **Amazon S3**
- **Wasabi Cloud Storage** 
- **Cloudflare R2**
- **Google Cloud Storage**
- **Any S3-compatible storage**

## 📦 **Usage**

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `JOB_ID` | Unique job identifier | ✅ |
| `DB_ENGINE` | Database type (`postgresql`, `mysql`, `mongodb`) | ✅ |
| `DB_HOST` | Database hostname | ✅ |
| `DB_PORT` | Database port | ✅ |
| `DB_NAME` | Database name | ✅ |
| `DB_USERNAME` | Database username | ✅ |
| `DB_PASSWORD` | Database password | ✅ |
| `STORAGE_TYPE` | Storage type (`s3`, `wasabi`, `r2`, `gcs`) | ✅ |
| `STORAGE_ENDPOINT` | Storage endpoint URL | ✅ |
| `STORAGE_BUCKET` | Storage bucket name | ✅ |
| `STORAGE_REGION` | Storage region | ✅ |
| `STORAGE_ACCESS_KEY_ID` | Storage access key | ✅ |
| `STORAGE_SECRET_ACCESS_KEY` | Storage secret key | ✅ |
| `BACKUP_PATH` | S3 object key path | ✅ |
| `CALLBACK_URL` | Status callback URL | ✅ |
| `CALLBACK_SECRET` | Callback authentication secret | ✅ |
| `RETENTION_DAYS` | Backup retention period | ❌ (default: 30) |

### Docker Run Example

```bash
docker run --rm \
  -e JOB_ID="backup-job-123" \
  -e DB_ENGINE="postgresql" \
  -e DB_HOST="db.example.com" \
  -e DB_PORT="5432" \
  -e DB_NAME="myapp" \
  -e DB_USERNAME="backup_user" \
  -e DB_PASSWORD="secret_password" \
  -e STORAGE_TYPE="s3" \
  -e STORAGE_ENDPOINT="https://s3.amazonaws.com" \
  -e STORAGE_BUCKET="my-backups" \
  -e STORAGE_REGION="us-east-1" \
  -e STORAGE_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE" \
  -e STORAGE_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" \
  -e BACKUP_PATH="backups/myapp/2025/backup-job-123.sql.gz" \
  -e CALLBACK_URL="https://planb.apito.io/api/jobs/callback" \
  -e CALLBACK_SECRET="webhook_secret_token" \
  ghcr.io/plan-backup/backup-runner:latest
```

### Google Cloud Run Example

```yaml
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: backup-job-123
spec:
  spec:
    template:
      spec:
        template:
          spec:
            containers:
            - image: ghcr.io/plan-backup/backup-runner:latest
              env:
              - name: JOB_ID
                value: "backup-job-123"
              - name: DB_ENGINE
                value: "postgresql"
              # ... other environment variables
```

## 🏗️ **Build**

```bash
# Build the container
docker build -t plan-backup/backup-runner .

# Tag for GitHub Container Registry
docker tag plan-backup/backup-runner ghcr.io/plan-backup/backup-runner:latest

# Push to registry
docker push ghcr.io/plan-backup/backup-runner:latest
```

## 🔄 **Backup Process**

1. **Validate Environment** - Check all required variables
2. **Create Backup** - Use appropriate database tool
3. **Compress** - Gzip compression for size optimization
4. **Upload** - Stream to S3-compatible storage
5. **Report Status** - Callback to Plan B API
6. **Cleanup** - Remove temporary files

## 🛡️ **Security Features**

- **No persistent data** - All credentials via environment variables
- **Temporary file cleanup** - No backup data left on container
- **Secure callbacks** - HMAC-signed status reporting
- **Minimal attack surface** - Ubuntu-based with only required tools

## 📊 **Monitoring**

The container reports status back to the Plan B API:

- **`running`** - Backup process started
- **`success`** - Backup completed and uploaded
- **`failed`** - Error occurred during backup

Logs are output to stdout for Cloud Run logging integration.

## 🤝 **Contributing**

Part of the Plan B platform. See the main [Plan B repository](https://github.com/plan-backup) for contributing guidelines.

## 📄 **License**

MIT License - see LICENSE file for details.