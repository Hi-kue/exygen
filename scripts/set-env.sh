#!/usr/bin/env bash

# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script initializes local environment files
# (`.env`) and verifies required workspace tools
# (`node`, `pnpm`, `python3`, `uv`) across the
# Exygen monorepo or for specific apps under `apps/`.
#
# Compatible with Linux and macOS (Bash 3.2+).
#
# Current File: set-env.sh
# Commands: [all|root|agent|api|web ...] [--force|-f] [--sync] [--dry-run] [--help|-h]
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/logs.sh"

set -eo pipefail

usage() {
    info "Usage: ./scripts/set-env.sh [targets...] [options]"
    info "Targets:"
    info "  all                 Configure .env files for root, agent, api, and web (default)"
    info "  root                Configure root .env file"
    info "  agent               Configure apps/agent/.env file"
    info "  api                 Configure apps/api/.env file"
    info "  web                 Configure apps/web/.env file"
    info "Options:"
    info "  --force, -f         Overwrite existing .env files"
    info "  --sync              Run 'uv sync --all-packages' and 'pnpm install' after configuring env"
    info "  --dry-run           Log actions without writing files or running commands"
    info "  --help, -h          Show this help message"
    info "Examples:"
    info "  ./scripts/set-env.sh"
    info "  ./scripts/set-env.sh api web"
    info "  ./scripts/set-env.sh all --force --sync"
}

check_required_tools() {
    local missing=0
    for tool in node pnpm python3 uv; do
        if command -v "$tool" >/dev/null 2>&1; then
            info "Detected required tool: $tool ($(command -v "$tool"))"
        else
            error "Missing required tool: $tool"
            missing=$(( missing + 1 ))
        fi
    done
    if (( missing > 0 )); then
        error "Please install missing tools before continuing."
        exit 1
    fi
}

write_env_file() {
    local target_path="$1"
    local content="$2"
    local force="$3"
    local dry_run="$4"

    if [[ -f "$target_path" && "$force" != "true" ]]; then
        info "Skipping existing env file (use --force to overwrite): $target_path"
        return 0
    fi

    if [[ "$dry_run" == "true" ]]; then
        info "[dry-run] Would write env file: $target_path"
        return 0
    fi

    printf "%s\n" "$content" > "$target_path"
    success "Wrote environment file: $target_path"
}

configure_target() {
    local target="$1"
    local force="$2"
    local dry_run="$3"

    case "$target" in
        root)
            if [[ -f "$ROOT_DIR/.env.example" ]]; then
                local content
                content="$(< "$ROOT_DIR/.env.example")"
                write_env_file "$ROOT_DIR/.env" "$content" "$force" "$dry_run"
            else
                write_env_file "$ROOT_DIR/.env" "# Exygen Root Environment
EXYGEN_ENV=development
API_HOST=127.0.0.1
API_PORT=8000
WEB_PORT=3000
VITE_API_URL=http://localhost:8000
EXYGEN_LLM_PROVIDER=deterministic_fallback" "$force" "$dry_run"
            fi
            ;;
        agent)
            write_env_file "$ROOT_DIR/apps/agent/.env" "# Exygen Agent Environment
EXYGEN_LLM_PROVIDER=deterministic_fallback
EXYGEN_DEFAULT_COURSE=COMP-251" "$force" "$dry_run"
            ;;
        api)
            write_env_file "$ROOT_DIR/apps/api/.env" "# Exygen API Environment
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
EXYGEN_LLM_PROVIDER=deterministic_fallback" "$force" "$dry_run"
            ;;
        web)
            write_env_file "$ROOT_DIR/apps/web/.env" "# Exygen Web Environment
VITE_API_URL=http://localhost:8000" "$force" "$dry_run"
            ;;
    esac
}

main() {
    local force=false
    local sync_deps=false
    local dry_run=false
    local requested=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help | -h)
                usage
                exit 0
                ;;
            --force | -f)
                force=true
                ;;
            --sync)
                sync_deps=true
                ;;
            --dry-run)
                dry_run=true
                ;;
            --all)
                requested+=("all")
                ;;
            -*)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                IFS=',' read -r -a split_targets <<< "$1"
                for t in "${split_targets[@]}"; do
                    local norm="${t#apps/}"
                    norm="${norm%/}"
                    case "$norm" in
                        all | root | agent | api | web)
                            requested+=("$norm")
                            ;;
                        *)
                            error "Unknown target: '$t'. Expected: all, root, agent, api, web."
                            exit 1
                            ;;
                    esac
                done
                ;;
        esac
        shift
    done

    check_required_tools

    if (( ${#requested[@]} == 0 )) || [[ " ${requested[*]} " == *" all "* ]]; then
        requested=("root" "agent" "api" "web")
    fi

    for target in "${requested[@]}"; do
        configure_target "$target" "$force" "$dry_run"
    done

    if $sync_deps; then
        cd "$ROOT_DIR"
        if $dry_run; then
            info "[dry-run] Would run: uv sync --all-packages && pnpm install"
        else
            info "Syncing Python workspace dependencies with uv..."
            uv sync --all-packages
            info "Installing Node workspace dependencies with pnpm..."
            pnpm install
            success "Workspace dependencies synchronized."
        fi
    fi

    success "Environment setup complete."
}

main "$@"
