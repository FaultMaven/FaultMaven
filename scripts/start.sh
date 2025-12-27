#!/bin/bash

# Enhanced FaultMaven server start script with process management
# This script starts the FaultMaven modular monolith using uvicorn
# All configuration is loaded from .env file automatically
#
# Features:
# - Detects if FaultMaven is already running
# - Offers to restart running instances
# - Prevents port conflicts
# - Supports both foreground and background execution
# - Health check monitoring

set -e

echo "🚀 Starting FaultMaven Modular Monolith..."
echo "=========================================="

# Script directory (relative to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Configuration
DEFAULT_HOST="${HOST:-0.0.0.0}"
DEFAULT_PORT="${PORT:-8000}"
LOG_FILE="${LOG_FILE:-/tmp/faultmaven-server.log}"
PID_FILE="${PID_FILE:-/tmp/faultmaven-server.pid}"

# Determine if running in Docker
if [ -f /.dockerenv ]; then
    IN_DOCKER=true
else
    IN_DOCKER=false
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Using defaults from .env.example"
    if [ -f ".env.example" ]; then
        echo "💡 Tip: Copy .env.example to .env and configure your settings"
    else
        echo "❌ .env.example not found. Please create environment configuration"
        exit 1
    fi
fi

# Check if FaultMaven is already running
check_running_instance() {
    # Check by PID file
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            # Verify it's actually uvicorn
            if ps -p "$PID" -o cmd= | grep -q "uvicorn.*faultmaven.app:app"; then
                return 0  # Running
            fi
        fi
        # PID file exists but process is dead, clean it up
        rm -f "$PID_FILE"
    fi

    # Check by process name
    if pgrep -f "uvicorn.*faultmaven.app:app" > /dev/null 2>&1; then
        return 0  # Running
    fi

    return 1  # Not running
}

# Check port availability
check_port_available() {
    local port=$1
    if command -v netstat >/dev/null 2>&1; then
        if netstat -ln 2>/dev/null | grep -q ":${port} "; then
            return 1  # Port in use
        fi
    elif command -v ss >/dev/null 2>&1; then
        if ss -ln 2>/dev/null | grep -q ":${port} "; then
            return 1  # Port in use
        fi
    elif command -v lsof >/dev/null 2>&1; then
        if lsof -i:"${port}" >/dev/null 2>&1; then
            return 1  # Port in use
        fi
    fi
    return 0  # Port available
}

# Handle existing instance
if check_running_instance; then
    EXISTING_PID=$(pgrep -f "uvicorn.*faultmaven.app:app" | head -n 1)
    echo "⚠️  FaultMaven is already running (PID: $EXISTING_PID)"

    # Check if running interactively
    if [ -t 0 ]; then
        echo "🔄 Do you want to restart it? [y/N]: "
        read -r response
        case $response in
            [yY][eE][sS]|[yY])
                echo "🛑 Stopping existing FaultMaven instance..."
                "$SCRIPT_DIR/stop.sh"
                sleep 2
                ;;
            *)
                echo "ℹ️  Keeping existing instance running"
                echo "📄 Logs: tail -f $LOG_FILE"
                echo "🛑 To stop: $SCRIPT_DIR/stop.sh"
                exit 0
                ;;
        esac
    else
        # Non-interactive mode: automatically restart
        echo "🔄 Non-interactive mode: automatically restarting..."
        "$SCRIPT_DIR/stop.sh"
        sleep 2
    fi
fi

# Double-check port availability
if ! check_port_available "$DEFAULT_PORT"; then
    echo "⚠️  Port $DEFAULT_PORT is still in use. Waiting for it to be released..."
    sleep 2
    if ! check_port_available "$DEFAULT_PORT"; then
        echo "❌ Port $DEFAULT_PORT is still occupied. Please check manually:"
        if command -v lsof >/dev/null 2>&1; then
            lsof -i:"$DEFAULT_PORT" || true
        fi
        exit 1
    fi
fi

# Check if running in Docker (no venv needed)
if [ "$IN_DOCKER" = false ]; then
    # Check for virtual environment or uv
    if [ -d ".venv" ]; then
        echo "🐍 Activating virtual environment..."
        source .venv/bin/activate
    elif command -v uv >/dev/null 2>&1; then
        echo "🐍 Using uv for package management..."
        # uv handles virtual environments automatically
    else
        echo "⚠️  No virtual environment found and uv not installed"
        echo "💡 Install dependencies with: pip install -e ."
    fi
fi

# Display configuration
echo "📁 Configuration:"
echo "   Project root: $PROJECT_ROOT"
echo "   Host: $DEFAULT_HOST"
echo "   Port: $DEFAULT_PORT"
echo "   Log file: $LOG_FILE"
echo "   Environment: $([ -f .env ] && echo '.env loaded' || echo 'using defaults')"

# Determine execution mode
BACKGROUND=false
if [ "$1" = "--background" ] || [ "$1" = "-d" ]; then
    BACKGROUND=true
fi

# Start FaultMaven
echo ""
echo "🏃 Starting FaultMaven server..."
echo "🌐 Server will be available at http://localhost:$DEFAULT_PORT"
echo "📚 API documentation at http://localhost:$DEFAULT_PORT/docs"
echo ""

if [ "$BACKGROUND" = true ]; then
    # Background mode
    echo "🔧 Starting in background mode..."
    nohup uvicorn faultmaven.app:app \
        --host "$DEFAULT_HOST" \
        --port "$DEFAULT_PORT" \
        --reload \
        > "$LOG_FILE" 2>&1 &

    SERVER_PID=$!
    echo "$SERVER_PID" > "$PID_FILE"

    # Wait a moment for the server to start
    sleep 2

    # Check if server is still running
    if ps -p "$SERVER_PID" > /dev/null 2>&1; then
        echo "✅ FaultMaven started successfully (PID: $SERVER_PID)"
        echo "📄 Logs: tail -f $LOG_FILE"
        echo "🔍 Monitor logs: $SCRIPT_DIR/logs.sh"
        echo "🛑 To stop: $SCRIPT_DIR/stop.sh"

        # Wait for health check
        echo ""
        echo "⏳ Waiting for server to be ready..."
        MAX_ATTEMPTS=30
        ATTEMPT=0
        while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
            if curl -sf http://localhost:$DEFAULT_PORT/health > /dev/null 2>&1; then
                echo "✅ Server is healthy and ready!"
                break
            fi
            ATTEMPT=$((ATTEMPT + 1))
            sleep 1
        done

        if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
            echo "⚠️  Server started but health check timed out"
            echo "📄 Check logs: tail -f $LOG_FILE"
        fi
    else
        echo "❌ Server failed to start. Check logs:"
        tail -n 20 "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
else
    # Foreground mode
    echo "🔧 Starting in foreground mode (Ctrl+C to stop)..."
    echo ""

    # Trap to clean up PID file on exit
    trap "rm -f $PID_FILE" EXIT

    # Start and save PID
    uvicorn faultmaven.app:app \
        --host "$DEFAULT_HOST" \
        --port "$DEFAULT_PORT" \
        --reload &

    SERVER_PID=$!
    echo "$SERVER_PID" > "$PID_FILE"

    # Wait for the server process
    wait "$SERVER_PID"
fi
