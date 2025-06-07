#!/bin/bash
# Quick run script - alias for dev-run.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/dev-run.sh" "$@"