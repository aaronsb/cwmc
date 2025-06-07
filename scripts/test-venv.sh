#!/bin/bash
# Test script to verify virtual environment handling

set -e

# Source common functions
source "$(dirname "$0")/common.sh"

echo "🧪 Testing Virtual Environment Handling"
echo "======================================"
echo

# Test 1: Project directory detection
echo "1. Testing project directory detection..."
PROJECT_DIR=$(get_project_dir)
echo "   Project directory: $PROJECT_DIR"
if [ -d "$PROJECT_DIR/src/livetranscripts" ]; then
    print_success "Project directory detected correctly"
else
    print_error "Project directory detection failed"
fi
echo

# Test 2: Ensure project directory
echo "2. Testing ensure_project_dir..."
ensure_project_dir
CURRENT_DIR=$(pwd)
if [ "$CURRENT_DIR" = "$PROJECT_DIR" ]; then
    print_success "Changed to project directory successfully"
else
    print_error "Failed to change to project directory"
fi
echo

# Test 3: Virtual environment activation
echo "3. Testing virtual environment activation..."
if activate_venv; then
    print_success "Virtual environment activated"
    echo "   VIRTUAL_ENV: $VIRTUAL_ENV"
    echo "   Python: $(which python)"
else
    print_error "Failed to activate virtual environment"
fi
echo

# Test 4: Check if venv is active
echo "4. Testing venv active check..."
if is_venv_active; then
    print_success "Virtual environment is active"
else
    print_error "Virtual environment is not active"
fi
echo

# Test 5: Get Python command
echo "5. Testing get_python_cmd..."
PYTHON_CMD=$(get_python_cmd)
echo "   Python command: $PYTHON_CMD"
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "   Python version: $PYTHON_VERSION"
print_success "Python command retrieved"
echo

# Test 6: Load environment variables
echo "6. Testing environment variable loading..."
if load_env; then
    print_success "Environment variables loaded"
    # Check if API keys are set (without exposing them)
    if [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your-openai-key-here" ]; then
        print_success "OpenAI API key is set"
    else
        print_warning "OpenAI API key not configured"
    fi
    if [ -n "$GOOGLE_API_KEY" ] && [ "$GOOGLE_API_KEY" != "your-google-key-here" ]; then
        print_success "Google API key is set"
    else
        print_warning "Google API key not configured"
    fi
else
    print_warning "No .env file found"
fi
echo

# Test 7: Import test
echo "7. Testing Python imports..."
if $PYTHON_CMD -c "import src.livetranscripts.main" 2>/dev/null; then
    print_success "Can import main module"
else
    print_error "Cannot import main module"
fi
echo

print_success "Virtual environment tests complete!"