#!/bin/bash
# Configure audio device for Live Transcripts
# Helps users select specific PipeWire/PulseAudio devices

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

# Check if config.yaml exists
if [ ! -f "config.yaml" ]; then
    print_error "config.yaml not found. Run ./scripts/configure.sh first"
    exit 1
fi

echo "🎤 Live Transcripts Audio Device Configuration"
echo "============================================="
echo

# Detect audio system
audio_system="unknown"
if command -v pw-cli &> /dev/null && pactl info 2>/dev/null | grep -q "PipeWire"; then
    audio_system="pipewire"
    print_success "PipeWire audio system detected"
elif command -v pactl &> /dev/null && pactl info &>/dev/null 2>&1; then
    audio_system="pulseaudio"
    print_success "PulseAudio audio system detected"
else
    print_error "No supported audio system detected"
    exit 1
fi

echo
print_info "Available audio sources:"
echo

# List all sources with detailed info
sources=()
source_descriptions=()
default_source=""
i=1

# Get default sink for monitor
if command -v pactl &> /dev/null; then
    default_sink=$(pactl get-default-sink 2>/dev/null || echo "")
    if [ -n "$default_sink" ]; then
        default_monitor="${default_sink}.monitor"
    fi
fi

# List all sources
while IFS=$'\t' read -r index name description; do
    # Skip null sources
    if [[ "$name" == *"null"* ]]; then
        continue
    fi
    
    # Determine source type
    source_type="input"
    type_label=""
    is_default=""
    
    if [[ "$name" == *".monitor" ]]; then
        source_type="monitor"
        type_label="${GREEN}[Monitor/Loopback]${NC}"
        
        # Check if this is the default monitor
        if [ "$name" = "$default_monitor" ]; then
            is_default="${GREEN}← Default${NC}"
        fi
    elif [[ "$description" == *"Microphone"* ]] || [[ "$description" == *"mic"* ]]; then
        type_label="${BLUE}[Microphone]${NC}"
    elif [[ "$description" == *"Webcam"* ]] || [[ "$description" == *"Camera"* ]]; then
        type_label="${BLUE}[Webcam]${NC}"
    fi
    
    # Format display
    printf "   %2d) %-50s %s %s\n" "$i" "$description" "$type_label" "$is_default"
    printf "       Device: %s\n" "$name"
    
    sources+=("$name")
    source_descriptions+=("$description")
    ((i++))
    
done < <(pactl list sources short | awk -F'\t' '{
    # Get source description
    cmd = "pactl list sources | grep -A 20 \"Name: " $2 "\" | grep \"Description:\" | cut -d: -f2- | xargs"
    cmd | getline desc
    close(cmd)
    print $1 "\t" $2 "\t" desc
}')

echo
print_info "Tips:"
echo "  - ${GREEN}[Monitor/Loopback]${NC} sources capture system audio (what you hear)"
echo "  - ${BLUE}[Microphone]${NC} sources capture from physical microphones"
echo "  - For meeting transcription, choose a monitor source"
echo

# Get user choice
read -p "Select audio source [1-$((i-1))]: " choice

# Validate choice
if [[ ! "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt $((i-1)) ]; then
    print_error "Invalid choice"
    exit 1
fi

selected_source="${sources[$((choice-1))]}"
selected_description="${source_descriptions[$((choice-1))]}"

echo
print_success "Selected: $selected_description"
print_info "Device: $selected_source"

# Update config.yaml
echo
print_info "Updating config.yaml..."

# Check if audio section exists
if grep -q "^audio:" config.yaml; then
    # Check if device_name exists under audio
    if grep -A 10 "^audio:" config.yaml | grep -q "device_name:"; then
        # Update existing device_name
        # Find the line number of audio: section
        audio_line=$(grep -n "^audio:" config.yaml | cut -d: -f1)
        # Find the next section (line starting without spaces)
        next_section_line=$(tail -n +$((audio_line + 1)) config.yaml | grep -n "^[^ ]" | head -1 | cut -d: -f1)
        
        if [ -n "$next_section_line" ]; then
            # Update device_name within audio section
            sed -i "/^audio:/,/^[^ ]/{s/device_name:.*/device_name: \"$selected_source\"/}" config.yaml
        else
            # Audio is the last section
            sed -i "/^audio:/,\${s/device_name:.*/device_name: \"$selected_source\"/}" config.yaml
        fi
    else
        # Add device_name to audio section
        awk -v device="$selected_source" '
            /^audio:/ { print; print "  device_name: \"" device "\""; next }
            { print }
        ' config.yaml > config.yaml.tmp
        mv config.yaml.tmp config.yaml
    fi
else
    # Add audio section with device_name
    echo "" >> config.yaml
    echo "audio:" >> config.yaml
    echo "  device_name: \"$selected_source\"" >> config.yaml
fi

print_success "Configuration updated!"

# Show current config
echo
print_info "Current audio configuration:"
grep -A 5 "^audio:" config.yaml | grep -E "(backend_preference|device_name):" | sed 's/^/  /'

# Test the device
echo
read -p "Test audio capture with this device? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Testing audio capture for 3 seconds..."
    
    if [ "$audio_system" = "pipewire" ]; then
        # Test with pw-record
        timeout 3 pw-record --target="$selected_source" --format=s16 --rate=16000 --channels=1 - | \
            pw-play --format=s16 --rate=16000 --channels=1 - &>/dev/null || true
    else
        # Test with parecord
        timeout 3 parecord --device="$selected_source" --format=s16le --rate=16000 --channels=1 | \
            paplay --format=s16le --rate=16000 --channels=1 &>/dev/null || true
    fi
    
    print_success "Audio test complete!"
    echo
    print_info "If you heard the audio playback, the device is working correctly."
    print_info "If not, try selecting a different device."
fi

echo
print_success "Audio device configuration complete!"
echo
print_info "Next steps:"
echo "  1. Start Live Transcripts: ./scripts/start.sh"
echo "  2. The selected device will be used for audio capture"
echo
print_info "To change the device later, run this script again."