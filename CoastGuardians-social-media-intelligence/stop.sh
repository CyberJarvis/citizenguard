#!/bin/bash

# BlueRadar Social Intelligence - Stop Script
# Stops all running BlueRadar processes

echo "🛑 Stopping CoastGuardian Social Intelligence System..."
echo ""

# Kill processes on port 8001
echo "📋 Stopping API server on port 8001..."
lsof -ti:8001 | xargs kill -9 2>/dev/null && echo "✅ Server stopped" || echo "ℹ️  No server running on port 8001"

# Also kill any Python uvicorn processes
killall -9 Python 2>/dev/null && echo "✅ All Python processes terminated" || echo "ℹ️  No Python processes found"

echo ""
echo "✅ CoastGuardian(Social-media) stopped successfully"
