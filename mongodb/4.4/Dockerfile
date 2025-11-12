# Plan B Database Backup Runner - MongoDB 4.4
# Client tools only - no database server

FROM mongo:4.4

# Set Plan B metadata
ENV DB_TYPE=mongodb
ENV DB_VERSION=4.4
ENV CONTAINER_VERSION=mongodb-4.4

# Install Python and required packages for compression and S3 upload
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install boto3 requests

# Copy runner script
COPY mongodb/4.4/runner.py /usr/local/bin/runner.py
RUN chmod +x /usr/local/bin/runner.py

# Override the MongoDB entrypoint to allow running client tools directly
# The original entrypoint starts the database server, we want client tools only
ENTRYPOINT []
CMD []

# Verify mongodump and mongorestore are available
RUN mongodump --version && mongorestore --version

LABEL maintainer="Plan B Backup"
LABEL database="mongodb"
LABEL version="4.4"
LABEL source="mongo:4.4"