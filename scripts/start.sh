#!/bin/bash
# Live Transcripts Development Start Script
# Starts the application with proper environment and monitoring

set -e

# Source common functions
source "$(dirname "$0")/common.sh"

# Check if already running
check_if_running() {
    if [ -f ".pid" ]; then
        PID=$(cat .pid)
        if ps -p $PID > /dev/null 2>&1; then
            print_error "Live Transcripts is already running (PID: $PID)"
            print_warning "Use ./scripts/stop.sh to stop it first"
            exit 1
        else
            # Clean up stale PID file
            rm -f .pid
        fi
    fi
}

# Check prerequisites
check_prerequisites() {
    # Check virtual environment
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found"
        print_warning "Run ./scripts/configure.sh first"
        exit 1
    fi
    
    # Check .env file
    if [ ! -f ".env" ]; then
        print_error ".env file not found"
        print_warning "Run ./scripts/configure.sh to create it"
        exit 1
    fi
    
    # Check API keys
    if grep -q "your-.*-api-key-here" .env; then
        print_error "API keys not configured in .env file"
        print_warning "Please add your OpenAI and Google API keys to .env"
        exit 1
    fi
}

# Start the application
start_app() {
    # Activate virtual environment
    if ! activate_venv; then
        exit 1
    fi
    
    # Load environment variables
    load_env
    
    # Create logs directory
    mkdir -p logs
    
    # Start based on mode
    MODE=${1:-full}
    
    case $MODE in
        "full"|"main")
            print_success "Starting Live Transcripts (full mode)..."
            nohup $(get_python_cmd) -m src.livetranscripts.main > logs/livetranscripts.log 2>&1 &
            PID=$!
            APP_MODE="Full transcription + Q&A"
            ;;
        "server"|"qa")
            print_success "Starting Live Transcripts (Q&A server only)..."
            nohup $(get_python_cmd) -m src.livetranscripts.server > logs/livetranscripts.log 2>&1 &
            PID=$!
            APP_MODE="Q&A server only"
            ;;
        *)
            print_error "Unknown mode: $MODE"
            print_warning "Usage: ./scripts/start.sh [full|server]"
            exit 1
            ;;
    esac
    
    # Save PID
    echo $PID > .pid
    
    # Wait a moment for startup
    sleep 2
    
    # Check if started successfully
    if ps -p $PID > /dev/null; then
        print_success "Live Transcripts started successfully!"
        echo
        echo "📊 Status:"
        echo "  - Mode: $APP_MODE"
        echo "  - PID: $PID"
        echo "  - Logs: tail -f logs/livetranscripts.log"
        echo "  - WebUI: http://localhost:8765"
        echo
        echo "🛑 To stop: ./scripts/stop.sh"
        
        # Show initial log output
        echo
        echo "📜 Initial log output:"
        echo "------------------------"
        timeout 3 tail -f logs/livetranscripts.log || true
    else
        print_error "Failed to start Live Transcripts"
        print_warning "Check logs/livetranscripts.log for errors"
        rm -f .pid
        exit 1
    fi
}

# Main
main() {
    echo "🎤 Live Transcripts - Development Start"
    echo "======================================"
    echo
    
    # Ensure we're in the project directory
    ensure_project_dir
    
    check_if_running
    check_prerequisites
    
    # Parse arguments
    MODE=${1:-full}
    
    # Start the application
    start_app $MODE
}

# Run main
main "$@"