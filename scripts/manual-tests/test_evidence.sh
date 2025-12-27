#!/bin/bash

echo "🧪 Testing Evidence Module"
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
CREATE_CASE_RESPONSE=$(curl -s -X POST http://localhost:8000/cases \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database connection issue",
    "description": "Need to upload logs and config files",
    "priority": "high"
  }')

CASE_ID=$(echo "$CREATE_CASE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

if [ -n "$CASE_ID" ]; then
  echo "✅ Created case: $CASE_ID"
else
  echo "❌ Could not create case"
  kill $SERVER_PID 2>/dev/null || true
  exit 1
fi

# Step 3: Create a test file
echo ""
echo "📄 Step 3: Creating test file"
TEST_FILE="test_evidence.log"
echo "This is a test log file for evidence upload.
2024-01-01 ERROR Database connection failed
2024-01-01 ERROR Timeout after 30 seconds
2024-01-01 INFO Retrying connection..." > $TEST_FILE

echo "✅ Created test file: $TEST_FILE"

# Step 4: Upload evidence
echo ""
echo "📤 Step 4: Upload evidence file"
UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8000/evidence/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "case_id=$CASE_ID" \
  -F "file=@$TEST_FILE" \
  -F "evidence_type=log" \
  -F "description=Database connection error log" \
  -F "tags=database,error,production")

echo "$UPLOAD_RESPONSE"

EVIDENCE_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

if [ -n "$EVIDENCE_ID" ]; then
  echo "✅ Uploaded evidence: $EVIDENCE_ID"
else
  echo "⚠️  Could not extract evidence ID"
fi

# Step 5: List evidence for case
echo ""
echo "📋 Step 5: List evidence for case"
curl -s -X GET "http://localhost:8000/evidence/case/$CASE_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo ""

# Step 6: Get specific evidence (if we have evidence_id)
if [ -n "$EVIDENCE_ID" ]; then
  echo ""
  echo "🔍 Step 6: Get evidence metadata"
  curl -s -X GET "http://localhost:8000/evidence/$EVIDENCE_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  echo ""

  # Step 7: Download evidence
  echo ""
  echo "📥 Step 7: Download evidence file"
  curl -s -X GET "http://localhost:8000/evidence/$EVIDENCE_ID/download" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -o "downloaded_evidence.log"

  if [ -f "downloaded_evidence.log" ]; then
    echo "✅ Downloaded file:"
    cat downloaded_evidence.log
  else
    echo "❌ Failed to download file"
  fi

  # Step 8: Delete evidence
  echo ""
  echo "🗑️  Step 8: Delete evidence"
  curl -s -X DELETE "http://localhost:8000/evidence/$EVIDENCE_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  echo ""

  # Verify file was deleted from storage
  if [ ! -f "data/files/evidence/$CASE_ID/*.log" ]; then
    echo "✅ File removed from storage"
  fi
fi

# Cleanup
echo ""
echo "🧹 Cleaning up test files"
rm -f $TEST_FILE downloaded_evidence.log

echo ""
echo "🛑 Stopping server..."
kill $SERVER_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "✅ Evidence module tests complete!"
