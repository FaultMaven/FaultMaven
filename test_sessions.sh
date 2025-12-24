#!/bin/bash

echo "🧪 Testing Session Module"
echo "=========================================="

# Start server in background
source .venv/bin/activate
uvicorn faultmaven.app:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 3

echo ""
echo "✅ Server started (PID: $SERVER_PID)"

# Step 1: Register and login to get access token
echo ""
echo "🔑 Step 1: Login to get access token"
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Failed to get access token"
  kill $SERVER_PID 2>/dev/null || true
  exit 1
fi

echo "✅ Got access token"

# Step 2: Create a session
echo ""
echo "📝 Step 2: Create a session"
CREATE_RESPONSE=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 192.168.1.100" \
  -H "User-Agent: Test-Client/1.0" \
  -d '{
    "session_data": {
      "client_type": "web",
      "browser": "chrome"
    }
  }')

echo "$CREATE_RESPONSE"

SESSION_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null || echo "")

if [ -n "$SESSION_ID" ]; then
  echo "✅ Created session: $SESSION_ID"
else
  echo "⚠️  Could not extract session ID"
fi

# Step 3: List all sessions
echo ""
echo "📋 Step 3: List all sessions"
curl -s -X GET http://localhost:8000/sessions \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo ""

# Step 4: Get specific session (if we have session_id)
if [ -n "$SESSION_ID" ]; then
  echo ""
  echo "🔍 Step 4: Get session details"
  curl -s -X GET http://localhost:8000/sessions/$SESSION_ID \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  echo ""

  # Step 5: Update session
  echo ""
  echo "✏️  Step 5: Update session"
  curl -s -X PATCH http://localhost:8000/sessions/$SESSION_ID \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "updates": {
        "page": "/dashboard",
        "last_action": "view_cases"
      }
    }'
  echo ""

  # Step 6: Delete session
  echo ""
  echo "🗑️  Step 6: Delete session"
  curl -s -X DELETE http://localhost:8000/sessions/$SESSION_ID \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  echo ""
fi

# Cleanup
echo ""
echo "🛑 Stopping server..."
kill $SERVER_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "✅ Session module tests complete!"
