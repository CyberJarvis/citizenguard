#!/bin/bash

# BlueRadar Social Intelligence - Run Script
# Starts the API server on port 8001 and opens the dashboard

echo "🌊 Starting BlueRadar Social Intelligence System..."
echo ""

# Kill any existing processes on port 8001
echo "📋 Checking for existing processes on port 8001..."
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
sleep 1

# Start the API server on port 8001
echo "🚀 Starting API server on http://localhost:8001..."
echo ""
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload &

# Wait for server to start
echo "⏳ Waiting for server to initialize..."
sleep 5

# Check if server started successfully
if lsof -i:8001 >/dev/null 2>&1; then
    echo "✅ Server started successfully on port 8001"
    echo ""
    echo "📊 Opening dashboard..."
    sleep 2

    # Open the dashboard in default browser
    open http://localhost:8001/dashboard 2>/dev/null || \
    xdg-open http://localhost:8001/dashboard 2>/dev/null || \
    echo "   Please open http://localhost:8001/dashboard in your browser"

    echo ""
    echo "================================================"
    echo "🎉 BlueRadar is running!"
    echo "================================================"
    echo ""
    echo "📍 API Documentation: http://localhost:8001/docs"
    echo "📍 Dashboard:         http://localhost:8001/dashboard"
    echo "📍 Enhanced Feed:     http://localhost:8001/feed/enhanced"
    echo ""
    echo "To stop the server: Press Ctrl+C or run 'killall -9 Python'"
    echo ""

    # Keep script running to show logs
    wait
else
    echo "❌ Failed to start server on port 8001"
    echo "Please check if the port is already in use or if there are errors above"
    exit 1
fi
