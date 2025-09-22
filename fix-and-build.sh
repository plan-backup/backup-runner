#!/bin/bash

echo "🔧 Fixing and building Plan B Backup Runner container..."

# The Dockerfile has been fixed - unzip was added to system dependencies
echo "✅ Dockerfile fixed: added 'unzip' to system dependencies"

# Build the container with the fix
echo "🏗️ Building Docker container..."
docker build -t plan-backup/backup-runner .

# Tag for GitHub Container Registry
echo "🏷️ Tagging for GitHub Container Registry..."
docker tag plan-backup/backup-runner ghcr.io/plan-backup/backup-runner:latest

echo "📦 Container build complete!"
echo ""
echo "🚀 To push to GitHub Container Registry, run:"
echo "   docker login ghcr.io"
echo "   docker push ghcr.io/plan-backup/backup-runner:latest"
echo ""
echo "🧪 To test the container locally, run:"
echo "   docker run --rm -e JOB_ID=test-123 -e DB_ENGINE=postgresql [...other env vars...] plan-backup/backup-runner"
