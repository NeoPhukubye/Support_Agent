#!/bin/bash
echo "🚀 Starting SupportAI Backend..."
cd "$(dirname "$0")/backend"
source venv/bin/activate
python3 main.py
