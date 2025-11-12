# Plan B Database Backup Runner - MariaDB 10.11.14
# Client tools only - no database server

FROM mariadb:10.11.14

# Set Plan B metadata
ENV DB_TYPE=mariadb
ENV DB_VERSION=10.11.14
ENV CONTAINER_VERSION=mariadb-10.11.14

# Install Python and required packages for compression and S3 upload
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install boto3 requests --break-system-packages

# Copy runner script
COPY mariadb/10.11.14/runner.py /usr/local/bin/runner.py
RUN chmod +x /usr/local/bin/runner.py

# Override the MariaDB entrypoint to allow running client tools directly
# The original entrypoint starts the database server, we want client tools only
ENTRYPOINT []
CMD []

# Verify mariadb-dump and mariadb are available
RUN mariadb-dump --version && mariadb --version

LABEL maintainer="Plan B Backup"
LABEL database="mariadb"
LABEL version="10.11.14"
LABEL source="mariadb:10.11.14"
