#!/bin/bash

# Plan B Backup Runner - Google Cloud Authentication Script
# This script handles authentication for Google Container Registry (GCR)

echo "🔐 Plan B Google Cloud Authentication"
echo "===================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "📋 Current gcloud configuration:"
gcloud config list

echo ""
echo "🔑 Authenticating with Google Cloud..."

# Authenticate with gcloud
echo "Step 1: Authenticating with gcloud..."
gcloud auth login --no-launch-browser

if [ $? -eq 0 ]; then
    echo "✅ gcloud authentication successful!"
else
    echo "❌ gcloud authentication failed!"
    exit 1
fi

# Configure Docker for GCR
echo ""
echo "Step 2: Configuring Docker for Google Container Registry..."
gcloud auth configure-docker

if [ $? -eq 0 ]; then
    echo "✅ Docker configured for GCR!"
else
    echo "❌ Docker configuration failed!"
    exit 1
fi

# Set application default credentials
echo ""
echo "Step 3: Setting up application default credentials..."
gcloud auth application-default login --no-launch-browser

if [ $? -eq 0 ]; then
    echo "✅ Application default credentials set!"
else
    echo "❌ Application default credentials setup failed!"
    exit 1
fi

echo ""
echo "🎉 Google Cloud authentication complete!"
echo ""
echo "📋 You can now:"
echo "   • Push Docker images to GCR"
echo "   • Run Cloud Run jobs"
echo "   • Access Google Cloud services"
echo ""
echo "🔍 To verify, try: gcloud auth list"
