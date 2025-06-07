#!/bin/bash
# List available audio devices for Live Transcripts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}!${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

echo "🎤 Available Audio Devices"
echo "========================="
echo

# Detect audio system
if command -v pw-cli &> /dev/null && pactl info 2>/dev/null | grep -q "PipeWire"; then
    print_success "Audio System: PipeWire"
    audio_system="pipewire"
elif command -v pactl &> /dev/null && pactl info &>/dev/null 2>&1; then
    print_success "Audio System: PulseAudio"
    audio_system="pulseaudio"
else
    print_error "No supported audio system detected"
    exit 1
fi

# Get default devices
echo
print_info "Default Devices:"

if command -v pactl &> /dev/null; then
    default_sink=$(pactl get-default-sink 2>/dev/null || echo "none")
    default_source=$(pactl get-default-source 2>/dev/null || echo "none")
    
    echo "  Output (sink): $default_sink"
    echo "  Input (source): $default_source"
    
    if [ "$default_sink" != "none" ]; then
        echo "  Monitor: ${default_sink}.monitor ${GREEN}← For system audio capture${NC}"
    fi
fi

# List all sinks (outputs)
echo
print_info "Audio Outputs (Sinks):"
echo

if command -v pactl &> /dev/null; then
    pactl list sinks short | while IFS=$'\t' read -r index name state format channels; do
        # Get sink description
        desc=$(pactl list sinks | grep -A 20 "Name: $name" | grep "Description:" | cut -d: -f2- | xargs)
        
        printf "  %-40s %s\n" "$name" "$desc"
        printf "  %-40s ${GREEN}%s${NC}\n" "${name}.monitor" "← Monitor for capturing output"
        echo
    done
fi

# List all sources (inputs)
echo
print_info "Audio Inputs (Sources):"
echo

if command -v pactl &> /dev/null; then
    pactl list sources short | while IFS=$'\t' read -r index name state format channels; do
        # Skip monitors as we already listed them
        if [[ "$name" == *".monitor" ]]; then
            continue
        fi
        
        # Get source description
        desc=$(pactl list sources | grep -A 20 "Name: $name" | grep "Description:" | cut -d: -f2- | xargs)
        
        # Determine type
        type_label=""
        if [[ "$desc" == *"Microphone"* ]] || [[ "$desc" == *"mic"* ]]; then
            type_label="${BLUE}[Microphone]${NC}"
        elif [[ "$desc" == *"Webcam"* ]] || [[ "$desc" == *"Camera"* ]]; then
            type_label="${BLUE}[Webcam]${NC}"
        fi
        
        printf "  %-40s %s %s\n" "$name" "$desc" "$type_label"
    done
fi

# Check current configuration
echo
print_info "Current Configuration:"

if [ -f "config.yaml" ]; then
    device_name=$(grep -A 10 "^audio:" config.yaml 2>/dev/null | grep "device_name:" | cut -d: -f2- | xargs | tr -d '"')
    backend=$(grep -A 10 "^audio:" config.yaml 2>/dev/null | grep "backend_preference:" | cut -d: -f2- | xargs)
    
    if [ -n "$backend" ]; then
        echo "  Backend: $backend"
    else
        echo "  Backend: auto"
    fi
    
    if [ -n "$device_name" ] && [ "$device_name" != "null" ]; then
        echo "  Device: $device_name"
        
        # Check if device exists
        if pactl list sources | grep -q "Name: $device_name"; then
            print_success "  Status: Device found"
        else
            print_warning "  Status: Device not found!"
        fi
    else
        echo "  Device: auto-select"
    fi
else
    print_warning "config.yaml not found"
fi

echo
print_info "Tips:"
echo "  - For meeting transcription, use a '.monitor' device"
echo "  - Monitor devices capture what you hear (system audio)"
echo "  - Run ./scripts/configure-audio-device.sh to select a device"