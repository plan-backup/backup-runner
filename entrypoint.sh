#!/bin/bash

# Plan B Backup Runner Entrypoint
set -e

echo "Plan B Database Backup Runner Starting..."
echo "Job ID: ${JOB_ID:-not-set}"
echo "Database Engine: ${DB_ENGINE:-not-set}"
echo "Database Host: ${DB_HOST:-not-set}"

# Validate required environment variables
required_vars=(
    "JOB_ID"
    "DB_ENGINE"
    "DB_HOST"
    "DB_PORT"
    "DB_NAME"
    "DB_USERNAME"
    "DB_PASSWORD"
    "STORAGE_TYPE"
    "STORAGE_ENDPOINT"
    "STORAGE_BUCKET"
    "STORAGE_REGION"
    "STORAGE_ACCESS_KEY_ID"
    "STORAGE_SECRET_ACCESS_KEY"
    "BACKUP_PATH"
    "CALLBACK_URL"
    "CALLBACK_SECRET"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

# Run the backup
python3 backup.py

echo "Backup job completed successfully"