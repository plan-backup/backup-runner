# Plan B Database Backup Runner
# Supports PostgreSQL, MySQL, MongoDB with S3-compatible storage upload

FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    lsb-release \
    ca-certificates \
    python3 \
    python3-pip \
    gzip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install PostgreSQL client
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y postgresql-client-15 \
    && rm -rf /var/lib/apt/lists/*

# Install MySQL client
RUN apt-get update && apt-get install -y mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Install MongoDB tools
RUN wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add - \
    && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-6.0.list \
    && apt-get update \
    && apt-get install -y mongodb-database-tools \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI for S3 operations (compatible with all S3-like services)
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf aws awscliv2.zip

# Install Python dependencies for API communication
RUN pip3 install requests

# Create app directory
WORKDIR /app

# Copy backup scripts
COPY backup.py .
COPY entrypoint.sh .

# Make scripts executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1

# Entry point
ENTRYPOINT ["./entrypoint.sh"]