#!/bin/bash

# Build script for CrawlerX

echo "Building CrawlerX Docker image..."

# Build the Docker image
docker build -t crawlerx:latest .

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    echo "To run the application:"
    echo "  Development: docker-compose up -d"
    echo "  Production:  docker-compose -f docker-compose.prod.yml up -d"
else
    echo "❌ Build failed!"
    exit 1
fi