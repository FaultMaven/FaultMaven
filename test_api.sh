#!/bin/bash

# Start the FastAPI server in the background
source .venv/bin/activate
uvicorn faultmaven.api:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 3

# Test health endpoint
echo ""
echo "🔍 Testing health endpoint..."
curl -s http://localhost:8000/health | python -m json.tool

# Test agent ask endpoint
echo ""
echo "🔍 Testing agent ask endpoint (non-streaming)..."
curl -s -X POST http://localhost:8000/agent/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is 2+2?", "stream": false}' \
  | python -m json.tool

echo ""
echo "✅ API tests complete!"

# Cleanup
echo ""
echo "🛑 Stopping server..."
kill $SERVER_PID
