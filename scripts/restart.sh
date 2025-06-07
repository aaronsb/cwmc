#!/bin/bash
# Live Transcripts Development Restart Script
# Convenience script to stop and start the application

set -e

# Source common functions
source "$(dirname "$0")/common.sh"

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${YELLOW}🔄 Restarting Live Transcripts...${NC}"
echo

# Stop if running
"$SCRIPT_DIR/stop.sh"

echo
sleep 1

# Start with the same mode if provided
"$SCRIPT_DIR/start.sh" "$@"