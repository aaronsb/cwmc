#!/bin/bash
# Live Transcripts Development Status Script
# Shows the current status of the application

set -e

# Source common functions
source "$(dirname "$0")/common.sh"

# Check process status
check_process() {
    if [ -f ".pid" ]; then
        PID=$(cat .pid)
        if ps -p $PID > /dev/null 2>&1; then
            # Get process info
            PROCESS_INFO=$(ps -p $PID -o pid,etime,pcpu,pmem,args --no-headers)
            CPU=$(echo "$PROCESS_INFO" | awk '{print $3}')
            MEM=$(echo "$PROCESS_INFO" | awk '{print $4}')
            UPTIME=$(echo "$PROCESS_INFO" | awk '{print $2}')
            
            print_success "Live Transcripts is running"
            echo "  - PID: $PID"
            echo "  - Uptime: $UPTIME"
            echo "  - CPU: ${CPU}%"
            echo "  - Memory: ${MEM}%"
            
            # Check which mode it's running in
            if ps -p $PID -o args= | grep -q "main"; then
                echo "  - Mode: Full (transcription + Q&A)"
            else
                echo "  - Mode: Server only (Q&A)"
            fi
            
            return 0
        else
            print_error "Live Transcripts is not running (stale PID file)"
            return 1
        fi
    else
        print_error "Live Transcripts is not running"
        return 1
    fi
}

# Check port status
check_ports() {
    echo
    print_info "Port Status:"
    
    # Check WebSocket port
    if lsof -i:8765 >/dev/null 2>&1; then
        print_success "WebSocket server is listening on port 8765"
        echo "  - URL: http://localhost:8765"
    else
        print_warning "WebSocket server is not listening on port 8765"
    fi
}

# Check API connectivity
check_apis() {
    echo
    print_info "API Configuration:"
    
    if [ -f ".env" ]; then
        # Check if API keys are configured
        if grep -q "OPENAI_API_KEY=sk-" .env; then
            print_success "OpenAI API key is configured"
        else
            print_warning "OpenAI API key not configured"
        fi
        
        if ! grep -q "GOOGLE_API_KEY=your-google-key-here" .env; then
            print_success "Google API key is configured"
        else
            print_warning "Google API key not configured"
        fi
    else
        print_error ".env file not found"
    fi
}

# Show recent logs
show_recent_activity() {
    echo
    print_info "Recent Activity:"
    
    if [ -f "logs/livetranscripts.log" ]; then
        # Check log size
        LOG_SIZE=$(ls -lh logs/livetranscripts.log | awk '{print $5}')
        echo "  - Log size: $LOG_SIZE"
        
        # Show last few transcriptions if any
        RECENT_TRANSCRIPTIONS=$(grep -E "Transcription:|Generated transcript:" logs/livetranscripts.log 2>/dev/null | tail -n 3 || true)
        if [ -n "$RECENT_TRANSCRIPTIONS" ]; then
            echo "  - Recent transcriptions:"
            echo "$RECENT_TRANSCRIPTIONS" | sed 's/^/    /'
        fi
        
        # Show any recent errors
        RECENT_ERRORS=$(grep -E "ERROR|Error|error" logs/livetranscripts.log 2>/dev/null | tail -n 3 || true)
        if [ -n "$RECENT_ERRORS" ]; then
            echo "  - Recent errors:"
            echo "$RECENT_ERRORS" | sed 's/^/    /'
        fi
    else
        echo "  - No log file found"
    fi
}

# Show system resources
show_resources() {
    echo
    print_info "System Resources:"
    
    # Show audio devices (Linux)
    if command -v pactl &> /dev/null; then
        DEFAULT_SOURCE=$(pactl get-default-source 2>/dev/null || echo "Not found")
        echo "  - Default audio source: $DEFAULT_SOURCE"
    fi
    
    # Show Python version
    PYTHON_CMD=$(get_python_cmd)
    if [ -n "$PYTHON_CMD" ]; then
        PYTHON_VERSION=$($PYTHON_CMD --version | awk '{print $2}')
        if is_venv_active; then
            echo "  - Python version: $PYTHON_VERSION (venv active)"
        else
            echo "  - Python version: $PYTHON_VERSION"
        fi
    fi
}

# Main
main() {
    echo "📊 Live Transcripts - Status"
    echo "============================"
    echo
    
    # Ensure we're in the project directory
    ensure_project_dir
    
    # Check process status
    if check_process; then
        check_ports
        check_apis
        show_recent_activity
        show_resources
        
        echo
        print_info "Commands:"
        echo "  - View logs: tail -f logs/livetranscripts.log"
        echo "  - Stop app: ./scripts/stop.sh"
        echo "  - Restart: ./scripts/restart.sh"
    else
        check_apis
        
        echo
        print_info "Commands:"
        echo "  - Start app: ./scripts/start.sh"
        echo "  - Start Q&A only: ./scripts/start.sh server"
    fi
}

# Run main
main "$@"