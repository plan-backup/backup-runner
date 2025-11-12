# Plan B Database Backup Runner - MySQL 5.7
# Client tools only - no database server

FROM mysql:5.7

# Set Plan B metadata
ENV DB_TYPE=mysql
ENV DB_VERSION=5.7
ENV CONTAINER_VERSION=mysql-5.7

# Install Python and required packages for compression and S3 upload
RUN yum install -y \
    python3 \
    python3-pip \
    && yum clean all

# Install Python dependencies
RUN pip3 install boto3 requests

# Copy shared base class
COPY shared/backup_base.py /usr/local/bin/backup_base.py

# Copy database-specific runner script
COPY mysql/5.7/runner.py /usr/local/bin/runner.py
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
LABEL version="5.7"
LABEL source="mysql:5.7"