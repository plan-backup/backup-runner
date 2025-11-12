# Plan B Database Backup Runner - Apache Cassandra Latest
# Using official Cassandra tools (cqlsh and nodetool)

FROM alpine:3.20

# Set database version and type
ENV DB_TYPE=cassandra
ENV DB_VERSION=4.0
ENV CONTAINER_VERSION=cassandra-4.0

# Install base dependencies including Java (required for Cassandra tools)
RUN apk add --no-cache \
    bash \
    python3 \
    py3-requests \
    py3-pip \
    curl \
    gzip \
    aws-cli \
    openjdk11-jre \
    && rm -rf /var/cache/apk/*

# Download and install Apache Cassandra tools
ENV CASSANDRA_VERSION=4.0.11
RUN cd /opt && \
    curl -L "https://archive.apache.org/dist/cassandra/${CASSANDRA_VERSION}/apache-cassandra-${CASSANDRA_VERSION}-bin.tar.gz" | tar xzf - && \
    ln -s apache-cassandra-${CASSANDRA_VERSION} cassandra && \
    chmod +x /opt/cassandra/bin/*

# Add Cassandra tools to PATH
ENV PATH="/opt/cassandra/bin:$PATH"
ENV CASSANDRA_HOME="/opt/cassandra"

# Create app directory
WORKDIR /app

# Copy shared entrypoint
COPY shared/entrypoint.sh ./entrypoint.sh

# Copy database-specific runner script
COPY cassandra/4.0/runner.py ./runner.py

# Copy shared base class
COPY shared/backup_base.py ./backup_base.py

# Make scripts executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1

# Entry point
ENTRYPOINT ["./entrypoint.sh"]
