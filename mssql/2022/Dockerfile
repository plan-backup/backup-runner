# Plan B Database Backup Runner - SQL Server Latest
# Using official Microsoft SQL Server tools

FROM alpine:3.20

# Set database version and type
ENV DB_TYPE=mssql
ENV DB_VERSION=2022
ENV CONTAINER_VERSION=mssql-2022

# Install base dependencies
RUN apk add --no-cache \
    bash \
    python3 \
    py3-requests \
    curl \
    gzip \
    aws-cli \
    unixodbc-dev \
    && rm -rf /var/cache/apk/*

# Install Microsoft SQL Server tools
RUN curl -O https://packages.microsoft.com/keys/microsoft.asc && \
    gpg --import microsoft.asc && \
    curl https://packages.microsoft.com/config/alpine/3.20/prod.repo > /etc/apk/repositories.d/mssql.repo && \
    apk update && \
    ACCEPT_EULA=Y apk add --no-cache mssql-tools18 msodbcsql18 && \
    rm -rf /var/cache/apk/* && \
    rm microsoft.asc

# Add SQL Server tools to PATH
ENV PATH="$PATH:/opt/mssql-tools18/bin"

# Create app directory
WORKDIR /app

# Copy shared entrypoint
COPY shared/entrypoint.sh ./entrypoint.sh

# Copy database-specific runner script
COPY mssql/2022/runner.py ./runner.py

# Copy shared base class
COPY shared/backup_base.py ./backup_base.py

# Make scripts executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1

# Entry point
ENTRYPOINT ["./entrypoint.sh"]
