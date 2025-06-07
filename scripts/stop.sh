#!/bin/bash
# Live Transcripts Development Stop Script
# Stops the running application gracefully

set -e

# Source common functions
source "$(dirname "$0")/common.sh"

# Stop the application
stop_app() {
    if [ ! -f ".pid" ]; then
        print_warning "No PID file found - Live Transcripts may not be running"
        
        # Try to find the process anyway
        PIDS=$(pgrep -f "src.livetranscripts" || true)
        if [ -n "$PIDS" ]; then
            print_warning "Found Live Transcripts processes: $PIDS"
            read -p "Kill these processes? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kill $PIDS
                print_success "Processes killed"
            fi
        else
            print_error "No Live Transcripts processes found"
        fi
        return
    fi
    
    PID=$(cat .pid)
    
    if ps -p $PID > /dev/null 2>&1; then
        print_warning "Stopping Live Transcripts (PID: $PID)..."
        
        # Try graceful shutdown first
        kill -TERM $PID
        
        # Wait up to 5 seconds for graceful shutdown
        for i in {1..5}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
            echo -n "."
        done
        echo
        
        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            print_warning "Process didn't stop gracefully, forcing..."
            kill -KILL $PID
            sleep 1
        fi
        
        if ps -p $PID > /dev/null 2>&1; then
            print_error "Failed to stop process"
            exit 1
        else
            print_success "Live Transcripts stopped successfully"
            rm -f .pid
        fi
    else
        print_warning "Process $PID not found (already stopped?)"
        rm -f .pid
    fi
}

# Clean up resources
cleanup() {
    # Clean up any orphaned WebSocket connections
    WEBSOCKET_PIDS=$(lsof -ti:8765 2>/dev/null || true)
    if [ -n "$WEBSOCKET_PIDS" ]; then
        print_warning "Found processes on port 8765: $WEBSOCKET_PIDS"
        read -p "Kill these processes? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill $WEBSOCKET_PIDS 2>/dev/null || true
            print_success "WebSocket processes cleaned up"
        fi
    fi
}

# Show recent logs
show_logs() {
    if [ -f "logs/livetranscripts.log" ]; then
        echo
        echo "📜 Recent log entries:"
        echo "------------------------"
        tail -n 20 logs/livetranscripts.log
    fi
}

# Main
main() {
    echo "🛑 Live Transcripts - Development Stop"
    echo "====================================="
    echo
    
    # Ensure we're in the project directory
    ensure_project_dir
    
    # Stop the application
    stop_app
    
    # Clean up resources
    cleanup
    
    # Optionally show logs
    if [[ "$1" == "--logs" ]] || [[ "$1" == "-l" ]]; then
        show_logs
    fi
    
    echo
    print_success "Shutdown complete"
}

# Run main
main "$@"