#!/bin/bash

# FaultMaven log monitoring script
# Real-time log viewer with filtering and formatting options

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
LOG_FILE="${LOG_FILE:-/tmp/faultmaven-server.log}"
LINES="${LINES:-50}"

# Print colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Show help
show_help() {
    echo "FaultMaven Log Monitoring Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --follow            Follow log file (live tail)"
    echo "  -n, --lines N           Show last N lines (default: 50)"
    echo "  -e, --errors            Show only ERROR and CRITICAL logs"
    echo "  -w, --warnings          Show only WARNING, ERROR, and CRITICAL logs"
    echo "  -g, --grep PATTERN      Filter logs by pattern"
    echo "  -l, --level LEVEL       Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    echo "  -c, --color             Force colored output (default: auto)"
    echo "  --clear                 Clear the log file"
    echo "  --path PATH             Use custom log file path"
    echo ""
    echo "Examples:"
    echo "  $0                      # Show last 50 lines"
    echo "  $0 -f                   # Follow logs in real-time"
    echo "  $0 -e                   # Show only errors"
    echo "  $0 -g 'LLM'            # Filter logs containing 'LLM'"
    echo "  $0 -n 100 -w           # Show last 100 warning+ logs"
    echo ""
    echo "Environment Variables:"
    echo "  LOG_FILE                Log file path (default: /tmp/faultmaven-server.log)"
    echo "  LINES                   Default number of lines to show"
}

# Parse arguments
FOLLOW=false
FILTER_PATTERN=""
FILTER_LEVEL=""
SHOW_ERRORS_ONLY=false
SHOW_WARNINGS_ONLY=false
FORCE_COLOR=false
CLEAR_LOG=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        -e|--errors)
            SHOW_ERRORS_ONLY=true
            shift
            ;;
        -w|--warnings)
            SHOW_WARNINGS_ONLY=true
            shift
            ;;
        -g|--grep)
            FILTER_PATTERN="$2"
            shift 2
            ;;
        -l|--level)
            FILTER_LEVEL="$2"
            shift 2
            ;;
        -c|--color)
            FORCE_COLOR=true
            shift
            ;;
        --clear)
            CLEAR_LOG=true
            shift
            ;;
        --path)
            LOG_FILE="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Clear log if requested
if [ "$CLEAR_LOG" = true ]; then
    if [ -f "$LOG_FILE" ]; then
        > "$LOG_FILE"
        print_info "Log file cleared: $LOG_FILE"
        exit 0
    else
        print_warning "Log file does not exist: $LOG_FILE"
        exit 0
    fi
fi

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    print_error "Log file not found: $LOG_FILE"
    print_info "Start FaultMaven server to generate logs"
    exit 1
fi

# Build grep pattern for filtering
GREP_ARGS=()
if [ "$SHOW_ERRORS_ONLY" = true ]; then
    GREP_ARGS+=(-E "ERROR|CRITICAL")
elif [ "$SHOW_WARNINGS_ONLY" = true ]; then
    GREP_ARGS+=(-E "WARNING|ERROR|CRITICAL")
elif [ -n "$FILTER_LEVEL" ]; then
    GREP_ARGS+=(-E "$FILTER_LEVEL")
fi

if [ -n "$FILTER_PATTERN" ]; then
    GREP_ARGS+=(-E "$FILTER_PATTERN")
fi

# Color highlighting function
highlight_logs() {
    if [ "$FORCE_COLOR" = true ] || [ -t 1 ]; then
        sed -E \
            -e "s/(ERROR|CRITICAL)/${RED}\1${NC}/g" \
            -e "s/(WARNING)/${YELLOW}\1${NC}/g" \
            -e "s/(INFO)/${GREEN}\1${NC}/g" \
            -e "s/(DEBUG)/${CYAN}\1${NC}/g" \
            -e "s/([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})/${BLUE}\1${NC}/g" \
            -e "s/(faultmaven\.[a-zA-Z0-9_.]+)/${MAGENTA}\1${NC}/g"
    else
        cat
    fi
}

# Display header
echo ""
print_info "FaultMaven Log Viewer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_info "Log file: $LOG_FILE"
print_info "File size: $(du -h "$LOG_FILE" 2>/dev/null | cut -f1)"

if [ "$FOLLOW" = true ]; then
    print_info "Mode: Following (Ctrl+C to stop)"
else
    print_info "Mode: Last $LINES lines"
fi

if [ ${#GREP_ARGS[@]} -gt 0 ]; then
    print_info "Filter: ${GREP_ARGS[*]}"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Display logs
if [ "$FOLLOW" = true ]; then
    # Follow mode (real-time)
    if [ ${#GREP_ARGS[@]} -gt 0 ]; then
        tail -f "$LOG_FILE" | grep --line-buffered "${GREP_ARGS[@]}" | highlight_logs
    else
        tail -f "$LOG_FILE" | highlight_logs
    fi
else
    # Static mode (last N lines)
    if [ ${#GREP_ARGS[@]} -gt 0 ]; then
        tail -n "$LINES" "$LOG_FILE" | grep "${GREP_ARGS[@]}" | highlight_logs
    else
        tail -n "$LINES" "$LOG_FILE" | highlight_logs
    fi
fi
