#!/bin/bash
# Debug script to check .env file configuration

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Checking .env file configuration..."
echo

if [ ! -f ".env" ]; then
    echo -e "${RED}✗${NC} .env file not found"
    exit 1
fi

echo "File contents (keys hidden):"
echo "----------------------------"
while IFS= read -r line; do
    if [[ "$line" =~ ^([A-Z_]+)=(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        
        if [[ "$key" == *"API_KEY"* ]]; then
            if [[ "$value" == "your-"* ]]; then
                echo -e "${RED}✗${NC} $key=${value}"
            else
                # Hide the actual key value
                masked="[${#value} characters]"
                echo -e "${GREEN}✓${NC} $key=$masked"
            fi
        else
            echo "  $line"
        fi
    else
        echo "  $line"
    fi
done < .env

echo
echo "Checking for placeholder values:"
if grep -q "your-.*-api-key-here" .env; then
    echo -e "${RED}✗${NC} Found placeholder API keys"
    grep "your-.*-api-key-here" .env | while read -r line; do
        echo "  $line"
    done
else
    echo -e "${GREEN}✓${NC} No placeholder API keys found"
fi

echo
echo "Testing environment variable loading:"
source .env 2>/dev/null
if [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your-openai-api-key-here" ]; then
    echo -e "${GREEN}✓${NC} OPENAI_API_KEY is set (${#OPENAI_API_KEY} characters)"
else
    echo -e "${RED}✗${NC} OPENAI_API_KEY is not properly set"
fi

if [ -n "$GOOGLE_API_KEY" ] && [ "$GOOGLE_API_KEY" != "your-google-api-key-here" ]; then
    echo -e "${GREEN}✓${NC} GOOGLE_API_KEY is set (${#GOOGLE_API_KEY} characters)"
else
    echo -e "${RED}✗${NC} GOOGLE_API_KEY is not properly set"
fi