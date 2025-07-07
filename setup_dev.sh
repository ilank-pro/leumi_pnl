#!/bin/bash

echo "🔧 Setting up Bank Leumi P&L Dashboard Development Environment"
echo "============================================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment. Please check if venv module is available."
    exit 1
fi

echo "✅ Virtual environment created successfully"

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies. Please check the error above."
    exit 1
fi

echo "✅ Dependencies installed successfully"
echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "To start the server, run: ./start_server.sh"
echo "To activate the virtual environment manually, run: source venv/bin/activate"
echo "" 