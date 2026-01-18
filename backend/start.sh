#!/bin/sh
# CoastGuardian Startup Script
# Ensures the app starts and responds to health checks

set -e

PORT="${PORT:-8000}"
echo "=============================================="
echo "CoastGuardian Backend Starting"
echo "Port: $PORT"
echo "Python: $(python --version)"
echo "Working Dir: $(pwd)"
echo "=============================================="

# List files to verify deployment
echo "Files in /app:"
ls -la /app

echo "Files in /app/app:"
ls -la /app/app 2>/dev/null || echo "No /app/app directory"

echo "=============================================="
echo "Starting uvicorn..."
echo "=============================================="

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 120 --log-level info
