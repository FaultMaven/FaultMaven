#!/bin/bash

echo "🧪 Testing Auth Module"
echo "=" * 60

# Start server in background
source .venv/bin/activate
uvicorn faultmaven.app:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 3

echo ""
echo "✅ Server started (PID: $SERVER_PID)"

# Test 1: Register a new user
echo ""
echo "📝 Test 1: Register new user"
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123",
    "full_name": "Test User"
  }'
echo ""

# Test 2: Login with the registered user
echo ""
echo "🔐 Test 2: Login"
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }')
echo "$LOGIN_RESPONSE"

# Extract access token
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -n "$ACCESS_TOKEN" ]; then
  echo ""
  echo "✅ Got access token: ${ACCESS_TOKEN:0:50}..."

  # Test 3: Get current user info
  echo ""
  echo "👤 Test 3: Get current user info"
  curl -s -X GET http://localhost:8000/auth/me \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  echo ""

  # Test 4: Logout
  echo ""
  echo "🚪 Test 4: Logout"
  curl -s -X POST http://localhost:8000/auth/logout \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  echo ""
else
  echo "❌ Failed to get access token"
fi

# Cleanup
echo ""
echo "🛑 Stopping server..."
kill $SERVER_PID 2>/dev/null || true

echo ""
echo "=" * 60
echo "✅ Auth module tests complete!"
