#!/bin/bash
# Script để kill các ports trước khi start services

echo "🔴 Killing processes on ports 8000 and 7860..."

# Kill port 8000 (Token Server)
if lsof -ti :8000 >/dev/null 2>&1; then
    echo "  Killing process on port 8000..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null
    echo "  ✅ Port 8000 freed"
else
    echo "  ✅ Port 8000 already free"
fi

# Kill port 7860 (Agent Server)
if lsof -ti :7860 >/dev/null 2>&1; then
    echo "  Killing process on port 7860..."
    lsof -ti :7860 | xargs kill -9 2>/dev/null
    echo "  ✅ Port 7860 freed"
else
    echo "  ✅ Port 7860 already free"
fi

echo ""
echo "✅ All ports cleared! You can now start the servers."

