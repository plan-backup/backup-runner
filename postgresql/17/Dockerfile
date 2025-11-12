# Plan B Database Backup Runner - PostgreSQL 17
# Client tools only - no database server

FROM postgres:17

# Set Plan B metadata
ENV DB_TYPE=postgresql
ENV DB_VERSION=17
ENV CONTAINER_VERSION=postgresql-17

# Install Python and required packages for compression and S3 upload
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install boto3 requests --break-system-packages

# Copy shared base class
COPY shared/backup_base.py /usr/local/bin/backup_base.py

# Copy database-specific runner script
COPY postgresql/17/runner.py /usr/local/bin/runner.py
RUN chmod +x /usr/local/bin/runner.py

# Copy shared entrypoint
COPY shared/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1
ENV OPERATION_TYPE=backup

# Override the PostgreSQL entrypoint to allow running client tools directly
# The original entrypoint starts the database server, we want client tools only
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Verify pg_dump and psql are available
RUN pg_dump --version && psql --version

LABEL maintainer="Plan B Backup"
LABEL database="postgresql"
LABEL version="17"
LABEL source="postgres:17"
