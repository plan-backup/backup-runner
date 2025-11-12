# Plan B Database Backup Runner - Oracle Database Latest
# Using official Oracle Instant Client

FROM alpine:3.20

# Set database version and type
ENV DB_TYPE=oracle
ENV DB_VERSION=19c
ENV CONTAINER_VERSION=oracle-19c

# Install base dependencies and Oracle prerequisites
RUN apk add --no-cache \
    bash \
    python3 \
    py3-requests \
    curl \
    gzip \
    aws-cli \
    libc6-compat \
    libnsl \
    unixodbc \
    && rm -rf /var/cache/apk/*

# Download and install Oracle Instant Client
RUN mkdir -p /opt/oracle && \
    cd /tmp && \
    curl -o instantclient-basic.zip https://download.oracle.com/otn_software/linux/instantclient/instantclient-basiclite-linuxx64.zip && \
    curl -o instantclient-tools.zip https://download.oracle.com/otn_software/linux/instantclient/instantclient-tools-linuxx64.zip && \
    unzip instantclient-basic.zip -d /opt/oracle/ && \
    unzip instantclient-tools.zip -d /opt/oracle/ && \
    rm -f instantclient-*.zip && \
    cd /opt/oracle/instantclient_* && \
    ln -sf /opt/oracle/instantclient_*/libclntsh.so.* /opt/oracle/instantclient_*/libclntsh.so

# Set Oracle environment variables
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_1:$LD_LIBRARY_PATH
ENV PATH=/opt/oracle/instantclient_21_1:$PATH
ENV ORACLE_HOME=/opt/oracle/instantclient_21_1

# Create app directory
WORKDIR /app

# Copy shared entrypoint
COPY shared/entrypoint.sh ./entrypoint.sh

# Copy database-specific runner script
COPY oracle/19c/runner.py ./runner.py

# Copy shared base class
COPY shared/backup_base.py ./backup_base.py

# Make scripts executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1

# Entry point
ENTRYPOINT ["./entrypoint.sh"]
