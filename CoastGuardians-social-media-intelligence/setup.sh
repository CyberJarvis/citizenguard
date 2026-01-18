#!/bin/bash

echo "🌊 CoastGuardian Social Intelligence Module Setup"
echo "============================================="

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install core dependencies
echo "📥 Installing core dependencies..."
pip install fastapi uvicorn requests python-dotenv

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your MongoDB URI"
fi

# Check if Ollama is running
echo "🤖 Checking Ollama status..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Ollama is not running. Starting Ollama server..."
    ollama serve &
    sleep 3
fi

echo ""
echo "✅ Phase 1 Setup Complete!"
echo ""
echo "🚀 Next Steps:"
echo "1. Edit .env file with your MongoDB URI"
echo "2. Download a model: ollama pull llama3.2:1b"
echo "3. Test: python llm_client.py"
echo ""
echo "📋 Progress: Phase 1/8 completed ✅"