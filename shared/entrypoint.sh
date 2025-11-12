#!/bin/bash
# Plan B Database Backup Runner - Shared Entrypoint
set -e

echo "Plan B Database Backup Runner Starting..."
echo "Job ID: ${JOB_ID:-not-set}"
echo "Database Engine: ${DB_ENGINE:-not-set}"
echo "Database Host: ${DB_HOST:-not-set}"
echo "Container Version: ${CONTAINER_VERSION:-unknown}"

    # Validate required environment variables
    required_vars=(
        "JOB_ID"
        "DB_ENGINE"
        "DB_HOST" 
        "DB_PORT"
        "DB_NAME"
        "DB_USERNAME"
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

    # DB_PASSWORD is optional for some databases (like Redis without auth)
    if [ -z "${DB_PASSWORD}" ]; then
        echo "WARNING: DB_PASSWORD is not set - some databases may not require authentication"
    fi

# Run the database-specific backup script
python3 /usr/local/bin/runner.py

echo "Backup job completed successfully"
