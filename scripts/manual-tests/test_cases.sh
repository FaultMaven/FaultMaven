#!/bin/bash

echo "🧪 Testing Case Module"
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

# Step 1: Login to get access token
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

# Step 2: Create a case
echo ""
echo "📝 Step 2: Create a case"
CREATE_RESPONSE=$(curl -s -X POST http://localhost:8000/cases \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Redis connection timeout issue",
    "description": "Intermittent timeouts on Redis cluster during peak hours",
    "priority": "high",
    "tags": ["redis", "performance"],
    "category": "infrastructure"
  }')

echo "$CREATE_RESPONSE"

CASE_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

if [ -n "$CASE_ID" ]; then
  echo "✅ Created case: $CASE_ID"
else
  echo "⚠️  Could not extract case ID"
fi

# Step 3: List all cases
echo ""
echo "📋 Step 3: List all cases"
curl -s -X GET http://localhost:8000/cases \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo ""

# Step 4: Get specific case (if we have case_id)
if [ -n "$CASE_ID" ]; then
  echo ""
  echo "🔍 Step 4: Get case details"
  curl -s -X GET http://localhost:8000/cases/$CASE_ID \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  echo ""

  # Step 5: Add hypothesis
  echo ""
  echo "💡 Step 5: Add hypothesis"
  curl -s -X POST http://localhost:8000/cases/$CASE_ID/hypotheses \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "title": "Connection pool exhaustion",
      "description": "High load causing connection pool to be exhausted",
      "confidence": 0.7
    }'
  echo ""

  # Step 6: Add solution
  echo ""
  echo "✨ Step 6: Add solution"
  curl -s -X POST http://localhost:8000/cases/$CASE_ID/solutions \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "title": "Increase connection pool size",
      "description": "Increase pool size from 10 to 50 connections",
      "implementation_steps": [
        "Update redis.conf with maxclients=50",
        "Restart Redis cluster",
        "Monitor connection usage"
      ]
    }'
  echo ""

  # Step 7: Add message
  echo ""
  echo "💬 Step 7: Add message to case"
  curl -s -X POST http://localhost:8000/cases/$CASE_ID/messages \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "role": "user",
      "content": "What are the common causes of Redis connection timeouts?"
    }'
  echo ""

  # Step 8: List messages
  echo ""
  echo "📜 Step 8: List case messages"
  curl -s -X GET http://localhost:8000/cases/$CASE_ID/messages \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  echo ""

  # Step 9: Update case status
  echo ""
  echo "🔄 Step 9: Update case status to VERIFYING"
  curl -s -X PATCH http://localhost:8000/cases/$CASE_ID \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "status": "verifying"
    }'
  echo ""

  # Step 10: Delete case
  echo ""
  echo "🗑️  Step 10: Delete case"
  curl -s -X DELETE http://localhost:8000/cases/$CASE_ID \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  echo ""
fi

# Cleanup
echo ""
echo "🛑 Stopping server..."
kill $SERVER_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "✅ Case module tests complete!"
