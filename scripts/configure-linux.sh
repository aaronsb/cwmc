#!/bin/bash
# Linux-specific configuration for Live Transcripts

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

# Versions that print to stderr (for functions that return values)
print_success_err() { echo -e "${GREEN}✓${NC} $1" >&2; }
print_error_err() { echo -e "${RED}✗${NC} $1" >&2; }
print_warning_err() { echo -e "${YELLOW}!${NC} $1" >&2; }
print_info_err() { echo -e "${BLUE}ℹ${NC} $1" >&2; }

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$NAME"
    elif command -v lsb_release &> /dev/null; then
        lsb_release -si
    elif [ -f /etc/arch-release ]; then
        echo "Arch Linux"
    elif [ -f /etc/debian_version ]; then
        echo "Debian"
    elif [ -f /etc/redhat-release ]; then
        echo "Red Hat"
    else
        echo "Unknown"
    fi
}

# Configure audio for Linux
configure_audio() {
    echo
    print_info "Configuring Linux audio system..."
    
    # Detect audio server
    audio_server="unknown"
    
    # Check for PipeWire
    if command -v pw-cli &> /dev/null; then
        if pactl info 2>/dev/null | grep -q "Server Name:.*PipeWire"; then
            audio_server="pipewire"
            print_success "PipeWire audio server detected (recommended)"
            
            # Check PipeWire version
            pw_version=$(pw-cli --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
            print_info "PipeWire version: $pw_version"
            
            # List PipeWire modules
            if command -v pw-cli &> /dev/null; then
                echo
                print_info "Checking PipeWire modules..."
                if pw-cli list-objects | grep -q "PipeWire:Interface:Module"; then
                    print_success "PipeWire modules loaded correctly"
                fi
            fi
        else
            print_warning "PipeWire installed but not running as audio server"
            audio_server="pipewire-available"
        fi
    fi
    
    # Check for PulseAudio
    if [ "$audio_server" = "unknown" ] && command -v pactl &> /dev/null; then
        if pactl info &>/dev/null; then
            audio_server="pulseaudio"
            print_success "PulseAudio audio server detected"
            
            # Check PulseAudio version
            pa_version=$(pactl info | grep "Server Version" | cut -d: -f2 | xargs)
            print_info "PulseAudio version: $pa_version"
        fi
    fi
    
    # Check for JACK
    if command -v jack_control &> /dev/null; then
        if jack_control status &>/dev/null; then
            print_info "JACK audio server also available"
        fi
    fi
    
    # List audio sources
    echo
    print_info "Available audio sources:"
    if command -v pactl &> /dev/null; then
        sources=$(pactl list sources short 2>/dev/null | grep -E "\.monitor|_monitor" | head -5)
        if [ -n "$sources" ]; then
            echo "$sources" | while read -r line; do
                source_name=$(echo "$line" | awk '{print $2}')
                echo "  - $source_name"
            done
            print_success "Monitor sources found for system audio capture"
        else
            print_warning "No monitor sources found - system audio capture may not work"
            print_info "This might be normal if no audio is playing"
        fi
    fi
    
    # Audio permissions check
    echo
    print_info "Checking audio permissions..."
    if groups | grep -qE "(audio|pipewire)"; then
        print_success "User is in audio group"
    else
        print_warning "User not in audio group - this is usually OK with modern systems"
    fi
    
    # Real-time permissions (for low latency)
    if [ -f /etc/security/limits.d/audio.conf ] || [ -f /etc/security/limits.d/99-audio.conf ]; then
        print_success "Real-time audio permissions configured"
    else
        print_info "No special real-time permissions configured (optional)"
    fi
    
    # Return detected audio server
    echo "$audio_server"
}

# Configure distribution-specific settings
configure_distro() {
    local distro="$1"
    
    echo
    print_info "Configuring for $distro..."
    
    case "$distro" in
        "Arch Linux"|"Manjaro"*)
            print_info "Arch-based distribution detected"
            print_info "Recommended packages: pipewire pipewire-pulse pipewire-jack"
            ;;
        "Ubuntu"|"Debian"*)
            print_info "Debian-based distribution detected"
            if [ "$audio_server" = "pipewire" ]; then
                print_info "Using PipeWire (modern setup)"
            else
                print_info "Consider upgrading to PipeWire for better performance"
            fi
            ;;
        "Fedora"*|"Red Hat"*)
            print_info "Red Hat-based distribution detected"
            print_info "Fedora uses PipeWire by default since F34"
            ;;
        *)
            print_info "Generic Linux configuration"
            ;;
    esac
}

