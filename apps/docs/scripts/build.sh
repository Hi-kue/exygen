#!/usr/bin/env bash

# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script is for building the documentation site
# for production deployment. When executed, zensical
# will build a static site from your Markdown files
# and output the generated files in its default 
# output directory (usually `dist/` or `.output/`).
#
# NOTE: YOU MUST HAVE UV INSTALLED AND PROPERLY CONFIGURED
# TO BE ABLE TO RUN THIS SCRIPT SUCCESSFULLY. IF YOU DON'T
# HAVE UV INSTALLED, PLEASE REFER TO THE OFFICIAL UV GUIDE
# FOR FURTHER INSTRUCTIONS:
# 
# https://docs.astral.sh/uv/getting-started/installation/
#
# Current File: build.sh
# Commands: N/A
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../scripts" && pwd)"
source "$SCRIPT_DIR/logs.sh"

set -e

info "Building documentation site with zensical..."
uv run zensical build --clean

info "Verifying generated local assets..."
uv run python scripts/verify_assets.py