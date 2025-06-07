#!/bin/bash
# Development run script for Live Transcripts
# Runs the service in foreground with full logging

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}!${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

# Function to print with timestamp
log_with_time() {
    echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $1"
}

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found. Run ./scripts/configure.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check for required environment variables
if [ ! -f ".env" ]; then
    print_error ".env file not found. Run ./scripts/configure.sh to set up"
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Check API keys
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-openai-api-key-here" ]; then
    print_error "OPENAI_API_KEY not configured in .env"
    exit 1
fi

if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "your-google-api-key-here" ]; then
    print_error "GOOGLE_API_KEY not configured in .env"
    exit 1
fi

# Clear screen for clean start
clear

echo -e "${MAGENTA}╔══════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║${NC}  🎤 Live Transcripts - Development Mode  ${MAGENTA}║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════╝${NC}"
echo

# Show configuration
print_info "Configuration:"

# Check audio backend
if [ -f "config.yaml" ]; then
    backend=$(grep -A 10 "^audio:" config.yaml 2>/dev/null | grep "backend_preference:" | cut -d: -f2- | xargs)
    device=$(grep -A 10 "^audio:" config.yaml 2>/dev/null | grep "device_name:" | cut -d: -f2- | xargs | tr -d '"')
    
    if [ -n "$backend" ]; then
        echo "  Audio Backend: ${GREEN}$backend${NC}"
    fi
    
    if [ -n "$device" ] && [ "$device" != "null" ]; then
        # Truncate long device names
        if [ ${#device} -gt 50 ]; then
            device_display="${device:0:47}..."
        else
            device_display="$device"
        fi
        echo "  Audio Device: ${GREEN}$device_display${NC}"
    else
        echo "  Audio Device: ${YELLOW}auto-select${NC}"
    fi
fi

echo "  Environment: ${GREEN}development${NC}"
echo "  Python: ${GREEN}$(python --version 2>&1 | cut -d' ' -f2)${NC}"
echo

print_info "Starting services..."
echo

# Function to handle cleanup on exit
cleanup() {
    echo
    log_with_time "${YELLOW}Shutting down...${NC}"
    
    # The Python script handles its own cleanup
    
    echo
    print_success "Services stopped"
    deactivate
    exit 0
}

# Set up signal handlers
trap cleanup INT TERM

# Parse command line arguments
ARGS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            ARGS="$ARGS --port $2"
            shift 2
            ;;
        --http-port)
            ARGS="$ARGS --http-port $2"
            shift 2
            ;;
        --whisper-model)
            ARGS="$ARGS --whisper-model $2"
            shift 2
            ;;
        --gemini-model)
            ARGS="$ARGS --gemini-model $2"
            shift 2
            ;;
        --context-minutes)
            ARGS="$ARGS --context-minutes $2"
            shift 2
            ;;
        --insight-interval)
            ARGS="$ARGS --insight-interval $2"
            shift 2
            ;;
        *)
            ARGS="$ARGS $1"
            shift
            ;;
    esac
done

# Run the application with unbuffered output for real-time logs
print_info "Launching Live Transcripts..."
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Run with Python unbuffered mode for immediate output
exec python -u -m src.livetranscripts.main $ARGS