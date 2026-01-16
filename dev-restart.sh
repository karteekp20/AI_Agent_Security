#!/bin/bash
# dev-restart.sh - Clean restart for development
# Usage: ./dev-restart.sh

set -e

echo "========================================"
echo "Sentinel Dev Restart"
echo "========================================"
echo ""

echo "🧹 Clearing Python bytecode cache..."
find ./sentinel -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find ./sentinel -name "*.pyc" -delete 2>/dev/null || true
find ./examples -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find ./examples -name "*.pyc" -delete 2>/dev/null || true
find ./migrations -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find ./migrations -name "*.pyc" -delete 2>/dev/null || true
echo "✓ Cache cleared"
echo ""

echo "🔄 Restarting containers..."
docker-compose restart sentinel-api
echo "✓ Containers restarted"
echo ""

echo "📋 Watching logs (Press Ctrl+C to exit)..."
echo "========================================"
docker-compose logs -f sentinel-api
