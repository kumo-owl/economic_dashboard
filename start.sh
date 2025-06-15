#!/bin/bash

echo "📊 Economic Dashboard Starting..."
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.9 or higher."
    exit 1
fi

# Check if streamlit is installed
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "🔧 Installing required packages..."
    pip install -r requirements.txt
fi

echo "🚀 Starting Economic Dashboard..."
echo "📱 Access URL: http://localhost:8501"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start the dashboard
python3 -m streamlit run dashboard.py

echo "👋 Dashboard stopped."