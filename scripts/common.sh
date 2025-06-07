#!/bin/bash
# Common functions for Live Transcripts scripts
# Source this file in other scripts: source "$(dirname "$0")/common.sh"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Print functions
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}!${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

# Get project directory
get_project_dir() {
    local SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[1]}" )" && pwd )"
    echo "$( cd "$SCRIPT_DIR/.." && pwd )"
}

# Activate virtual environment
activate_venv() {
    local PROJECT_DIR=$(get_project_dir)
    
    if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
        source "$PROJECT_DIR/venv/bin/activate"
        return 0
    elif [ -f "$PROJECT_DIR/venv/Scripts/activate" ]; then
        source "$PROJECT_DIR/venv/Scripts/activate"
        return 0
    else
        print_error "Virtual environment not found at $PROJECT_DIR/venv"
        print_warning "Run ./scripts/setup.sh to create it"
        return 1
    fi
}

# Check if venv is active
is_venv_active() {
    if [ -n "$VIRTUAL_ENV" ]; then
        return 0
    else
        return 1
    fi
}

# Ensure we're in project directory
ensure_project_dir() {
    local PROJECT_DIR=$(get_project_dir)
    cd "$PROJECT_DIR"
    
    if [ ! -f "pyproject.toml" ] || [ ! -d "src/livetranscripts" ]; then
        print_error "Invalid project directory: $PROJECT_DIR"
        exit 1
    fi
}

# Load environment variables from .env
load_env() {
    local PROJECT_DIR=$(get_project_dir)
    
    if [ -f "$PROJECT_DIR/.env" ]; then
        export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
        return 0
    else
        print_warning ".env file not found"
        return 1
    fi
}

# Get Python command (prefer venv)
get_python_cmd() {
    if is_venv_active; then
        echo "python"
    else
        local PROJECT_DIR=$(get_project_dir)
        if [ -f "$PROJECT_DIR/venv/bin/python" ]; then
            echo "$PROJECT_DIR/venv/bin/python"
        elif [ -f "$PROJECT_DIR/venv/Scripts/python.exe" ]; then
            echo "$PROJECT_DIR/venv/Scripts/python.exe"
        else
            echo "python3"
        fi
    fi
}