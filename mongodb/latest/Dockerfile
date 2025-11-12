# Plan B Database Backup Runner - MongoDB Latest
# Client tools only - no database server

FROM mongo:latest

# Set Plan B metadata
ENV DB_TYPE=mongodb
ENV DB_VERSION=latest
ENV CONTAINER_VERSION=mongodb-latest

# Install Python and required packages for compression and S3 upload
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install boto3 requests --break-system-packages

# Copy runner script
COPY mongodb/latest/runner.py /usr/local/bin/runner.py
RUN chmod +x /usr/local/bin/runner.py

# Override the MongoDB entrypoint to allow running client tools directly
# The original entrypoint starts the database server, we want client tools only
ENTRYPOINT []
CMD []

# Verify mongodump and mongorestore are available
RUN mongodump --version && mongorestore --version

LABEL maintainer="Plan B Backup"
LABEL database="mongodb"
LABEL version="latest"
LABEL source="mongo:latest"