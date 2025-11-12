# Plan B Database Backup Runner - Couchbase Latest
# Using official Couchbase tools

FROM alpine:3.20

# Set database version and type
ENV DB_TYPE=couchbase
ENV DB_VERSION=7.2
ENV CONTAINER_VERSION=couchbase-7.2

# Install base dependencies and prerequisites for Couchbase tools
RUN apk add --no-cache \
    bash \
    python3 \
    py3-requests \
    curl \
    gzip \
    aws-cli \
    wget \
    openssl \
    ca-certificates \
    libc6-compat \
    && rm -rf /var/cache/apk/*

# Download and install Couchbase tools
ENV COUCHBASE_VERSION=7.2.4
RUN cd /tmp && \
    wget "https://packages.couchbase.com/releases/${COUCHBASE_VERSION}/couchbase-server-community_${COUCHBASE_VERSION}-linux_x86_64.tar.gz" && \
    tar -xzf "couchbase-server-community_${COUCHBASE_VERSION}-linux_x86_64.tar.gz" && \
    cp couchbase-server-community_${COUCHBASE_VERSION}/bin/cbbackup /usr/local/bin/ && \
    cp couchbase-server-community_${COUCHBASE_VERSION}/bin/cbrestore /usr/local/bin/ && \
    cp couchbase-server-community_${COUCHBASE_VERSION}/bin/cbtransfer /usr/local/bin/ && \
    chmod +x /usr/local/bin/cb* && \
    rm -rf /tmp/*

# Add Couchbase tools to PATH
ENV PATH="/usr/local/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy shared entrypoint
COPY shared/entrypoint.sh ./entrypoint.sh

# Copy database-specific runner script
COPY couchbase/7.2/runner.py ./runner.py

# Copy shared base class
COPY shared/backup_base.py ./backup_base.py

# Make scripts executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1

# Entry point
ENTRYPOINT ["./entrypoint.sh"]
