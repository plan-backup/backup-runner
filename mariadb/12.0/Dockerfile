# Plan B Database Backup Runner - MariaDB 12.0
# Client tools only - no database server

FROM mariadb:12.0

# Set Plan B metadata
ENV DB_TYPE=mariadb
ENV DB_VERSION=12.0
ENV CONTAINER_VERSION=mariadb-12.0

# Install Python and required packages for compression and S3 upload
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install boto3 requests

# Copy runner script
COPY runner.py /usr/local/bin/runner.py
RUN chmod +x /usr/local/bin/runner.py

# Override the MariaDB entrypoint to allow running client tools directly
# The original entrypoint starts the database server, we want client tools only
ENTRYPOINT []
CMD []

# Verify mariadb-dump and mariadb are available
RUN mariadb-dump --version && mariadb --version

LABEL maintainer="Plan B Backup"
LABEL database="mariadb"
LABEL version="12.0"
LABEL source="mariadb:12.0"
