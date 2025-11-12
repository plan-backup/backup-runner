# Plan B Database Backup Runner - MySQL Latest
# Client tools only - no database server

FROM mysql:latest

# Set Plan B metadata
ENV DB_TYPE=mysql
ENV DB_VERSION=latest
ENV CONTAINER_VERSION=mysql-latest

# Install Python and required packages for compression and S3 upload
RUN microdnf update -y && microdnf install -y \
    python3 \
    python3-pip \
    && microdnf clean all

# Install Python dependencies
RUN pip3 install boto3 requests

# Copy shared base class
COPY shared/backup_base.py /usr/local/bin/backup_base.py

# Copy database-specific runner script
COPY mysql/latest/runner.py /usr/local/bin/runner.py
RUN chmod +x /usr/local/bin/runner.py

# Copy shared entrypoint
COPY shared/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1
ENV OPERATION_TYPE=backup

# Override the MySQL entrypoint to allow running client tools directly
# The original entrypoint starts the database server, we want client tools only
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Verify mysqldump and mysql are available
RUN mysqldump --version && mysql --version

LABEL maintainer="Plan B Backup"
LABEL database="mysql"
LABEL version="latest"
LABEL source="mysql:latest"