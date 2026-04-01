#!/bin/bash
# Neron Server - Safe Startup Script
# This script properly cleans up old processes and starts the app fresh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔄 Neron Server Startup"
echo "====================="

# Activate venv
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run: python3 -m venv venv"
    exit 1
fi

source venv/bin/activate
echo "✓ Virtual environment activated"

# Kill any existing processes gracefully
echo "🧹 Cleaning up old processes..."
pkill -f "python.*core/app.py" 2>/dev/null || true
pkill -f "python.*api_agent" 2>/dev/null || true
pkill -f "python.*telegram_agent" 2>/dev/null || true
sleep 2
echo "✓ Old processes cleaned"

# Wait for port to be released
echo "⏳ Waiting for port 8010 to become available..."
for i in {1..10}; do
    if ! timeout 1 bash -c "echo >/dev/tcp/localhost/8010" 2>/dev/null; then
        echo "✓ Port 8010 is available"
        break
    fi
    echo "  Attempt $i/10: Port still in use, waiting..."
    sleep 1
done

# Configure Python to not buffer output
export PYTHONUNBUFFERED=1

# Start the app
echo "🚀 Starting Neron Application..."
echo "═════════════════════════════════"
python3 core/app.py
