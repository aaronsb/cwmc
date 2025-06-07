#!/bin/bash
# Quick setup script for Live Transcripts
# Can be run directly with: curl -sSL https://raw.githubusercontent.com/aaronsb/cwmc/master/scripts/quick-setup.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}!${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

echo -e "${MAGENTA}🎤 Live Transcripts Quick Setup${NC}"
echo "================================"
echo

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed. Please install git first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    print_error "Python 3.9+ required (found $PYTHON_VERSION)"
    exit 1
fi

print_success "Found Python $PYTHON_VERSION"

# Determine target directory
TARGET_DIR="$HOME/Projects/cwmc"
print_info "Installing to: $TARGET_DIR"

# Create directory if needed
if [ -d "$TARGET_DIR" ]; then
    print_warning "Directory already exists: $TARGET_DIR"
    read -p "Remove existing directory and continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$TARGET_DIR"
    else
        print_info "Installation cancelled"
        exit 1
    fi
fi

# Create parent directory
mkdir -p "$(dirname "$TARGET_DIR")"

# Clone repository
print_info "Cloning Live Transcripts repository..."
git clone https://github.com/aaronsb/cwmc.git "$TARGET_DIR"
cd "$TARGET_DIR"

# Make scripts executable
chmod +x scripts/*.sh

# Run the main configuration script
print_info "Starting configuration..."
echo
./scripts/configure.sh

# Success message
echo
echo -e "${GREEN}✅ Live Transcripts installed successfully!${NC}"
echo
echo "Location: $TARGET_DIR"
echo
echo "To start using Live Transcripts:"
echo -e "  ${BLUE}cd $TARGET_DIR${NC}"
echo -e "  ${BLUE}./scripts/dev-run.sh${NC}"
echo
echo "For more options:"
echo "  ./scripts/list-audio-devices.sh    - List audio devices"
echo "  ./scripts/configure-audio-device.sh - Change audio device"
echo "  make dev                           - Run in development mode"