# Detect available audio backends
detect_backends() {
    local backends=()
    
    # Check for PipeWire
    if command -v pw-cli &> /dev/null; then
        if pactl info 2>/dev/null | grep -q "Server Name:.*PipeWire"; then
            backends+=("pipewire:running:recommended")
        else
            backends+=("pipewire:available:recommended")
        fi
    fi
    
    # Check for PulseAudio
    if command -v pactl &> /dev/null; then
        if pactl info &>/dev/null 2>&1 && ! pactl info 2>/dev/null | grep -q "PipeWire"; then
            backends+=("pulseaudio:running:good")
        elif ! pactl info 2>/dev/null | grep -q "PipeWire"; then
            backends+=("pulseaudio:available:good")
        fi
    fi
    
    # Check for JACK
    if command -v jack_control &> /dev/null; then
        if jack_control status &>/dev/null 2>&1; then
            backends+=("jack:running:advanced")
        else
            backends+=("jack:available:advanced")
        fi
    fi
    
    # SoundDevice (Python) - always available as fallback
    backends+=("sounddevice:available:fallback")
    
    # PyAudio - check if can be used
    if python3 -c "import pyaudio" &>/dev/null 2>&1; then
        backends+=("pyaudio:available:legacy")
    fi
    
    printf '%s\n' "${backends[@]}"
}

# Let user choose audio backend
choose_backend() {
    echo >&2
    print_info_err "Available audio backends:"
    echo >&2
    
    local backends=($(detect_backends))
    local options=()
    local default_choice=""
    local i=1
    
    for backend_info in "${backends[@]}"; do
        IFS=':' read -r backend status recommendation <<< "$backend_info"
        
        # Format display
        local display="$i) $backend"
        
        # Add status
        if [ "$status" = "running" ]; then
            display+=" $(echo -e "${GREEN}[running]${NC}")"
        else
            display+=" [available]"
        fi
        
        # Add recommendation
        case "$recommendation" in
            "recommended")
                display+=" $(echo -e "${GREEN}← Recommended${NC}")"
                [ -z "$default_choice" ] && default_choice=$i
                ;;
            "good")
                display+=" $(echo -e "${BLUE}← Good choice${NC}")"
                [ -z "$default_choice" ] && default_choice=$i
                ;;
            "advanced")
                display+=" $(echo -e "${YELLOW}← For advanced users${NC}")"
                ;;
            "fallback")
                display+=" ← Fallback option"
                ;;
            "legacy")
                display+=" ← Legacy (may show warnings)"
                ;;
        esac
        
        echo -e "   $display" >&2
        options+=("$backend")
        ((i++))
    done
    
    echo >&2
    # Show auto option
    echo -e "   $i) auto $(echo -e "${GREEN}← Let Live Transcripts decide${NC}")" >&2
    options+=("auto")
    
    # Get user choice
    echo >&2
    if [ -n "$default_choice" ]; then
        read -p "Select audio backend [1-$i] (default: $default_choice): " choice >&2
        [ -z "$choice" ] && choice=$default_choice
    else
        read -p "Select audio backend [1-$i]: " choice >&2
    fi
    
    # Validate choice
    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "$i" ]; then
        selected_backend="${options[$((choice-1))]}"
        print_success_err "Selected: $selected_backend"
        echo "$selected_backend"
    else
        print_error_err "Invalid choice"
        echo "auto"
    fi
}

# Configure selected backend
configure_backend() {
    local backend="$1"
    
    echo
    print_info "Configuring $backend backend..."
    
    case "$backend" in
        "pipewire")
            print_info "PipeWire configuration:"
            echo "  - Lowest latency and best performance"
            echo "  - Native system audio capture support"
            echo "  - Recommended quantum: 256-512 for low latency"
            
            # Update config
            update_config "pipewire"
            ;;
            
        "pulseaudio")
            print_info "PulseAudio configuration:"
            echo "  - Stable and widely supported"
            echo "  - Good system audio capture via monitor sources"
            echo "  - Higher latency than PipeWire"
            
            # Update config
            update_config "pulseaudio"
            ;;
            
        "jack")
            print_info "JACK configuration:"
            echo "  - Professional audio with ultra-low latency"
            echo "  - Requires JACK server to be running"
            echo "  - Best for audio production environments"
            
            # Update config
            update_config "jack"
            ;;
            
        "sounddevice")
            print_info "SoundDevice configuration:"
            echo "  - Python-based, cross-platform"
            echo "  - Good compatibility"
            echo "  - Moderate latency"
            
            # Update config
            update_config "sounddevice"
            ;;
            
        "pyaudio")
            print_info "PyAudio configuration:"
            echo "  - Legacy backend, widely compatible"
            echo "  - May show ALSA warnings (harmless)"
            echo "  - Higher latency"
            
            # Update config
            update_config "pyaudio"
            ;;
            
        "auto"|*)
            print_info "Automatic backend selection:"
            echo "  - Live Transcripts will choose the best available backend"
            echo "  - Priority: PipeWire → PulseAudio → SoundDevice → PyAudio"
            
            # Update config
            update_config "auto"
            ;;
    esac
}

