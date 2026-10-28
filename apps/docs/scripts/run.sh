#!/usr/bin/env bash

# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script is responsible for serving the documentation
# site locally for development and testing purposes. When
# executed, zensical will serve the documentation site on
# a specific port (default: 3000 usually) and provide the 
# localhost url to access it alongside other relevant
# pieces of information to the console.
#
# NOTE: YOU MUST HAVE UV INSTALLED AND PROPERLY CONFIGURED
# TO BE ABLE TO RUN THIS SCRIPT SUCCESSFULLY. IF YOU DON'T
# HAVE UV INSTALLED, PLEASE REFER TO THE OFFICIAL UV GUIDE
# FOR FURTHER INSTRUCTIONS:
# 
# https://docs.astral.sh/uv/getting-started/installation/
#
# Current File: run.sh
# Commands: N/A
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../scripts" && pwd)"
source "$SCRIPT_DIR/logs.sh"

set -e

info "Starting documentation site (port 3001)..."
uv run zensical serve --dev-addr localhost:3001