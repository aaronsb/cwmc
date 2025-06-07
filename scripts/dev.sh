#!/bin/bash
# Live Transcripts Development Helper Script
# Interactive menu for development tasks

set -e

# Source common functions
source "$(dirname "$0")/common.sh"

# Get directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR=$(get_project_dir)

# Show menu
show_menu() {
    clear
    echo -e "${CYAN}🎤 Live Transcripts - Development Menu${NC}"
    echo "======================================="
    echo
    echo "1) Start application (full mode)"
    echo "2) Start Q&A server only"
    echo "3) Stop application"
    echo "4) Restart application"
    echo "5) Show status"
    echo "6) View logs (live)"
    echo "7) Run tests"
    echo "8) Format code"
    echo "9) Run linting"
    echo "0) Exit"
    echo
}

# Execute choice
execute_choice() {
    case $1 in
        1)
            echo -e "${GREEN}Starting application (full mode)...${NC}"
            "$SCRIPT_DIR/start.sh" full
            read -p "Press Enter to continue..."
            ;;
        2)
            echo -e "${GREEN}Starting Q&A server only...${NC}"
            "$SCRIPT_DIR/start.sh" server
            read -p "Press Enter to continue..."
            ;;
        3)
            echo -e "${YELLOW}Stopping application...${NC}"
            "$SCRIPT_DIR/stop.sh"
            read -p "Press Enter to continue..."
            ;;
        4)
            echo -e "${YELLOW}Restarting application...${NC}"
            "$SCRIPT_DIR/restart.sh"
            read -p "Press Enter to continue..."
            ;;
        5)
            "$SCRIPT_DIR/status.sh"
            read -p "Press Enter to continue..."
            ;;
        6)
            echo -e "${BLUE}Viewing logs (Ctrl+C to exit)...${NC}"
            if [ -f "$PROJECT_DIR/logs/livetranscripts.log" ]; then
                tail -f "$PROJECT_DIR/logs/livetranscripts.log"
            else
                echo -e "${RED}No log file found${NC}"
                read -p "Press Enter to continue..."
            fi
            ;;
        7)
            echo -e "${BLUE}Running tests...${NC}"
            cd "$PROJECT_DIR"
            activate_venv
            make test
            read -p "Press Enter to continue..."
            ;;
        8)
            echo -e "${BLUE}Formatting code...${NC}"
            cd "$PROJECT_DIR"
            activate_venv
            make format
            read -p "Press Enter to continue..."
            ;;
        9)
            echo -e "${BLUE}Running linting...${NC}"
            cd "$PROJECT_DIR"
            activate_venv
            make lint
            read -p "Press Enter to continue..."
            ;;
        0)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            read -p "Press Enter to continue..."
            ;;
    esac
}

# Main loop
main() {
    ensure_project_dir
    
    while true; do
        show_menu
        read -p "Enter your choice: " choice
        execute_choice "$choice"
    done
}

# Run main
main