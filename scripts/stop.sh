#!/bin/bash

# FaultMaven server stop script
# Gracefully stops running FaultMaven server instances

set -e

echo "🛑 Stopping FaultMaven server..."
echo "================================"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
PID_FILE="${PID_FILE:-/tmp/faultmaven-server.pid}"
LOG_FILE="${LOG_FILE:-/tmp/faultmaven-server.log}"

# Check for PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "📋 Found PID file: $PID"

    # Check if process is running
    if ps -p "$PID" > /dev/null 2>&1; then
        # Verify it's actually uvicorn
        if ps -p "$PID" -o cmd= | grep -q "uvicorn.*faultmaven.app:app"; then
            echo "🔄 Stopping FaultMaven (PID: $PID)..."

            # Try graceful shutdown first (SIGTERM)
            kill -TERM "$PID" 2>/dev/null || true

            # Wait for graceful shutdown (max 10 seconds)
            WAIT_COUNT=0
            while ps -p "$PID" > /dev/null 2>&1 && [ $WAIT_COUNT -lt 10 ]; do
                sleep 1
                WAIT_COUNT=$((WAIT_COUNT + 1))
                echo -n "."
            done
            echo ""

            # Force kill if still running
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "⚠️  Graceful shutdown failed, forcing..."
                kill -9 "$PID" 2>/dev/null || true
                sleep 1
            fi

            # Verify process stopped
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "❌ Failed to stop process $PID"
                exit 1
            else
                echo "✅ FaultMaven stopped successfully"
            fi
        else
            echo "⚠️  PID $PID exists but is not FaultMaven"
        fi
    else
        echo "ℹ️  Process $PID is not running"
    fi

    # Clean up PID file
    rm -f "$PID_FILE"
    echo "🧹 Cleaned up PID file"
else
    echo "ℹ️  No PID file found at $PID_FILE"
fi

# Kill any remaining uvicorn processes for faultmaven.app
echo ""
echo "🔍 Checking for any remaining FaultMaven processes..."
REMAINING_PIDS=$(pgrep -f "uvicorn.*faultmaven.app:app" 2>/dev/null || true)

if [ -n "$REMAINING_PIDS" ]; then
    echo "⚠️  Found remaining processes: $REMAINING_PIDS"
    echo "🔄 Stopping remaining processes..."

    for PID in $REMAINING_PIDS; do
        echo "  Stopping PID: $PID"
        kill -TERM "$PID" 2>/dev/null || true
    done

    # Wait for processes to stop
    sleep 2

    # Force kill if necessary
    STILL_RUNNING=$(pgrep -f "uvicorn.*faultmaven.app:app" 2>/dev/null || true)
    if [ -n "$STILL_RUNNING" ]; then
        echo "⚠️  Force killing remaining processes..."
        pkill -9 -f "uvicorn.*faultmaven.app:app" 2>/dev/null || true
        sleep 1
    fi

    # Verify all stopped
    FINAL_CHECK=$(pgrep -f "uvicorn.*faultmaven.app:app" 2>/dev/null || true)
    if [ -n "$FINAL_CHECK" ]; then
        echo "❌ Some processes could not be stopped: $FINAL_CHECK"
        exit 1
    else
        echo "✅ All remaining processes stopped"
    fi
else
    echo "✅ No remaining FaultMaven processes found"
fi

# Check port status
DEFAULT_PORT="${PORT:-8000}"
echo ""
echo "🔍 Checking port $DEFAULT_PORT status..."

if command -v lsof >/dev/null 2>&1; then
    if lsof -i:"$DEFAULT_PORT" >/dev/null 2>&1; then
        echo "⚠️  Port $DEFAULT_PORT is still in use:"
        lsof -i:"$DEFAULT_PORT"
    else
        echo "✅ Port $DEFAULT_PORT is now free"
    fi
elif command -v netstat >/dev/null 2>&1; then
    if netstat -ln 2>/dev/null | grep -q ":${DEFAULT_PORT} "; then
        echo "⚠️  Port $DEFAULT_PORT may still be in use"
    else
        echo "✅ Port $DEFAULT_PORT appears free"
    fi
else
    echo "ℹ️  Unable to check port status (lsof/netstat not available)"
fi

echo ""
echo "✅ FaultMaven shutdown complete"
echo "📄 Last logs available at: $LOG_FILE"
