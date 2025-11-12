# Plan B Database Backup Runner - ArangoDB 3.10
# Client tools only - no database server

FROM arangodb/arangodb:3.10.12

# Set Plan B metadata
ENV DB_TYPE=arangodb
ENV DB_VERSION=3.10
ENV CONTAINER_VERSION=arangodb-3.10

# Install Python and required packages for compression and S3 upload
RUN apk add --no-cache \
    python3 \
    py3-pip

# Install Python dependencies
RUN pip3 install boto3

# Copy runner script
COPY arangodb/3.10/runner.py /usr/local/bin/runner.py
RUN chmod +x /usr/local/bin/runner.py

# Override the ArangoDB entrypoint to allow running client tools directly
# The original entrypoint starts the database server, we want client tools only
ENTRYPOINT []
CMD []

# Verify arangodump and arangorestore are available
RUN which arangodump && which arangorestore

LABEL maintainer="Plan B Backup"
LABEL database="arangodb"
LABEL version="3.10"
LABEL source="arangodb/arangodb:3.10.12"