# Update config.yaml with backend choice
update_config() {
    local backend="$1"
    
    # Check if config.yaml exists
    if [ ! -f "config.yaml" ]; then
        print_warning "config.yaml not found, creating one"
        cat > config.yaml << EOF
# Live Transcripts Configuration - Linux
# Auto-generated by configure-linux.sh

profile: linux

audio:
  backend_preference: $backend
  
# Run ./scripts/configure-linux.sh to change audio backend
EOF
    else
        # Update existing config
        if grep -q "backend_preference:" config.yaml; then
            # Update existing backend_preference
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/backend_preference:.*/backend_preference: $backend/" config.yaml
            else
                sed -i "s/backend_preference:.*/backend_preference: $backend/" config.yaml
            fi
            print_success "Updated backend preference to: $backend"
        else
            # Add backend_preference under audio section
            if grep -q "^audio:" config.yaml; then
                # Find audio section and add backend_preference
                awk '/^audio:/ {print; print "  backend_preference: '$backend'"; next} 1' config.yaml > config.yaml.tmp
                mv config.yaml.tmp config.yaml
                print_success "Added backend preference: $backend"
            else
                # No audio section, append it
                echo "" >> config.yaml
                echo "audio:" >> config.yaml
                echo "  backend_preference: $backend" >> config.yaml
                print_success "Added audio configuration with backend: $backend"
            fi
        fi
    fi
}

# Optimize audio settings
optimize_audio() {
    local backend="$1"
    
    echo
    print_info "Optimization tips for $backend:"
    
    case "$backend" in
        "pipewire")
            echo "  - Lower latency: pw-metadata -n settings 0 clock.force-quantum 256"
            echo "  - Check performance: pw-top"
            echo "  - View devices: pw-cli list-objects | grep node.name"
            ;;
        "pulseaudio")
            echo "  - Reduce latency: edit /etc/pulse/daemon.conf"
            echo "  - Set: default-fragments = 2"
            echo "  - Set: default-fragment-size-msec = 5"
            ;;
        "jack")
            echo "  - Start JACK: jack_control start"
            echo "  - Set buffer size: jack_control ds period 256"
            echo "  - Use QjackCtl for GUI control"
            ;;
        *)
            echo "  - Default settings should work well"
            ;;
    esac
}

# Main configuration
main() {
    echo "🐧 Linux Audio Configuration for Live Transcripts"
    echo "================================================"
    
    # Detect distribution
    DISTRO=$(detect_distro)
    print_info "Detected distribution: $DISTRO"
    
    # Configure distribution-specific settings first (brief)
    case "$DISTRO" in
        "Arch Linux"|"Manjaro"*)
            print_info "Arch-based system - excellent audio support"
            ;;
        "Ubuntu"|"Debian"*)
            print_info "Debian-based system detected"
            ;;
        "Fedora"*|"Red Hat"*)
            print_info "Red Hat-based system detected"
            ;;
    esac
    
    # Detect current audio setup
    echo
    print_info "Detecting audio system..."
    
    # Check what's currently running
    current_audio="unknown"
    if command -v pw-cli &> /dev/null && pactl info 2>/dev/null | grep -q "PipeWire"; then
        current_audio="PipeWire"
        print_success "Currently running: PipeWire"
    elif command -v pactl &> /dev/null && pactl info &>/dev/null 2>&1; then
        current_audio="PulseAudio"
        print_success "Currently running: PulseAudio"
    else
        print_warning "No audio server detected"
    fi
    
    # Let user choose backend
    selected_backend=$(choose_backend)
    
    # Configure the selected backend
    configure_backend "$selected_backend"
    
    # Show optimization tips
    optimize_audio "$selected_backend"
    
    echo
    print_success "Linux audio configuration complete!"
    
    # Show summary
    echo
    print_info "Configuration Summary:"
    echo "  - Distribution: $DISTRO"
    echo "  - Audio system: $current_audio"
    echo "  - Selected backend: $selected_backend"
    echo
    
    if [ "$selected_backend" = "pipewire" ] && [ "$current_audio" != "PipeWire" ]; then
        print_warning "Note: PipeWire backend selected but PipeWire is not running"
        print_info "Consider starting PipeWire or selecting a different backend"
    fi
    
    # Ask about device configuration
    echo
    read -p "Configure specific audio device now? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Run device configuration script
        if [ -f "scripts/configure-audio-device.sh" ]; then
            echo
            bash scripts/configure-audio-device.sh
        else
            print_error "Audio device configuration script not found"
        fi
    else
        echo
        print_info "You can configure audio devices later with:"
        echo "  ./scripts/configure-audio-device.sh"
    fi
}

# Run main
main "$@"