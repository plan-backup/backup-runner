# Plan B Database Backup Runner - Redis 7.2
# Client tools only - no database server

FROM redis:7.2

# Set Plan B metadata
ENV DB_TYPE=redis
ENV DB_VERSION=7.2
ENV CONTAINER_VERSION=redis-7.2

# Install Python and required packages for compression and S3 upload
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-boto3 \
    python3-requests \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared base class
COPY shared/backup_base.py /usr/local/bin/backup_base.py

# Copy database-specific runner script
COPY redis/7.2/runner.py /usr/local/bin/runner.py
RUN chmod +x /usr/local/bin/runner.py

# Copy shared entrypoint
COPY shared/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1

# Override the Redis entrypoint to allow running client tools directly
# The original entrypoint starts the database server, we want client tools only
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Verify redis-cli is available
RUN redis-cli --version

LABEL maintainer="Plan B Backup"
LABEL database="redis"
LABEL version="7.2"
LABEL source="redis:7.2"
