#!/usr/bin/env bash

# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script enables execution permissions for all
# scripts located in the `scripts/` directory. It
# is useful for ensuring that all utility scripts
# are executable without running into some errors
# when trying to run them manually.
#
# Current File: enable.sh
# Commands: N/A
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../scripts" && pwd)"
source "$SCRIPT_DIR/logs.sh"

set -e

info "Setting 'chmod +x' for all scripts in the scripts/ directory..."
chmod +x "$SCRIPT_DIR"/*.sh

if [ $? -eq 0 ]; then
    success "All scripts in the scripts/ directory have been set to executable."
else
    error "Failed to set executable permissions for scripts in the scripts/ directory."
    exit 1
fi
